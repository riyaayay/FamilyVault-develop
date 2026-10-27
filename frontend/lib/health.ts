// Health & Emergency Red Alert data layer.
//
// Core Backend (backend/app/api/v1/endpoints/health.py), prefix /api/v1/health:
//   GET  /records                 -> clan health board (household-private records come back `restricted`)
//   POST /emergency-dossier/{id}  -> full dossier from the real health record (audited)
//   POST /emergency-pass/{id}     -> HMAC-signed 24h pass token for a QR code
//   POST /emergency-alert/trigger -> family-wide Red Alert broadcast (audited)
// Falls back to the seeded Vance data when the backend is unreachable.

import type { EmergencyPayload } from "@/components/family/EmergencyAlertOverlay";
import { BACKEND_URL, backendFetch } from "./api";

export type Medication = { name: string; dosage: string; frequency: string };

export type HealthRecord = {
  blood_group: string | null;
  allergies: string[];
  chronic_conditions: string[];
  current_medications: Medication[];
  emergency_notes: string | null;
  primary_physician_contact: string | null;
  is_emergency_visible: boolean;
};

export type MemberHealth = {
  user_id: string;
  full_name: string;
  date_of_birth: string | null;
  has_record: boolean;
  restricted: boolean;
  record: HealthRecord | null;
};

export type Dossier = {
  patient_id: string;
  full_name: string;
  blood_group: string | null;
  critical_allergies: string[];
  chronic_conditions: string[];
  active_medications: Medication[];
  emergency_contacts: { name: string; relation: string; phone_number: string | null }[];
  primary_physician_contact: string | null;
  emergency_notes: string | null;
  has_health_record: boolean;
  tamper_proof_hash: string;
};

export type EmergencyPass = { token: string; pass_path: string; expires_at: string };

const record = (r: Partial<HealthRecord>): HealthRecord => ({
  blood_group: null,
  allergies: [],
  chronic_conditions: [],
  current_medications: [],
  emergency_notes: null,
  primary_physician_contact: null,
  is_emergency_visible: true,
  ...r,
});

// Mirrors backend/scripts/seed.py health_records.
const mockBoard: MemberHealth[] = [
  {
    user_id: "00000000-0000-0000-0000-000000000001", full_name: "Arthur Vance", date_of_birth: "1948-03-15",
    has_record: true, restricted: false,
    record: record({
      blood_group: "B+", allergies: ["Dust mites"], chronic_conditions: ["Mild Arthritis"],
      current_medications: [{ name: "Glucosamine", dosage: "500mg", frequency: "Daily" }],
      emergency_notes: "Requires walking stick assistance for prolonged travel.",
      primary_physician_contact: "+91-98110-22334 (Dr. Sen)",
    }),
  },
  {
    user_id: "00000000-0000-0000-0000-000000000002", full_name: "Eleanor Vance", date_of_birth: "1952-08-22",
    has_record: true, restricted: false,
    record: record({
      blood_group: "O+", allergies: ["Penicillin", "Sulfa drugs"], chronic_conditions: ["Hypertension", "Arrhythmia"],
      current_medications: [
        { name: "Amlodipine", dosage: "5mg", frequency: "Once daily, morning" },
        { name: "Aspirin", dosage: "75mg", frequency: "Post dinner" },
      ],
      emergency_notes: "Cardiac pacemaker installed Nov 2024. Primary physician Dr. A. Sen at AIIMS.",
      primary_physician_contact: "+91-98110-22334 (Dr. Sen)",
    }),
  },
  { user_id: "00000000-0000-0000-0000-000000000003", full_name: "David Vance", date_of_birth: "1975-11-10", has_record: false, restricted: false, record: null },
  { user_id: "00000000-0000-0000-0000-000000000004", full_name: "Sarah Vance", date_of_birth: "1978-05-18", has_record: false, restricted: false, record: null },
  {
    user_id: "00000000-0000-0000-0000-000000000008", full_name: "Lucas Vance", date_of_birth: "2005-06-12",
    has_record: true, restricted: false,
    record: record({ blood_group: "O+", allergies: ["Peanuts", "Shellfish"], emergency_notes: "EpiPen prescribed; carries in school backpack." }),
  },
];

export type Loaded<T> = { data: T; live: boolean };

export async function getHealthBoard(): Promise<Loaded<MemberHealth[]>> {
  if (!BACKEND_URL) return { data: mockBoard, live: false };
  try {
    return { data: await backendFetch<MemberHealth[]>("/api/v1/health/records"), live: true };
  } catch (err) {
    console.warn("[health] board falling back to mock data:", err);
    return { data: mockBoard, live: false };
  }
}

function mockDossier(memberId: string): Dossier {
  const m = mockBoard.find((x) => x.user_id === memberId) ?? mockBoard[1];
  const r = m.record ?? record({});
  return {
    patient_id: m.user_id,
    full_name: m.full_name,
    blood_group: r.blood_group,
    critical_allergies: r.allergies,
    chronic_conditions: r.chronic_conditions,
    active_medications: r.current_medications,
    emergency_contacts: [
      { name: "Arthur Vance", relation: "Head of family", phone_number: "+91-98100-11001" },
      { name: "David Vance", relation: "Child", phone_number: "+91-98100-11003" },
    ].filter((c) => c.name !== m.full_name),
    primary_physician_contact: r.primary_physician_contact,
    emergency_notes: r.emergency_notes,
    has_health_record: m.has_record,
    tamper_proof_hash: "offline-demo",
  };
}

/** Compiles the dossier; `live` is false when it came from offline demo data. */
export async function compileDossier(memberId: string): Promise<Loaded<Dossier>> {
  if (!BACKEND_URL) return { data: mockDossier(memberId), live: false };
  try {
    const data = await backendFetch<Dossier>(`/api/v1/health/emergency-dossier/${memberId}`, { method: "POST" });
    return { data, live: true };
  } catch (err) {
    console.warn("[health] dossier falling back to mock data:", err);
    return { data: mockDossier(memberId), live: false };
  }
}

export async function issueEmergencyPass(memberId: string): Promise<EmergencyPass | null> {
  if (!BACKEND_URL) return null;
  try {
    return await backendFetch<EmergencyPass>(`/api/v1/health/emergency-pass/${memberId}`, { method: "POST" });
  } catch (err) {
    console.warn("[health] could not issue emergency pass:", err);
    return null;
  }
}

export async function triggerRedAlert(memberId: string, condition: string): Promise<boolean> {
  if (!BACKEND_URL) return true;
  try {
    await backendFetch("/api/v1/health/emergency-alert/trigger", {
      method: "POST",
      body: { user_id: memberId, condition },
    });
    return true;
  } catch (err) {
    console.warn("[health] red alert broadcast failed:", err);
    return false;
  }
}

/** Shapes a dossier for the existing EmergencyAlertDossierModal. */
export function dossierToPayload(d: Dossier, passUrl = ""): EmergencyPayload {
  const contact = d.emergency_contacts[0];
  const notes = [
    ...(d.emergency_notes ? [d.emergency_notes] : []),
    ...d.active_medications.map((m) => `${m.name} ${m.dosage} (${m.frequency})`),
  ];
  return {
    memberId: d.patient_id,
    memberName: d.full_name,
    condition: d.chronic_conditions.length ? d.chronic_conditions.join(" / ") : "No chronic conditions on record",
    bloodGroup: d.blood_group ?? "Unknown",
    allergies: d.critical_allergies,
    medicalNotes: notes.length ? notes : ["No medical notes on file"],
    emergencyContact: {
      name: contact?.name ?? d.primary_physician_contact ?? "Not on file",
      hospital: contact?.relation ?? "",
      phone: contact?.phone_number ?? "",
    },
    signedTokenPassUrl: passUrl,
    isActive: true,
  };
}
