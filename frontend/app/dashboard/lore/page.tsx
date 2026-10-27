export const dynamic = "force-dynamic";

import "@/lib/supabase/server-token";
import { Image as ImageIcon, Mic, Video } from "lucide-react";

import { getLore, type Memory } from "@/lib/lore";

const KIND_ICON = { image: ImageIcon, audio: Mic, video: Video } as const;

function byYear(memories: Memory[]): [string, Memory[]][] {
  const groups = new Map<string, Memory[]>();
  for (const m of memories) {
    const year = m.date ? String(new Date(m.date).getFullYear()) : "Undated";
    groups.set(year, [...(groups.get(year) ?? []), m]);
  }
  return [...groups.entries()];
}

function MemoryMedia({ memory }: { memory: Memory }) {
  if (!memory.url) {
    return (
      <div className="flex h-24 items-center justify-center rounded bg-muted text-xs text-muted-foreground">
        No playable file attached to this memory
      </div>
    );
  }
  if (memory.kind === "audio") return <audio controls preload="none" src={memory.url} className="w-full" />;
  if (memory.kind === "video") return <video controls preload="metadata" src={memory.url} className="w-full rounded" />;
  // Media can come from R2 or the biometrics service, so a plain <img> avoids next/image host config.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={memory.url} alt={memory.title} loading="lazy" className="aspect-video w-full rounded object-cover" />;
}

export default async function LorePage() {
  const { data: memories, live } = await getLore();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Generational Lore</h1>
        <p className="text-sm text-muted-foreground">
          Photos, voice notes and videos the family has accepted into its shared story.
          {!live && " Showing offline demo data."}
        </p>
      </div>

      {memories.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No memories yet. Upload a photo from Nuclear Family; once it is accepted it appears here.
        </p>
      )}

      {byYear(memories).map(([year, items]) => (
        <section key={year} aria-labelledby={`lore-${year}`} className="space-y-3">
          <h2 id={`lore-${year}`} className="font-mono text-sm text-muted-foreground">
            {year}
          </h2>
          <ol className="space-y-4 border-l pl-4 sm:pl-6">
            {items.map((m) => {
              const Icon = KIND_ICON[m.kind];
              return (
                <li key={m.id} className="relative">
                  <span className="absolute -left-[1.3rem] top-1 flex h-5 w-5 items-center justify-center rounded-full border bg-background sm:-left-[2.05rem]">
                    <Icon className="h-3 w-3" aria-hidden />
                  </span>
                  <article className="max-w-xl space-y-2 rounded-lg border p-3">
                    <MemoryMedia memory={m} />
                    <div>
                      <h3 className="text-sm font-medium">{m.title}</h3>
                      <p className="text-xs text-muted-foreground">
                        Shared by {m.sharedBy}
                        {m.date && ` · ${new Date(m.date).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}`}
                        {m.taggedCount > 0 && ` · ${m.taggedCount} tagged`}
                      </p>
                    </div>
                  </article>
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}
