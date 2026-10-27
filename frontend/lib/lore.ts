// Generational Lore timeline data layer.
// GET /api/v1/media/timeline -> published photo/audio/video memories for the clan, newest first.
// GET /api/v1/users/          -> names for the "shared by" line.

import { BACKEND_URL, backendFetch, mediaUrl } from "./api";

export type MemoryKind = "image" | "audio" | "video";

export type Memory = {
  id: string;
  title: string;
  kind: MemoryKind;
  url: string;
  sharedBy: string;
  taggedCount: number;
  date: string; // ISO
};

type MediaDto = {
  id: string;
  media_title: string | null;
  media_type: string;
  r2_storage_key: string;
  uploader_id: string;
  matched_face_ids: string[];
  created_at: string | null;
};

type UserDto = { id: string; full_name: string };

function kindOf(mime: string): MemoryKind {
  const top = mime.split("/")[0];
  return top === "audio" || top === "video" ? top : "image";
}

// Mirrors the published media in backend/scripts/seed.py.
const mockMemories: Memory[] = [
  { id: "lore-1", title: "Sophia's school annual day", kind: "image", url: "/intro/08.jpg", sharedBy: "Michael Vance", taggedCount: 1, date: "2026-03-02T00:00:00Z" },
  { id: "lore-2", title: "Dadi's recipe: kadhi chawal (voice note)", kind: "audio", url: "", sharedBy: "Eleanor Vance", taggedCount: 0, date: "2026-01-14T00:00:00Z" },
  { id: "lore-3", title: "Diwali at the Haveli", kind: "image", url: "/intro/03.jpg", sharedBy: "David Vance", taggedCount: 1, date: "2025-10-20T00:00:00Z" },
];

export async function getLore(): Promise<{ data: Memory[]; live: boolean }> {
  if (!BACKEND_URL) return { data: mockMemories, live: false };
  try {
    const [media, users] = await Promise.all([
      backendFetch<MediaDto[]>("/api/v1/media/timeline"),
      backendFetch<UserDto[]>("/api/v1/users/").catch(() => [] as UserDto[]),
    ]);
    const names = new Map(users.map((u) => [u.id, u.full_name]));
    return {
      live: true,
      data: media.map((m) => ({
        id: m.id,
        title: m.media_title ?? "Untitled memory",
        kind: kindOf(m.media_type),
        url: mediaUrl(m.r2_storage_key),
        sharedBy: names.get(m.uploader_id) ?? "A family member",
        taggedCount: m.matched_face_ids?.length ?? 0,
        date: m.created_at ?? "",
      })),
    };
  } catch (err) {
    console.warn("[lore] falling back to mock data:", err);
    return { data: mockMemories, live: false };
  }
}
