// Milestone vault data layer. Same pattern as media-inbox.ts: try the Core
// Backend first, fall back to mock data if it is unreachable.
//
// Backend (Runeet, backend/app/api/v1/endpoints/vault.py), prefix /api/v1/vault:
//   GET   /                -> { data: [DocumentResponse] }
//   POST  /{id}/sign       -> records the caller as a trustee approval
//   PATCH /{id}/unlock     -> releases the capsule if the unlock date has passed
// A capsule is a document with a capsule_status of ACTIVE / LOCKED /
// TRUSTEE_PENDING / RELEASED. The server decides when something unlocks; the
// countdown here is display only.
//
// All vault routes need the logged-in user. getAccessToken() below is the one
// place to plug the session token in. With no token the backend answers 401
// and the page falls back to mock data.

import { VIEWER_ID } from "./media-inbox";
import { createClient } from "./supabase/client";

export type CapsuleStatus = "ACTIVE" | "LOCKED" | "TRUSTEE_PENDING" | "RELEASED";

export type Capsule = {
    id: string;
    title: string;
    description: string;
    category: string;
    status: CapsuleStatus;
    unlockAt: string; // ISO timestamp, empty when there is no date lock
    required: number; // trustee signatures needed, 0 means none
    signedBy: string[]; // user ids of trustees who have signed
};

export type ActionResult = {
    ok: boolean;
    message: string;
    capsule: Capsule | null;
};

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL;

// True when the list came from mock data. Actions then stay local, because
// mock ids are not real UUIDs and the backend would reject them.
let usingMock = !BACKEND_URL;

// Names for the seed.py person ids we know about. Anyone else shows a short id.
const KNOWN_NAMES: Record<string, string> = {
    "00000000-0000-0000-0000-000000000003": "David Vance",
    "00000000-0000-0000-0000-000000000004": "Sarah Vance",
    "00000000-0000-0000-0000-000000000007": "Robert Vance",
    "00000000-0000-0000-0000-000000000008": "Lucas Vance",
};

export function nameFor(userId: string): string {
    return KNOWN_NAMES[userId] ?? `Trustee ${userId.slice(0, 8)}`;
}

export function countdown(ms: number): string {
    if (ms <= 0) return "Unlock date reached";
    const total = Math.floor(ms / 1000);
    const d = Math.floor(total / 86400);
    const h = Math.floor((total % 86400) / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${d}d ${h}h ${m}m ${s}s`;
}

// Mock data from the Sprint 5 PDF. The viewer (Lucas) signing the will takes
// it from 1 of 2 to 2 of 2 and releases it.
const mockCapsules: Capsule[] = [
    {
        id: "cap_mock_will",
        title: "Arthur_Ancestral_Will.pdf",
        description: "Digital will and land deeds for the Vance clan.",
        category: "LEGACY_WILL",
        status: "TRUSTEE_PENDING",
        unlockAt: "",
        required: 2,
        signedBy: ["00000000-0000-0000-0000-000000000003"],
    },
    {
        id: "cap_mock_birthday",
        title: "Sophia_18th_Birthday.mp4",
        description: "Milestone time capsule for Sophia.",
        category: "MEMORABILIA",
        status: "LOCKED",
        unlockAt: "2026-11-20T00:00:00Z",
        required: 0,
        signedBy: [],
    },
    {
        id: "cap_mock_letter",
        title: "Eleanor_Letter_To_Grandchildren.pdf",
        description: "Released time capsule.",
        category: "MEMORABILIA",
        status: "RELEASED",
        unlockAt: "2026-06-01T00:00:00Z",
        required: 0,
        signedBy: [],
    },
];

// Returns the Supabase session access token, or "" when nobody is signed in
// (including the demo login, which never creates a real session).
async function getAccessToken(): Promise<string> {
    try {
        const supabase = createClient();
        const { data } = await supabase.auth.getSession();
        return data.session?.access_token ?? "";
    } catch (err) {
        console.warn("[vault] could not read session:", err);
        return "";
    }
}

async function authHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
}

// Maps one backend DocumentResponse to a Capsule.
function normalizeCapsule(raw: any): Capsule {
    return {
        id: raw.id,
        title: raw.title ?? "Untitled",
        description: raw.description ?? "",
        category: raw.category ?? "",
        status: raw.capsule_status ?? "ACTIVE",
        unlockAt: raw.time_capsule_unlock_at ?? "",
        required: raw.trustee_approvals_required ?? 0,
        signedBy: (raw.trustee_approvals_received ?? []).map(String),
    };
}

// The vault also holds plain documents. Only date-locked, trustee-governed or
// non-ACTIVE items belong on this page.
function isCapsule(c: Capsule): boolean {
    return c.status !== "ACTIVE" || c.unlockAt !== "" || c.required > 0;
}

export async function getCapsules(): Promise<Capsule[]> {
    if (!BACKEND_URL) {
        usingMock = true;
        return [...mockCapsules];
    }
    try {
        // Trailing slash matters: without it FastAPI redirects and the
        // Authorization header can be dropped.
        const res = await fetch(`${BACKEND_URL}/api/v1/vault/`, {
            headers: await authHeaders(),
            cache: "no-store",
        });
        if (!res.ok) throw new Error(`getCapsules fetch failed: ${res.status}`);
        const json = await res.json();
        usingMock = false;
        return (json.data ?? []).map(normalizeCapsule).filter(isCapsule);
    } catch (err) {
        console.warn("[vault] getCapsules falling back to mock data:", err);
        usingMock = true;
        return [...mockCapsules];
    }
}

// Sends one action to the backend and turns the reply into an ActionResult.
async function sendAction(
    id: string,
    action: "sign" | "unlock",
    method: "POST" | "PATCH",
): Promise<ActionResult> {
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/vault/${id}/${action}`, {
            method,
            headers: await authHeaders(),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok) {
            return {
                ok: false,
                message: String(json.detail ?? json.message ?? `Request failed (${res.status})`),
                capsule: null,
            };
        }
        return {
            ok: true,
            message: String(json.message ?? "Done"),
            capsule: json.data ? normalizeCapsule(json.data) : null,
        };
    } catch (err) {
        console.warn(`[vault] ${action} failed:`, err);
        return { ok: false, message: "Could not reach the server", capsule: null };
    }
}

// Record the logged-in user's trustee signature.
export async function signCapsule(id: string): Promise<ActionResult> {
    if (!BACKEND_URL || usingMock) {
        const i = mockCapsules.findIndex((c) => c.id === id);
        if (i < 0) return { ok: false, message: "Capsule not found", capsule: null };
        const cap = mockCapsules[i];
        if (cap.required <= 0) {
            return { ok: false, message: "This item does not need trustee signatures", capsule: null };
        }
        const signedBy = cap.signedBy.includes(VIEWER_ID) ? cap.signedBy : [...cap.signedBy, VIEWER_ID];
        const status = signedBy.length >= cap.required ? "RELEASED" : "TRUSTEE_PENDING";
        const updated: Capsule = { ...cap, signedBy, status };
        mockCapsules[i] = updated;
        return {
            ok: true,
            message: `Trustee signature recorded. Quorum: ${signedBy.length}/${cap.required}`,
            capsule: updated,
        };
    }
    return sendAction(id, "sign", "POST");
}

// Ask the server to release a capsule whose unlock date has passed. Only call
// this once the date is reached: for trustee-governed items the backend treats
// an earlier unlock call as the caller's signature.
export async function unlockCapsule(id: string): Promise<ActionResult> {
    if (!BACKEND_URL || usingMock) {
        const i = mockCapsules.findIndex((c) => c.id === id);
        if (i < 0) return { ok: false, message: "Capsule not found", capsule: null };
        const cap = mockCapsules[i];
        if (cap.unlockAt === "" || Date.now() < Date.parse(cap.unlockAt)) {
            return { ok: false, message: "Unlock date has not been reached", capsule: null };
        }
        const updated: Capsule = { ...cap, status: "RELEASED" };
        mockCapsules[i] = updated;
        return { ok: true, message: `Time capsule '${cap.title}' released`, capsule: updated };
    }
    return sendAction(id, "unlock", "PATCH");
}