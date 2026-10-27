"use client";

import React from "react";

export type MilestoneBadgeData = {
  id: string;
  title: string;
  type: "time_capsule" | "digital_will";
  status: "SEALED" | "UNLOCKED";
  unlockDate?: string;
  requiredSignatures?: number;
  currentSignatures?: number;
};

interface MilestoneNodeBadgeProps {
  milestones: MilestoneBadgeData[];
  onBadgeClick?: (milestone: MilestoneBadgeData) => void;
}

export function MilestoneNodeBadge({ milestones, onBadgeClick }: MilestoneNodeBadgeProps) {
  if (!milestones || milestones.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {milestones.map((m) => {
        const isWill = m.type === "digital_will";
        const isSealed = m.status === "SEALED";

        return (
          <button
            key={m.id}
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onBadgeClick?.(m);
            }}
            title={`${m.title} - ${isSealed ? "Sealed / Locked" : "Unlocked"}`}
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold transition-all hover:scale-105 ${
              isSealed
                ? isWill
                  ? "bg-amber-100 text-amber-900 border border-amber-300 dark:bg-amber-950/80 dark:text-amber-200 dark:border-amber-800"
                  : "bg-indigo-100 text-indigo-900 border border-indigo-300 dark:bg-indigo-950/80 dark:text-indigo-200 dark:border-indigo-800"
                : "bg-emerald-100 text-emerald-900 border border-emerald-300 dark:bg-emerald-950/80 dark:text-emerald-200 dark:border-emerald-800"
            }`}
          >
            <span>{isSealed ? "🔒" : "🔓"}</span>
            <span className="truncate max-w-[100px]">{m.title}</span>
            {isWill && isSealed && m.requiredSignatures && (
              <span className="ml-0.5 rounded bg-amber-200/80 px-1 text-[8px] dark:bg-amber-900">
                {m.currentSignatures ?? 1}/{m.requiredSignatures}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
