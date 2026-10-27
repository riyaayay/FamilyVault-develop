"use client";

import { useEffect, useState } from "react";
import { getCapsules, unlockCapsule, countdown, type Capsule } from "@/lib/vault";
import TrusteeSignatureModal from "@/components/vault/TrusteeSignatureModal";

const STATUS_LABEL: Record<string, string> = {
    ACTIVE: "Active",
    LOCKED: "Sealed",
    TRUSTEE_PENDING: "Awaiting trustees",
    RELEASED: "Unlocked",
};

export default function VaultPage() {
    const [capsules, setCapsules] = useState<Capsule[]>([]);
    const [loading, setLoading] = useState(true);
    // null until mounted, so server and client render the same first frame.
    const [now, setNow] = useState<number | null>(null);
    const [selected, setSelected] = useState<Capsule | null>(null);
    const [notice, setNotice] = useState("");

    useEffect(() => {
        getCapsules().then((list) => {
            setCapsules(list);
            setLoading(false);
        });
    }, []);

    // Tick every second for the countdowns.
    useEffect(() => {
        setNow(Date.now());
        const timer = setInterval(() => setNow(Date.now()), 1000);
        return () => clearInterval(timer);
    }, []);

    function replaceCapsule(updated: Capsule) {
        setCapsules((list) => list.map((c) => (c.id === updated.id ? updated : c)));
        setSelected((s) => (s && s.id === updated.id ? updated : s));
    }

    async function handleUnlock(c: Capsule) {
        const result = await unlockCapsule(c.id);
        setNotice(result.message);
        if (result.capsule) replaceCapsule(result.capsule);
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-semibold">Milestone Vault</h1>
                <p className="text-sm text-muted-foreground">
                    Time capsules and digital wills. Items unlock on their date or when enough
                    trustees have signed.
                </p>
            </div>

            {notice && (
                <p role="status" aria-live="polite" className="rounded border p-3 text-sm">
                    {notice}
                </p>
            )}

            {loading && <p className="text-sm text-muted-foreground">Loading vault...</p>}

            {!loading && capsules.length === 0 && (
                <p className="text-sm text-muted-foreground">No sealed capsules or wills yet.</p>
            )}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {capsules.map((c) => {
                    const released = c.status === "RELEASED";
                    const unlockMs = c.unlockAt ? Date.parse(c.unlockAt) : 0;
                    const remaining = now !== null && unlockMs ? unlockMs - now : null;
                    const dateReached = remaining !== null && remaining <= 0;
                    const percent =
                        c.required > 0 ? Math.min(100, (c.signedBy.length / c.required) * 100) : 0;

                    return (
                        <div key={c.id} className="flex flex-col gap-3 rounded-lg border p-4">
                            <div>
                                <div className="flex items-start justify-between gap-2">
                                    <h2 className="break-all text-sm font-medium">{c.title}</h2>
                                    <span className="shrink-0 rounded border px-2 py-0.5 text-xs">
                                        {STATUS_LABEL[c.status] ?? c.status}
                                    </span>
                                </div>
                                {c.description && (
                                    <p className="mt-1 text-xs text-muted-foreground">{c.description}</p>
                                )}
                            </div>

                            {!released && remaining !== null && (
                                <p className="text-sm tabular-nums">{countdown(remaining)}</p>
                            )}
                            {released && <p className="text-sm">Unlocked</p>}

                            {c.required > 0 && (
                                <div>
                                    <div className="flex justify-between text-xs">
                                        <span>Trustee signatures</span>
                                        <span>
                                            {c.signedBy.length} of {c.required}
                                        </span>
                                    </div>
                                    <div className="mt-1 h-1.5 w-full rounded bg-muted">
                                        <div
                                            className="h-1.5 rounded bg-primary"
                                            style={{ width: `${percent}%` }}
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="mt-auto flex gap-2">
                                {!released && c.required > 0 && (
                                    <button
                                        type="button"
                                        onClick={() => setSelected(c)}
                                        className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground"
                                    >
                                        Review and sign
                                    </button>
                                )}
                                {!released && dateReached && (
                                    <button
                                        type="button"
                                        onClick={() => handleUnlock(c)}
                                        className="rounded border px-3 py-1.5 text-sm"
                                    >
                                        Unlock
                                    </button>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {selected && (
                <TrusteeSignatureModal
                    capsule={selected}
                    onClose={() => setSelected(null)}
                    onSigned={replaceCapsule}
                />
            )}
        </div>
    );
}