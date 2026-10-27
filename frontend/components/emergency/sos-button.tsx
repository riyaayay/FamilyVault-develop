"use client";

import { useEffect, useState } from "react";
import { Siren, X } from "lucide-react";

import { EmergencyAlertDossierModal, type EmergencyPayload } from "@/components/family/EmergencyAlertOverlay";
import { compileDossier, dossierToPayload, getHealthBoard, triggerRedAlert, type MemberHealth } from "@/lib/health";

// Always-visible Red Alert control (requirements 3.3.4): one tap opens a member
// picker, a second tap broadcasts the alert and opens that member's dossier.
export function SosButton() {
  const [open, setOpen] = useState(false);
  const [members, setMembers] = useState<MemberHealth[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [dossier, setDossier] = useState<EmergencyPayload | null>(null);

  useEffect(() => {
    if (!open || members.length) return;
    getHealthBoard().then(({ data }) => setMembers(data));
  }, [open, members.length]);

  async function raise(member: MemberHealth) {
    setBusyId(member.user_id);
    setNotice("");
    const [{ data, live }, broadcast] = await Promise.all([
      compileDossier(member.user_id),
      triggerRedAlert(member.user_id, "Medical emergency"),
    ]);
    setBusyId(null);
    setOpen(false);
    setNotice(
      broadcast
        ? `Red Alert sent for ${member.full_name}${live ? "" : " (offline demo)"}`
        : `Could not broadcast the alert. Showing ${member.full_name}'s dossier anyway.`,
    );
    setDossier(dossierToPayload(data));
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        className="fixed right-4 top-4 z-50 flex items-center gap-2 rounded-full bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-red-600/30 transition hover:bg-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600"
      >
        <Siren className="h-4 w-4" aria-hidden />
        SOS
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Raise an emergency Red Alert"
          className="fixed right-4 top-16 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-xl border bg-background p-4 shadow-2xl"
        >
          <div className="mb-3 flex items-start justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold">Emergency Red Alert</h2>
              <p className="text-xs text-muted-foreground">
                Who needs help? The family is alerted and their medical dossier opens.
              </p>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close" className="rounded p-1 hover:bg-muted">
              <X className="h-4 w-4" />
            </button>
          </div>
          {members.length === 0 && <p className="text-sm text-muted-foreground">Loading family…</p>}
          <ul className="max-h-72 space-y-1 overflow-y-auto">
            {members.map((m) => (
              <li key={m.user_id}>
                <button
                  type="button"
                  disabled={busyId !== null}
                  onClick={() => raise(m)}
                  className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm hover:border-red-500 hover:bg-red-500/5 disabled:opacity-50"
                >
                  <span>{m.full_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {busyId === m.user_id ? "Sending…" : m.record?.blood_group ?? (m.restricted ? "Private" : "No record")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {notice && (
        <p
          role="status"
          aria-live="assertive"
          className="fixed left-1/2 top-4 z-50 -translate-x-1/2 rounded-full border border-red-500/40 bg-background px-4 py-2 text-sm shadow"
        >
          {notice}
        </p>
      )}

      <EmergencyAlertDossierModal
        alertData={dossier ?? undefined}
        isOpen={dossier !== null}
        onClose={() => {
          setDossier(null);
          setNotice("");
        }}
      />
    </>
  );
}
