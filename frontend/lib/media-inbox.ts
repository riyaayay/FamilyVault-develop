// Media inbox data layer. Mirrors the pattern in nuclear-family.ts: try the
// live services first, fall back to mock data if they are unreachable.
//
// Inbox: GET /api/v1/media/inbox (Core Backend)
//   -> { success, message, data: [MediaContributionResponse] }
// The backend has no bbox, face names or thumbnail URL yet. Faces are built
// from the confidence_scores dict ({ face_id: score }), bbox stays [0,0,0,0].
//
// Kinship: GET /api/graph/kinship?person_a=&person_b= (graph-service)
// returns { pathLength, label }. Today `label` is generic, for example
// "parent/child (1 gen)". Cultural terms (Chacha, Bua, Mama) are planned
// for the same endpoint, so the pill just shows whatever `label` says.
//
// Triage: PATCH /api/v1/media/{id}/triage and POST /api/v1/media/batch-triage.
// Backend status values are AUTO_PUBLISHED / REJECTED (it also accepts
// APPROVED and normalizes it to AUTO_PUBLISHED).
// With no backend URL configured, or when the inbox is on mock data, triage
// runs in mock mode and always succeeds.

import { authHeaders, mediaUrl } from "./api";
export type InboxStatus = "pending" | "accepted" | "rejected";

export type InboxFace = {
    faceId: string;
    bbox: [number, number, number, number]; // x1, y1, x2, y2 in image pixels
    confidence: number; // 0 when there is no match at all
    name: string; // best match or best suggestion, empty if none
    suggested: { personId: string; name: string; confidence: number }[];
};

export type InboxItem = {
    mediaId: string;
    mediaType: string; // "image" | "video" | "audio" | ...
    thumbnailUrl: string; // empty string when there is nothing to show
    uploadedBy: string; // person id of the contributor
    uploadedByName: string; // display fallback when the id is not in the roster
    uploadedAt: string; // ISO timestamp, may be empty
    pendingFaces: number;
    kinship: string; // how the contributor relates to the viewer, empty if unknown
    status: InboxStatus;
    faces: InboxFace[];
};

// Sprint 4 spec: >= 0.85 auto-tags, 0.70 to 0.85 needs a head's decision.
export const AUTO_THRESHOLD = 0.85;
export const INBOX_FLOOR = 0.7;

// True for the canned 00000000-0000-0000-0000-0000000000NN seed ids and real
// DB ids alike. Mock inbox items (e.g. "med_mock_001") are NOT UUIDs and must
// never be posted to backend endpoints that type media ids as List[UUID].
function isUuid(id: string): boolean {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id.trim());
}

export function confidenceBand(score: number): "high" | "review" | "low" {
    if (score >= AUTO_THRESHOLD) return "high";
    if (score >= INBOX_FLOOR) return "review";
    return "low";
}

// TODO: replace with the logged-in user's person id once session context is
// wired. Mock viewer is Lucas Vance (seed.py PERSON_IDS 8).
export const VIEWER_ID = "00000000-0000-0000-0000-000000000008";

// Member ids are the seed.py PERSON_IDS UUIDs (David 3, Sarah 4, Robert 7).
// Kinship labels are mock values as seen from the viewer (Lucas).
const mockInbox: InboxItem[] = [
    {
        mediaId: "med_mock_001",
        mediaType: "image",
        thumbnailUrl: "/group1.jpg",
        uploadedBy: "00000000-0000-0000-0000-000000000003",
        uploadedByName: "David Vance",
        uploadedAt: "2026-09-06T12:00:00Z",
        pendingFaces: 1,
        kinship: "Father",
        status: "pending",
        faces: [
            {
                faceId: "f1",
                bbox: [100, 50, 220, 170],
                confidence: 0.92,
                name: "David Vance",
                suggested: [],
            },
            {
                faceId: "f2",
                bbox: [300, 80, 410, 190],
                confidence: 0.78,
                name: "Robert Vance",
                suggested: [
                    {
                        personId: "00000000-0000-0000-0000-000000000007",
                        name: "Robert Vance",
                        confidence: 0.78,
                    },
                ],
            },
        ],
    },
    {
        mediaId: "med_mock_002",
        mediaType: "audio",
        thumbnailUrl: "",
        uploadedBy: "00000000-0000-0000-0000-000000000007",
        uploadedByName: "Robert Vance",
        uploadedAt: "2026-09-05T09:30:00Z",
        pendingFaces: 0,
        kinship: "Chacha",
        status: "pending",
        faces: [],
    },
    {
        mediaId: "med_mock_003",
        mediaType: "image",
        thumbnailUrl: "/group2.jpg",
        uploadedBy: "00000000-0000-0000-0000-000000000004",
        uploadedByName: "Sarah Vance",
        uploadedAt: "2026-09-04T18:45:00Z",
        pendingFaces: 3,
        kinship: "Mother",
        status: "pending",
        faces: [
            {
                faceId: "f1",
                bbox: [60, 40, 170, 160],
                confidence: 0.88,
                name: "Sarah Vance",
                suggested: [],
            },
            {
                faceId: "f2",
                bbox: [220, 60, 330, 170],
                confidence: 0.76,
                name: "David Vance",
                suggested: [
                    {
                        personId: "00000000-0000-0000-0000-000000000003",
                        name: "David Vance",
                        confidence: 0.76,
                    },
                ],
            },
            {
                faceId: "f3",
                bbox: [380, 90, 480, 190],
                confidence: 0.72,
                name: "Robert Vance",
                suggested: [
                    {
                        personId: "00000000-0000-0000-0000-000000000007",
                        name: "Robert Vance",
                        confidence: 0.72,
                    },
                ],
            },
        ],
    },
];

const GRAPH_URL = process.env.NEXT_PUBLIC_GRAPH_API_URL;
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL;

// True when the inbox came from mock data. Triage then skips the backend,
// because mock ids are not real UUIDs and the backend would reject them.
let usingMock = !BACKEND_URL;

// Maps one backend MediaContributionResponse to an InboxItem.
// The backend has no bbox or face names yet, so those stay empty; the
// thumbnail is resolved from the storage key. Faces come from the confidence_scores dict ({ face_id: score }).
function normalizeBackendItem(raw: any): InboxItem {
    const scores = raw.confidence_scores ?? {};
    const faces: InboxFace[] = Object.keys(scores).map((faceId) => ({
        faceId,
        bbox: [0, 0, 0, 0],
        confidence: Number(scores[faceId]) || 0,
        name: "",
        suggested: [],
    }));
    return {
        mediaId: raw.id,
        mediaType: String(raw.media_type ?? "image").split("/")[0],
        thumbnailUrl: mediaUrl(raw.r2_storage_key ?? ""),
        uploadedBy: raw.uploader_id ?? "",
        uploadedByName: "",
        uploadedAt: raw.created_at ?? "",
        pendingFaces: faces.filter((f) => f.confidence < AUTO_THRESHOLD).length,
        kinship: "",
        status: "pending",
        faces,
    };
}

export async function getInbox(): Promise<InboxItem[]> {
    if (!BACKEND_URL) {
        usingMock = true;
        return mockInbox;
    }
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/media/inbox`, {
            cache: "no-store",
            headers: await authHeaders(),
        });
        if (!res.ok) throw new Error(`getInbox fetch failed: ${res.status}`);
        const json = await res.json();
        usingMock = false;
        return (json.data ?? []).map(normalizeBackendItem);
    } catch (err) {
        console.warn("[media-inbox] getInbox falling back to mock data:", err);
        usingMock = true;
        return mockInbox;
    }
}

// How is `personId` related to the viewer? Returns the graph service label,
// or `fallback` (mock value or empty string) when it cannot be fetched.
export async function getKinshipLabel(
    personId: string,
    fallback: string,
): Promise<string> {
    if (!GRAPH_URL || !personId) {
        return fallback;
    }
    try {
        const res = await fetch(
            `${GRAPH_URL}/api/graph/kinship?person_a=${VIEWER_ID}&person_b=${personId}`,
            { cache: "no-store", headers: await authHeaders() },
        );
        if (!res.ok) throw new Error(`getKinshipLabel fetch failed: ${res.status}`);
        const data = await res.json();
        return data.label ?? fallback;
    } catch (err) {
        console.warn("[media-inbox] getKinshipLabel falling back:", err);
        return fallback;
    }
}

// Accept or reject one item. Returns true on success.
export async function triageMedia(
    mediaId: string,
    status: "accepted" | "rejected",
): Promise<boolean> {
    if (!BACKEND_URL || !isUuid(mediaId)) {
        return true;
    }
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/media/${mediaId}/triage`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json", ...(await authHeaders()) },
            body: JSON.stringify({
                status: status === "accepted" ? "AUTO_PUBLISHED" : "REJECTED",
            }),
        });
        return res.ok;
    } catch (err) {
        console.warn("[media-inbox] triageMedia failed:", err);
        return false;
    }
}

// Bulk triage: one POST /api/v1/media/batch-triage.
// Response: { success, message, data: { succeeded_ids, failed_ids, ... } }
// Returns the ids that succeeded so the UI can update just those.
export async function triageBatch(
    mediaIds: string[],
    status: "accepted" | "rejected",
): Promise<string[]> {
    if (!BACKEND_URL) {
        return mediaIds;
    }
    // Only real UUIDs belong on the wire: mock inbox ids (e.g. "med_mock_001")
    // are not UUIDs and would be rejected with a 422 by the backend schema.
    const realIds = mediaIds.filter(isUuid);
    const localIds = mediaIds.filter((id) => !isUuid(id));
    if (realIds.length === 0) {
        return mediaIds;
    }
    try {
        const res = await fetch(`${BACKEND_URL}/api/v1/media/batch-triage`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...(await authHeaders()) },
            body: JSON.stringify({
                media_ids: realIds,
                status: status === "accepted" ? "AUTO_PUBLISHED" : "REJECTED",
            }),
        });
        if (!res.ok) {
            if (localIds.length > 0) return localIds;
            return [];
        }
        const json = await res.json();
        const doneIds: string[] = json?.data?.succeeded_ids ?? [];
        return [...localIds, ...doneIds];
    } catch (err) {
        console.warn("[media-inbox] triageBatch failed:", err);
        return localIds;
    }
}