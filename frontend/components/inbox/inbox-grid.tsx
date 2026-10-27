"use client";

import React from "react";
import type { InboxItem } from "@/lib/media-inbox";
import { confidenceBand, triageMedia, triageBatch } from "@/lib/media-inbox";
import type { FamilyMember } from "@/lib/nuclear-family";

const ROLE_LABELS: Record<string, string> = {
    ADMIN: "Admin",
    MEMBER: "Member",
    CHILD: "Child",
    VIEWER: "Viewer",
};

const RELATION_LABELS: Record<string, string> = {
    HEAD: "Head of family",
    SPOUSE: "Spouse of the family head",
    CHILD: "Child of the family head",
    EXTENDED: "Extended family",
};

const BAND_LABELS = {
    high: "Auto-tag",
    review: "Needs review",
    low: "Low match",
};

const BAND_BOX = {
    high: "border-green-500",
    review: "border-amber-500",
    low: "border-red-500",
};

const BAND_BAR = {
    high: "bg-green-500",
    review: "bg-amber-500",
    low: "bg-red-500",
};

// TODO: read the household name from the household API.
const HOUSEHOLD_NAME = "David & Sarah Household";

function initialsOf(name: string) {
    const parts = name.trim().split(/\s+/);
    const first = parts[0]?.[0] ?? "?";
    const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
    return (first + last).toUpperCase();
}

export function InboxGrid({
    initialItems,
    members,
}: {
    initialItems: InboxItem[];
    members: FamilyMember[];
}) {
    const [items, setItems] = React.useState(initialItems);
    const [profileItemId, setProfileItemId] = React.useState<string | null>(null);
    const [selected, setSelected] = React.useState<string[]>([]);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState("");
    // natural pixel size of each loaded image, used to scale the face boxes
    const [sizes, setSizes] = React.useState<Record<string, { w: number; h: number }>>({});

    const pendingItems = items.filter((i) => i.status === "pending");
    const pendingCount = pendingItems.length;

    // close the profile popup with the Escape key
    React.useEffect(() => {
        function onKeyDown(e: KeyboardEvent) {
            if (e.key === "Escape") setProfileItemId(null);
        }
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, []);

    async function decide(mediaId: string, status: "accepted" | "rejected") {
        setError("");
        setBusy(true);
        const ok = await triageMedia(mediaId, status);
        setBusy(false);
        if (!ok) {
            setError("Could not save the decision. Please try again.");
            return;
        }
        setItems((prev) =>
            prev.map((i) => (i.mediaId === mediaId ? { ...i, status } : i)),
        );
        setSelected((prev) => prev.filter((id) => id !== mediaId));
    }

    async function decideSelected(status: "accepted" | "rejected") {
        if (selected.length === 0) return;
        setError("");
        setBusy(true);
        const done = await triageBatch(selected, status);
        setBusy(false);
        setItems((prev) =>
            prev.map((i) => (done.includes(i.mediaId) ? { ...i, status } : i)),
        );
        setSelected((prev) => prev.filter((id) => !done.includes(id)));
        if (done.length < selected.length) {
            setError(`${selected.length - done.length} of ${selected.length} could not be saved.`);
        }
    }

    function toggleSelected(mediaId: string) {
        setSelected((prev) =>
            prev.includes(mediaId)
                ? prev.filter((id) => id !== mediaId)
                : [...prev, mediaId],
        );
    }

    function selectAllPending() {
        setSelected(pendingItems.map((i) => i.mediaId));
    }

    function findMember(personId: string) {
        return members.find((m) => m.id === personId);
    }

    const profileItem = items.find((i) => i.mediaId === profileItemId);
    const profileMember = profileItem
        ? findMember(profileItem.uploadedBy)
        : undefined;

    if (items.length === 0) {
        return (
            <p className="text-sm text-muted-foreground">
                No media is waiting for review.
            </p>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
                <p className="text-sm text-muted-foreground">
                    {pendingCount} waiting for review
                </p>
                {pendingCount > 0 ? (
                    <button
                        onClick={selectAllPending}
                        className="rounded-md border px-3 py-1 text-sm border-border hover:bg-muted"
                    >
                        Select all pending
                    </button>
                ) : null}
            </div>

            {selected.length > 0 ? (
                <div className="sticky top-0 z-10 flex flex-wrap items-center gap-3 rounded-md border border-border bg-background p-3">
                    <span className="text-sm text-foreground">
                        {selected.length} selected
                    </span>
                    <button
                        disabled={busy}
                        onClick={() => decideSelected("accepted")}
                        className="rounded-md border px-3 py-2 text-sm border-foreground bg-foreground text-background disabled:opacity-50"
                    >
                        Accept selected
                    </button>
                    <button
                        disabled={busy}
                        onClick={() => decideSelected("rejected")}
                        className="rounded-md border px-3 py-2 text-sm border-border hover:bg-muted disabled:opacity-50"
                    >
                        Reject selected
                    </button>
                    <button
                        disabled={busy}
                        onClick={() => setSelected([])}
                        className="rounded-md border px-3 py-2 text-sm border-border hover:bg-muted disabled:opacity-50"
                    >
                        Clear
                    </button>
                </div>
            ) : null}

            {error ? (
                <p role="alert" className="text-sm text-red-500">
                    {error}
                </p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((item) => {
                    const member = findMember(item.uploadedBy);
                    const contributor = member
                        ? member.fullName
                        : item.uploadedByName || "Unknown member";
                    const isImage = item.mediaType === "image";
                    const size = sizes[item.mediaId];
                    const isPending = item.status === "pending";

                    // the weakest face decides how the whole photo is labelled
                    const hasFaces = item.faces.length > 0;
                    const lowest = hasFaces
                        ? Math.min(...item.faces.map((f) => f.confidence))
                        : 0;
                    const band = confidenceBand(lowest);
                    const percent = Math.round(lowest * 100);

                    const tag = (
                        <>
                            <span className="text-sm font-medium text-foreground">
                                Contributed by {contributor}
                            </span>
                            {item.kinship ? (
                                <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted-foreground">
                                    {item.kinship}
                                </span>
                            ) : null}
                        </>
                    );

                    return (
                        <div
                            key={item.mediaId}
                            className="rounded-md border border-border p-4 space-y-3"
                        >
                            {isPending ? (
                                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={selected.includes(item.mediaId)}
                                        onChange={() => toggleSelected(item.mediaId)}
                                        aria-label={`Select media from ${contributor}`}
                                    />
                                    Select
                                </label>
                            ) : null}

                            {isImage && item.thumbnailUrl ? (
                                <div className="relative w-full overflow-hidden rounded-md bg-muted">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                        src={item.thumbnailUrl}
                                        alt={`Uploaded by ${contributor}`}
                                        className="block h-auto w-full"
                                        onLoad={(e) => {
                                            const img = e.currentTarget;
                                            setSizes((prev) => ({
                                                ...prev,
                                                [item.mediaId]: {
                                                    w: img.naturalWidth,
                                                    h: img.naturalHeight,
                                                },
                                            }));
                                        }}
                                    />
                                    {size
                                        ? item.faces.map((face, idx) => {
                                            const [x1, y1, x2, y2] = face.bbox;
                                            const faceBand = confidenceBand(face.confidence);
                                            return (
                                                <div
                                                    key={face.faceId}
                                                    className={`absolute border-2 ${BAND_BOX[faceBand]}`}
                                                    style={{
                                                        left: `${(x1 / size.w) * 100}%`,
                                                        top: `${(y1 / size.h) * 100}%`,
                                                        width: `${((x2 - x1) / size.w) * 100}%`,
                                                        height: `${((y2 - y1) / size.h) * 100}%`,
                                                    }}
                                                >
                                                    <span className="absolute -top-5 left-0 rounded bg-black/70 px-1 text-xs text-white">
                                                        {idx + 1}
                                                    </span>
                                                </div>
                                            );
                                        })
                                        : null}
                                </div>
                            ) : (
                                <div className="aspect-video rounded-md bg-muted flex items-center justify-center overflow-hidden">
                                    <span className="text-sm text-muted-foreground">
                                        {isImage ? "No preview" : item.mediaType}
                                    </span>
                                </div>
                            )}

                            {hasFaces ? (
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                                        <span>{BAND_LABELS[band]}</span>
                                        <span>Lowest match {percent}%</span>
                                    </div>
                                    <div
                                        className="h-2 w-full rounded bg-muted"
                                        role="meter"
                                        aria-valuemin={0}
                                        aria-valuemax={100}
                                        aria-valuenow={percent}
                                        aria-label="Lowest face match confidence"
                                    >
                                        <div
                                            className={`h-2 rounded ${BAND_BAR[band]}`}
                                            style={{ width: `${percent}%` }}
                                        />
                                    </div>
                                    <ul className="space-y-1">
                                        {item.faces.map((face, idx) => (
                                            <li
                                                key={face.faceId}
                                                className="flex items-center gap-2 text-xs"
                                            >
                                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-foreground">
                                                    {face.name ? initialsOf(face.name) : "?"}
                                                </span>
                                                <span className="text-foreground">
                                                    {idx + 1}. {face.name || "Unknown face"}
                                                </span>
                                                <span className="text-muted-foreground">
                                                    {Math.round(face.confidence * 100)}%
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            ) : null}

                            <div className="space-y-1">
                                {member ? (
                                    <button
                                        onClick={() => setProfileItemId(item.mediaId)}
                                        aria-label={`View profile of ${contributor}`}
                                        className="flex flex-wrap items-center gap-2 text-left hover:underline"
                                    >
                                        {tag}
                                    </button>
                                ) : (
                                    <div className="flex flex-wrap items-center gap-2">{tag}</div>
                                )}
                                <p className="text-sm text-muted-foreground">
                                    {item.uploadedAt ? item.uploadedAt.slice(0, 10) : "Date unknown"}
                                    {item.pendingFaces > 0
                                        ? `, ${item.pendingFaces} ${item.pendingFaces === 1 ? "face" : "faces"} to confirm`
                                        : ""}
                                </p>
                            </div>

                            {isPending ? (
                                <div className="flex gap-3">
                                    <button
                                        disabled={busy}
                                        onClick={() => decide(item.mediaId, "accepted")}
                                        className="rounded-md border px-3 py-2 text-sm border-foreground bg-foreground text-background disabled:opacity-50"
                                    >
                                        Accept
                                    </button>
                                    <button
                                        disabled={busy}
                                        onClick={() => decide(item.mediaId, "rejected")}
                                        className="rounded-md border px-3 py-2 text-sm border-border hover:bg-muted disabled:opacity-50"
                                    >
                                        Reject
                                    </button>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground">
                                    {item.status === "accepted" ? "Accepted" : "Rejected"}
                                </p>
                            )}
                        </div>
                    );
                })}
            </div>

            {profileItem && profileMember ? (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
                    onClick={() => setProfileItemId(null)}
                >
                    <div
                        role="dialog"
                        aria-modal="true"
                        aria-label={`Profile of ${profileMember.fullName}`}
                        className="w-full max-w-sm rounded-md border border-border bg-background p-6 space-y-4"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center gap-3">
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-sm font-medium text-foreground">
                                {profileMember.initials}
                            </div>
                            <div>
                                <p className="text-base font-semibold text-foreground">
                                    {profileMember.fullName}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    {RELATION_LABELS[profileMember.relationToHead] ??
                                        profileMember.relationToHead}
                                </p>
                            </div>
                        </div>

                        <dl className="space-y-2 text-sm">
                            <div>
                                <dt className="text-muted-foreground">Household</dt>
                                <dd className="text-foreground">{HOUSEHOLD_NAME}</dd>
                            </div>
                            <div>
                                <dt className="text-muted-foreground">Access role</dt>
                                <dd className="text-foreground">
                                    {ROLE_LABELS[profileMember.role] ?? profileMember.role}
                                </dd>
                            </div>
                            {profileItem.kinship ? (
                                <div>
                                    <dt className="text-muted-foreground">Related to you as</dt>
                                    <dd className="text-foreground">{profileItem.kinship}</dd>
                                </div>
                            ) : null}
                            <div>
                                <dt className="text-muted-foreground">Bio</dt>
                                <dd className="text-foreground">No bio added yet.</dd>
                            </div>
                        </dl>

                        <button
                            autoFocus
                            onClick={() => setProfileItemId(null)}
                            className="rounded-md border px-3 py-2 text-sm border-border hover:bg-muted"
                        >
                            Close
                        </button>
                    </div>
                </div>
            ) : null}
        </div>
    );
}