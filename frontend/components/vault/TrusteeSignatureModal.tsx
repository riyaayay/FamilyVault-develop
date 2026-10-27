"use client";

import { useEffect, useState } from "react";
import { signCapsule, nameFor, type Capsule } from "@/lib/vault";

type Props = {
    capsule: Capsule;
    onClose: () => void;
    onSigned: (updated: Capsule) => void;
};

export default function TrusteeSignatureModal({ capsule, onClose, onSigned }: Props) {
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState("");

    const signed = capsule.signedBy.length;
    const released = capsule.status === "RELEASED";
    const percent = capsule.required > 0 ? Math.min(100, (signed / capsule.required) * 100) : 0;

    // Close on Escape.
    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === "Escape") onClose();
        }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);

    async function handleSign() {
        setBusy(true);
        const result = await signCapsule(capsule.id);
        setBusy(false);
        setMessage(result.message);
        if (result.capsule) onSigned(result.capsule);
    }

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={onClose}
        >
            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="trustee-modal-title"
                className="w-full max-w-md rounded-lg border bg-background p-6 shadow-lg"
                onClick={(e) => e.stopPropagation()}
            >
                <h2 id="trustee-modal-title" className="text-lg font-semibold">
                    Trustee signature
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">{capsule.title}</p>

                <div className="mt-4">
                    <div className="flex justify-between text-sm">
                        <span>Signatures</span>
                        <span>
                            {signed} of {capsule.required}
                        </span>
                    </div>
                    <div className="mt-1 h-2 w-full rounded bg-muted">
                        <div className="h-2 rounded bg-primary" style={{ width: `${percent}%` }} />
                    </div>
                </div>

                <div className="mt-4">
                    <p className="text-sm font-medium">Signed by</p>
                    {signed === 0 ? (
                        <p className="text-sm text-muted-foreground">No signatures yet.</p>
                    ) : (
                        <ul className="mt-1 space-y-1 text-sm">
                            {capsule.signedBy.map((id) => (
                                <li key={id}>{nameFor(id)}</li>
                            ))}
                        </ul>
                    )}
                </div>

                <p className="mt-4 text-xs text-muted-foreground">
                    Your signature is recorded against your account. The capsule is released once the
                    required number of signatures is reached.
                </p>

                {message && (
                    <p role="status" aria-live="polite" className="mt-3 text-sm">
                        {message}
                    </p>
                )}

                <div className="mt-6 flex justify-end gap-2">
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded border px-3 py-1.5 text-sm"
                    >
                        Close
                    </button>
                    <button
                        type="button"
                        onClick={handleSign}
                        disabled={busy || released}
                        className="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
                    >
                        {released ? "Released" : busy ? "Signing..." : "Sign as trustee"}
                    </button>
                </div>
            </div>
        </div>
    );
}