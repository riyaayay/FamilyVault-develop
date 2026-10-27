"use client";

import React from "react";
import type { FamilyMemberData } from "@/app/dashboard/family/page";
import type { CulturalKinshipResponse } from "@/lib/cultural-kinship";

export type ApprovedTimelinePhoto = {
  id: string;
  url: string;
  caption: string;
  year?: string;
};

const MOCK_APPROVED_PHOTOS: Record<string, ApprovedTimelinePhoto[]> = {
  "Arthur Vance": [
    { id: "photo-1", url: "/mock/arthur-reunion.jpg", caption: "Vance Ancestral Haveli Reunion", year: "1995" },
    { id: "photo-2", url: "/mock/arthur-patel.jpg", caption: "Arthur with Clan Trustees", year: "2012" },
  ],
  "Eleanor Vance": [
    { id: "photo-3", url: "/mock/eleanor-garden.jpg", caption: "Matriarch Heritage Archive", year: "2010" },
  ],
  "David Vance": [
    { id: "photo-4", url: "/mock/david-lucas.jpg", caption: "Lucas & David at Family Vault Launch", year: "2024" },
  ],
  "Lucas Vance": [
    { id: "photo-5", url: "/mock/lucas-stem.jpg", caption: "Lucas Vance Robotics Fair", year: "2025" },
  ],
  "Robert Vance": [
    { id: "photo-6", url: "/mock/robert-lucas.jpg", caption: "Robert & Lucas Vance Gathering", year: "2023" },
  ],
};

interface PersonDrawerProps {
  member: FamilyMemberData | null;
  kinshipInfo?: CulturalKinshipResponse | null;
  onClose: () => void;
}

export function PersonDrawer({ member, kinshipInfo, onClose }: PersonDrawerProps) {
  if (!member) return null;

  const approvedPhotos = MOCK_APPROVED_PHOTOS[member.full_name] || [];

  return (
    <aside
      role="dialog"
      aria-label={`Detailed dossier for ${member.full_name}`}
      className="absolute top-0 right-0 z-30 flex h-full w-full max-w-sm flex-col justify-between border-l border-slate-200 bg-white/95 p-5 shadow-2xl backdrop-blur overflow-y-auto dark:border-slate-800 dark:bg-slate-900/95"
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between border-b border-slate-100 pb-3 dark:border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
              {member.full_name}
            </h2>
            <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
              <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                Gen {member.generation} • {member.relation_to_head}
              </span>
              {kinshipInfo?.term && (
                <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-bold text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                  {kinshipInfo.term} ({kinshipInfo.english})
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dossier drawer"
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            ✕
          </button>
        </div>

        {kinshipInfo?.gotra && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
            <span className="font-semibold">Gotra Ancestry: </span>
            {kinshipInfo.gotra}
          </div>
        )}

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 dark:border-slate-800 dark:bg-slate-800/60">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block dark:text-slate-400">
            Emergency Medical Pass
          </span>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs font-bold text-rose-600 dark:text-rose-400">
              Blood Group: {member.blood_group || "O+"}
            </span>
            <span className="text-[10px] text-slate-500">
              {member.is_living ? "Living" : "Deceased"}
            </span>
          </div>

          {member.health_alerts && member.health_alerts.length > 0 && (
            <div className="mt-2 space-y-1 border-t border-rose-200/60 pt-2 dark:border-rose-900/40">
              <span className="text-[10px] font-bold text-rose-700 uppercase block dark:text-rose-300">
                Active Medical Conditions:
              </span>
              {member.health_alerts.map((alert, i) => (
                <p key={i} className="text-[11px] text-rose-900 leading-tight dark:text-rose-200">
                  • {alert}
                </p>
              ))}
            </div>
          )}
        </div>

        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2 dark:text-slate-400">
            Approved Timeline Photos ({approvedPhotos.length})
          </span>
          {approvedPhotos.length > 0 ? (
            <div className="grid grid-cols-2 gap-2">
              {approvedPhotos.map((photo) => (
                <div
                  key={photo.id}
                  className="group relative aspect-video overflow-hidden rounded-md border border-slate-200 bg-slate-100 dark:border-slate-800 dark:bg-slate-800"
                >
                  <div className="flex h-full w-full items-center justify-center text-center p-2 text-[10px] text-slate-500">
                    {photo.caption} ({photo.year})
                  </div>
                  <div className="absolute inset-x-0 bottom-0 bg-black/60 px-1.5 py-0.5 text-[9px] text-white backdrop-blur">
                    {photo.year}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-md border border-dashed border-slate-200 p-3 text-center text-xs text-slate-400 dark:border-slate-800 dark:text-slate-500">
              No approved media tagged yet.
            </p>
          )}
        </div>

        {member.milestones && member.milestones.length > 0 && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 dark:border-slate-800 dark:bg-slate-800/60">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1 dark:text-slate-400">
              Clan Milestones
            </span>
            <ul className="space-y-1">
              {member.milestones.map((m, idx) => (
                <li key={idx} className="text-xs text-slate-700 dark:text-slate-300">
                  - {m}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        onClick={onClose}
        className="mt-4 w-full rounded-md border border-slate-300 bg-white py-2 text-xs font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
      >
        Close Dossier
      </button>
    </aside>
  );
}
