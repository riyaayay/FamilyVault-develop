"use client";

import React from "react";
import { BaseEdge, getSmoothStepPath, type EdgeProps, type Edge } from "@xyflow/react";

export type KinshipEdgeData = {
  isKinshipPath?: boolean;
  kinshipLabel?: string;
};

export type KinshipEdgeType = Edge<KinshipEdgeData, "kinshipPath">;

export function KinshipPathGlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps<KinshipEdgeType>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 16,
  });

  const isHighlighted = Boolean(data?.isKinshipPath);

  return (
    <>
      <svg style={{ position: "absolute", width: 0, height: 0 }}>
        <defs>
          <linearGradient id="kinshipGlowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ec4899" />
            <stop offset="50%" stopColor="#a855f7" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
          <filter id="glowBlur" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
      </svg>

      {isHighlighted && (
        <path
          d={edgePath}
          fill="none"
          stroke="url(#kinshipGlowGrad)"
          strokeWidth={8}
          strokeOpacity={0.65}
          filter="url(#glowBlur)"
          className="transition-all duration-300"
        />
      )}

      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...(style || {}),
          stroke: isHighlighted ? "url(#kinshipGlowGrad)" : "#94a3b8",
          strokeWidth: isHighlighted ? 3.5 : 2,
          strokeDasharray: isHighlighted ? "8, 4" : undefined,
          opacity: isHighlighted ? 1 : 0.45,
          transition: "all 0.3s ease-in-out",
        }}
      />

      {isHighlighted && data?.kinshipLabel && (
        <foreignObject
          width={140}
          height={32}
          x={labelX - 70}
          y={labelY - 16}
          className="pointer-events-none overflow-visible"
        >
          <div className="flex h-full w-full items-center justify-center">
            <span className="rounded-full border border-purple-300 bg-white/95 px-2.5 py-0.5 text-[10px] font-bold text-purple-700 shadow-md backdrop-blur dark:border-purple-700 dark:bg-slate-900/95 dark:text-purple-300">
              {data.kinshipLabel}
            </span>
          </div>
        </foreignObject>
      )}
    </>
  );
}
