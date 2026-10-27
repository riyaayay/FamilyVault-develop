"use client";

import { useEffect, useState } from "react";
import { Copy, Lock, ShieldAlert } from "lucide-react";

import { EmergencyAlertDossierModal, type EmergencyPayload } from "@/components/family/EmergencyAlertOverlay";
import { BACKEND_URL } from "@/lib/api";
import {
  compileDossier,
  dossierToPayload,
  getHealthBoard,
  issueEmergencyPass,
  type MemberHealth,
} from "@/lib/health";

function age(dob: string | null): string {
  if (!dob) return "";
  const years = Math.floor((Date.now() - Date.parse(dob)) / (365.25 * 24 * 3600 * 1000));
  return `${years} yrs`;
}

export default function HealthPage() {
  const [members, setMembers] = useState<MemberHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);
  const [dossier, setDossier] = useState<EmergencyPayload | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [passes, setPasses] = useState<Record<string, { url: string; expires: string }>>({});
  const [notice, setNotice] = useState("");

  useEffect(() => {
    getHealthBoard().then(({ data, live }) => {
      setMembers(data);
      setLive(live);
      setLoading(false);
    });
  }, []);

  async function openDossier(m: MemberHealth) {
    setBusy(`dossier-${m.user_id}`);
    const { data } = await compileDossier(m.user_id);
    setBusy(null);
    setDossier(dossierToPayload(data, passes[m.user_id]?.url ?? ""));
  }

  async function createPass(m: MemberHealth) {
    setBusy(`pass-${m.user_id}`);
    const pass = await issueEmergencyPass(m.user_id);
    setBusy(null);
    if (!pass) {
      setNotice("Emergency passes need the live backend and a signed-in session.");
      return;
    }
    const url = `${BACKEND_URL}${pass.pass_path}`;
    setPasses((p) => ({ ...p, [m.user_id]: { url, expires: pass.expires_at } }));
    setNotice(`24-hour pass issued for ${m.full_name}.`);
  }

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setNotice("Pass link copied. Anyone with the link can read the emergency summary until it expires.");
    } catch {
      setNotice(url);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Family Health</h1>
        <p className="text-sm text-muted-foreground">
          Blood groups, allergies and medication for the clan. Records private to another household stay
          hidden unless the member allows emergency access.
          {!loading && !live && " Showing offline demo data."}
        </p>
      </div>

      {notice && (
        <p role="status" aria-live="polite" className="rounded border p-3 text-sm break-all">
          {notice}
        </p>
      )}

      {loading && <p className="text-sm text-muted-foreground">Loading health records…</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {members.map((m) => {
          const r = m.record;
          const pass = passes[m.user_id];
          return (
            <section key={m.user_id} className="flex flex-col gap-3 rounded-lg border p-4">
              <header className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-sm font-medium">{m.full_name}</h2>
                  <p className="text-xs text-muted-foreground">{age(m.date_of_birth)}</p>
                </div>
                {r?.blood_group && (
                  <span className="shrink-0 rounded bg-red-600/10 px-2 py-0.5 text-xs font-semibold text-red-600">
                    {r.blood_group}
                  </span>
                )}
              </header>

              {m.restricted && (
                <p className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Lock className="h-3.5 w-3.5" aria-hidden /> Private to their household
                </p>
              )}
              {!m.has_record && <p className="text-xs text-muted-foreground">No health record on file yet.</p>}

              {r && (
                <dl className="space-y-2 text-xs">
                  {r.allergies.length > 0 && (
                    <div>
                      <dt className="flex items-center gap-1 font-medium text-red-600">
                        <ShieldAlert className="h-3.5 w-3.5" aria-hidden /> Allergies
                      </dt>
                      <dd className="mt-1 flex flex-wrap gap-1">
                        {r.allergies.map((a) => (
                          <span key={a} className="rounded border border-red-500/40 px-1.5 py-0.5">
                            {a}
                          </span>
                        ))}
                      </dd>
                    </div>
                  )}
                  {r.chronic_conditions.length > 0 && (
                    <div>
                      <dt className="font-medium">Conditions</dt>
                      <dd className="text-muted-foreground">{r.chronic_conditions.join(", ")}</dd>
                    </div>
                  )}
                  {r.current_medications.length > 0 && (
                    <div>
                      <dt className="font-medium">Medication</dt>
                      <dd className="text-muted-foreground">
                        {r.current_medications.map((med) => `${med.name} ${med.dosage}`).join(", ")}
                      </dd>
                    </div>
                  )}
                  {r.emergency_notes && <p className="text-muted-foreground">{r.emergency_notes}</p>}
                </dl>
              )}

              {pass && (
                <div className="rounded border border-dashed p-2 text-xs">
                  <p className="font-medium">Emergency pass</p>
                  <p className="text-muted-foreground">Expires {new Date(pass.expires).toLocaleString()}</p>
                  <button
                    type="button"
                    onClick={() => copy(pass.url)}
                    className="mt-1 inline-flex items-center gap-1 underline"
                  >
                    <Copy className="h-3 w-3" aria-hidden /> Copy link
                  </button>
                </div>
              )}

              {!m.restricted && (
                <div className="mt-auto flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => openDossier(m)}
                    className="rounded bg-red-600 px-3 py-1.5 text-sm text-white disabled:opacity-50"
                  >
                    {busy === `dossier-${m.user_id}` ? "Compiling…" : "Red Alert dossier"}
                  </button>
                  <button
                    type="button"
                    disabled={busy !== null}
                    onClick={() => createPass(m)}
                    className="rounded border px-3 py-1.5 text-sm disabled:opacity-50"
                  >
                    {busy === `pass-${m.user_id}` ? "Issuing…" : "24h pass"}
                  </button>
                </div>
              )}
            </section>
          );
        })}
      </div>

      <EmergencyAlertDossierModal
        alertData={dossier ?? undefined}
        isOpen={dossier !== null}
        onClose={() => setDossier(null)}
      />
    </div>
  );
}
