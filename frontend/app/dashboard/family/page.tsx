"use client";

export const dynamic = "force-dynamic";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import fallbackTreeData from "@/contracts/graph-tree-response.json";
import { KinshipPathGlowEdge, type KinshipEdgeData } from "@/components/family/KinshipPathGlow";
import { PersonDrawer } from "@/components/family/PersonDrawer";
import { fetchCulturalKinship, type CulturalKinshipResponse } from "@/lib/cultural-kinship";
import { authHeaders, getSessionUserId } from "@/lib/api";
import {
  MilestoneNodeBadge,
  type MilestoneBadgeData,
} from "@/components/family/MilestoneNodeBadge";
import {
  EmergencyAlertDossierModal,
  CANONICAL_ELEANOR_ALERT,
  type EmergencyPayload,
} from "@/components/family/EmergencyAlertOverlay";

export type FamilyMemberData = {
  full_name: string;
  role: string;
  relation_to_head: string;
  generation: number;
  gender: "male" | "female";
  birth_date: string;
  is_living: boolean;
  avatar_url: string | null;
  nuclear_household: string;
  blood_group?: string;
  health_alerts?: string[];
  milestones?: string[];
  unlocked_letters?: string[];
  isHighlighted?: boolean;
  milestoneBadges?: MilestoneBadgeData[];
  hasEmergencyAlert?: boolean;
  onEmergencyClick?: () => void;
  onMilestoneClick?: (milestone: MilestoneBadgeData) => void;
};

type RawTreeNode = {
  id: string;
  type?: string;
  data: FamilyMemberData;
  position: { x: number; y: number };
};

type RawTreeEdge = {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
  animated?: boolean;
};

const genColors: Record<number, { bg: string; border: string; text: string; badgeBg: string }> = {
  1: { bg: "#f0fdf4", border: "#16a34a", text: "#14532d", badgeBg: "#dcfce7" },
  2: { bg: "#f8fafc", border: "#64748b", text: "#0f172a", badgeBg: "#e2e8f0" },
  3: { bg: "#f0f9ff", border: "#0284c7", text: "#0c4a6e", badgeBg: "#e0f2fe" },
};

function FamilyMemberNode({ data }: NodeProps<Node<FamilyMemberData>>) {
  const isHead = data.relation_to_head === "HEAD";
  const isAncestor = data.generation === 1;
  const theme = genColors[data.generation] ?? genColors[2];
  const isHighlighted = data.isHighlighted;
  const hasEmergency = Boolean(data.hasEmergencyAlert);

  return (
    <div
      style={{
        backgroundColor: theme.bg,
        borderWidth: hasEmergency ? "2.5px" : isHighlighted ? "2.5px" : isHead ? "2.5px" : "1.5px",
        borderColor: hasEmergency ? "#e11d48" : isHighlighted ? "#a855f7" : isHead ? "#d97706" : theme.border,
        boxShadow: hasEmergency
          ? "0 0 20px 4px rgba(225, 29, 72, 0.45)"
          : isHighlighted
          ? "0 0 16px 3px rgba(168, 85, 247, 0.45)"
          : isHead
          ? "0 4px 12px -2px rgba(217, 119, 6, 0.25)"
          : "0 2px 6px -1px rgba(0, 0, 0, 0.08)",
      }}
      className="relative flex min-w-[210px] flex-col rounded-xl px-4 py-3 font-sans transition-all hover:scale-[1.02] cursor-pointer"
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-slate-400"
      />

      {/* Top Header Row */}
      <div className="mb-2 flex items-center justify-between gap-1.5 text-[10px] font-semibold">
        <span
          style={{ backgroundColor: theme.badgeBg, color: theme.text }}
          className="rounded px-1.5 py-0.5"
        >
          {isAncestor ? "Gen 1 • Ancestor" : `Gen ${data.generation}`}
        </span>

        <div className="flex items-center gap-1.5">
          {hasEmergency && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                data.onEmergencyClick?.();
              }}
              title="Emergency Red Alert Active - Click for Medical Dossier"
              className="flex items-center gap-1 rounded bg-rose-600 px-1.5 py-0.5 text-[9px] font-black uppercase text-white shadow-sm hover:bg-rose-700 animate-pulse"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-white" />
              RED ALERT
            </button>
          )}

          {isHead ? (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-800">
              Clan Head
            </span>
          ) : (
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
              {data.relation_to_head}
            </span>
          )}
        </div>
      </div>

      {/* Full Name & Clinical Alert Beacon */}
      <div className="flex items-center justify-between">
        <div className="text-sm font-bold tracking-tight text-slate-900">
          {data.full_name}
        </div>
        {data.health_alerts && data.health_alerts.length > 0 && !hasEmergency && (
          <span
            className="flex h-2.5 w-2.5 rounded-full bg-rose-500 animate-pulse"
            title="Emergency Health Alert Active"
          />
        )}
      </div>

      {/* Milestone Badging Chips */}
      {data.milestoneBadges && data.milestoneBadges.length > 0 && (
        <MilestoneNodeBadge
          milestones={data.milestoneBadges}
          onBadgeClick={data.onMilestoneClick}
        />
      )}

      {/* Bottom Household & Living State */}
      <div className="mt-2.5 flex items-center justify-between border-t border-slate-200/80 pt-2 text-[11px]">
        <span className="max-w-[110px] truncate text-slate-500" title={data.nuclear_household}>
          {data.nuclear_household}
        </span>
        <div className="flex items-center gap-1">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              data.is_living ? "bg-emerald-500" : "bg-slate-400"
            }`}
          />
          <span className="text-[10px] text-slate-600 font-medium">
            {data.is_living ? "Living" : "Deceased"}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2.5 !w-2.5 !border-2 !border-white !bg-slate-400"
      />
    </div>
  );
}

function buildNodes(
  rawNodes: RawTreeNode[],
  handlers: {
    onEmergencyClick: (member: FamilyMemberData) => void;
    onMilestoneClick: (badge: MilestoneBadgeData) => void;
  }
): Node<FamilyMemberData>[] {
  return rawNodes.map((n) => {
    const isEleanor = n.data.full_name?.includes("Eleanor");
    const isArthur = n.data.full_name?.includes("Arthur");
    const isDavid = n.data.full_name?.includes("David");
    const isLucas = n.data.full_name?.includes("Lucas");
    const isSophia = n.data.full_name?.includes("Sophia");

    const clinicalAlerts = isEleanor
      ? [
          "Pacemaker Implantation (St. Jude Medical 2021)",
          "Severe Allergy: Penicillin and Sulfa Drugs",
          "AIIMS Cardiology Emergency Hotline: +91-11-26588500",
        ]
      : [];

    const memberMilestones = isArthur
      ? ["Clan Patriarch and Custodian (1985)", "Golden Anniversary Milestone (2022)"]
      : isEleanor
      ? ["Matriarchal Archive Founder (2010)", "Generational Lore Trustee"]
      : isDavid
      ? ["Sprint 3 Milestone Vault Signer", "Vance Labs Engineering Lead"]
      : isLucas
      ? ["Next Generation STEM Scholar (2024)"]
      : ["Generational Vault Contributor"];

    const memberLetters = isArthur
      ? ["To My Grandchildren (Time-Locked: 2028)", "Ancestral Homestead Deed Lore"]
      : isEleanor
      ? ["Family Heritage and Values (Unlocked)", "To the Next Matriarch (Time-Locked: 2030)"]
      : isDavid
      ? ["Letter to Lucas (Unlock: 18th Birthday)"]
      : [];

    // Milestone badges for Sprint 5 Deliverable 6
    const milestoneBadges: MilestoneBadgeData[] = [];
    if (isSophia) {
      milestoneBadges.push({
        id: "mb-sophia-18",
        title: "18th Birthday Capsule",
        type: "time_capsule",
        status: "SEALED",
        unlockDate: "2026-11-20",
      });
    }
    if (isArthur) {
      milestoneBadges.push({
        id: "mb-arthur-will",
        title: "Ancestral Will",
        type: "digital_will",
        status: "SEALED",
        requiredSignatures: 3,
        currentSignatures: 2,
      });
    }

    return {
      id: n.id,
      type: "familyMember",
      position: n.position,
      data: {
        ...n.data,
        blood_group: n.data.blood_group || (isEleanor ? "A+" : isArthur ? "O+" : isDavid ? "B+" : "O+"),
        health_alerts: n.data.health_alerts || clinicalAlerts,
        milestones: n.data.milestones || memberMilestones,
        unlocked_letters: n.data.unlocked_letters || memberLetters,
        milestoneBadges,
        hasEmergencyAlert: isEleanor, // Eleanor triggers red alert protocol
        onEmergencyClick: () => handlers.onEmergencyClick(n.data),
        onMilestoneClick: handlers.onMilestoneClick,
      },
    };
  });
}

function buildEdges(rawEdges: RawTreeEdge[]): Edge<KinshipEdgeData>[] {
  return rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    type: "kinshipPath",
    data: { isKinshipPath: false },
    animated: e.animated ?? false,
    style: { stroke: "#94a3b8", strokeWidth: 2 },
  }));
}

function FamilyTreeCanvas() {
  const [clanName, setClanName] = useState<string>("Vance Ancestral Clan");
  const [dataSource, setDataSource] = useState<"live" | "mock">("mock");
  const [loading, setLoading] = useState<boolean>(true);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node<FamilyMemberData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge<KinshipEdgeData>>([]);

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedMember, setSelectedMember] = useState<FamilyMemberData | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [kinshipData, setKinshipData] = useState<CulturalKinshipResponse | null>(null);

  // Emergency Alert Modal state
  const [emergencyModalOpen, setEmergencyModalOpen] = useState<boolean>(false);
  const [activeEmergencyData, setActiveEmergencyData] = useState<EmergencyPayload>(CANONICAL_ELEANOR_ALERT);

  // Milestone Notification state
  const [activeMilestoneToast, setActiveMilestoneToast] = useState<MilestoneBadgeData | null>(null);

  const { setCenter } = useReactFlow();

  const handleEmergencyClick = useCallback((member: FamilyMemberData) => {
    setActiveEmergencyData({
      ...CANONICAL_ELEANOR_ALERT,
      memberName: member.full_name,
      bloodGroup: member.blood_group || "A+",
    });
    setEmergencyModalOpen(true);
  }, []);

  const handleMilestoneClick = useCallback((badge: MilestoneBadgeData) => {
    setActiveMilestoneToast(badge);
    setTimeout(() => {
      setActiveMilestoneToast(null);
    }, 4000);
  }, []);

  const nodeTypes = useMemo(() => ({ familyMember: FamilyMemberNode }), []);
  const edgeTypes: EdgeTypes = useMemo(
    () => ({
      kinshipPath: KinshipPathGlowEdge,
    }),
    []
  );

  const loadTreeData = useCallback(async () => {
    setLoading(true);

    const graphBaseUrl =
      process.env.NEXT_PUBLIC_GRAPH_API_URL || "http://localhost:8001";
    // Kinship badges are relative to the root: the signed-in member, or the
    // seeded clan head for demo visitors.
    const rootPersonId = (await getSessionUserId()) || "00000000-0000-0000-0000-000000000001";

    const handlers = {
      onEmergencyClick: handleEmergencyClick,
      onMilestoneClick: handleMilestoneClick,
    };

    try {
      const res = await fetch(`${graphBaseUrl}/api/graph/tree?person_id=${rootPersonId}&max_depth=4`, {
        signal: AbortSignal.timeout(2500),
        headers: await authHeaders(),
      });

      if (res.ok) {
        const json = await res.json();
        if (Array.isArray(json.nodes) && Array.isArray(json.edges) && json.nodes.length > 0) {
          setClanName(json.clan_name || "Vance Ancestral Clan");
          setNodes(buildNodes(json.nodes, handlers));
          setEdges(buildEdges(json.edges));
          setDataSource("live");
          setLoading(false);
          return;
        }
      }
    } catch {
      // Fallback below
    }

    setClanName(fallbackTreeData.clan_name ?? "Vance Ancestral Clan");
    setNodes(buildNodes(fallbackTreeData.nodes as RawTreeNode[], handlers));
    setEdges(buildEdges(fallbackTreeData.edges as RawTreeEdge[]));
    setDataSource("mock");
    setLoading(false);
  }, [setNodes, setEdges, handleEmergencyClick, handleMilestoneClick]);

  useEffect(() => {
    loadTreeData();
  }, [loadTreeData]);

  useEffect(() => {
    if (selectedNodeIds.length === 2) {
      fetchCulturalKinship(selectedNodeIds[0], selectedNodeIds[1]).then((res) => {
        setKinshipData(res);
      });
    } else {
      setKinshipData(null);
    }
  }, [selectedNodeIds]);

  const handleSelectMember = (node: Node<FamilyMemberData>) => {
    setCenter(node.position.x + 105, node.position.y + 45, {
      zoom: 1.2,
      duration: 800,
    });
    setSelectedMember(node.data);
    setSearchQuery("");
  };

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    const memberData = node.data as FamilyMemberData;
    setSelectedMember(memberData);

    setSelectedNodeIds((prev) => {
      if (prev.length === 0 || prev.length >= 2) return [node.id];
      if (prev.includes(node.id)) return prev;
      return [...prev, node.id];
    });
  }, []);

  const styledEdges = useMemo(() => {
    const isPathActive = selectedNodeIds.length === 2;
    return edges.map((edge) => {
      const isConnected =
        isPathActive &&
        ((edge.source === selectedNodeIds[0] && edge.target === selectedNodeIds[1]) ||
          (edge.source === selectedNodeIds[1] && edge.target === selectedNodeIds[0]));

      return {
        ...edge,
        data: {
          ...edge.data,
          isKinshipPath: isConnected,
          kinshipLabel: isConnected && kinshipData ? `${kinshipData.term} (${kinshipData.english})` : undefined,
        },
      };
    });
  }, [edges, selectedNodeIds, kinshipData]);

  const styledNodes = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isHighlighted: selectedNodeIds.includes(node.id),
      },
    }));
  }, [nodes, selectedNodeIds]);

  return (
    <div className="flex h-[calc(100vh-6rem)] w-full flex-col gap-2">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {clanName}
          </h1>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              dataSource === "live"
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                dataSource === "live" ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            {dataSource === "live" ? "Live Neo4j Graph" : "Contract Mock (Fallback)"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {selectedNodeIds.length > 0 && (
            <button
              onClick={() => {
                setSelectedNodeIds([]);
                setKinshipData(null);
              }}
              className="rounded-md border border-purple-300 bg-purple-50 px-2.5 py-1.5 text-xs font-medium text-purple-700 hover:bg-purple-100 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-300 dark:hover:bg-purple-900"
            >
              Clear Kinship ({selectedNodeIds.length})
            </button>
          )}

          <button
            onClick={() => setEmergencyModalOpen(true)}
            className="flex items-center gap-1.5 rounded-md border border-rose-300 bg-rose-50 px-2.5 py-1.5 text-xs font-bold text-rose-700 hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950/60 dark:text-rose-300"
          >
            <span className="h-2 w-2 rounded-full bg-rose-600 animate-ping" />
            Medical Pass
          </button>

          <button
            onClick={loadTreeData}
            disabled={loading}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            {loading ? "Refreshing..." : "Refresh Graph"}
          </button>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="relative flex-1 rounded-lg border border-slate-200 bg-slate-50/50 shadow-inner overflow-hidden dark:border-slate-800 dark:bg-slate-950">
        {/* Search Overlay */}
        <div className="absolute top-3 left-3 z-10 w-72">
          <div className="rounded-lg border border-slate-300 bg-white/95 px-3 py-1.5 shadow-md backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
            <input
              type="text"
              placeholder="Search Vance Clan member..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent text-xs text-slate-800 placeholder-slate-400 focus:outline-none dark:text-slate-100 dark:placeholder-slate-500"
            />
          </div>

          {searchQuery.trim() && (
            <div className="mt-1 max-h-56 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
              {nodes
                .filter((n) =>
                  n.data.full_name.toLowerCase().includes(searchQuery.toLowerCase())
                )
                .map((n) => (
                  <button
                    key={n.id}
                    onClick={() => handleSelectMember(n)}
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-xs hover:bg-purple-50 transition-colors border-b border-slate-100 last:border-b-0 dark:border-slate-800 dark:hover:bg-purple-950/40"
                  >
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {n.data.full_name}
                    </span>
                    <span className="text-[10px] text-purple-600 font-medium dark:text-purple-400">
                      Gen {n.data.generation} • {n.data.relation_to_head}
                    </span>
                  </button>
                ))}
            </div>
          )}

          {selectedNodeIds.length === 1 && (
            <div className="mt-1.5 rounded-md bg-purple-50 border border-purple-200 px-2.5 py-1 text-[11px] text-purple-700 shadow-sm dark:border-purple-800 dark:bg-purple-950/80 dark:text-purple-300">
              Select a second member to highlight their direct kinship path.
            </div>
          )}

          {selectedNodeIds.length === 2 && kinshipData && (
            <div className="mt-1.5 rounded-md bg-purple-100 border border-purple-300 p-2 text-xs font-semibold text-purple-900 shadow-md dark:border-purple-700 dark:bg-purple-950 dark:text-purple-200">
              Kinship: {kinshipData.term} ({kinshipData.english})
              {kinshipData.gotra && (
                <div className="text-[10px] font-normal text-purple-700 dark:text-purple-400">
                  Gotra: {kinshipData.gotra}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Milestone Click Floating Notification */}
        {activeMilestoneToast && (
          <div className="absolute bottom-5 left-5 z-20 max-w-xs rounded-xl border border-indigo-200 bg-white/95 p-3.5 shadow-xl backdrop-blur animate-in slide-in-from-bottom duration-200 dark:border-indigo-900 dark:bg-slate-900/95">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-indigo-700 dark:text-indigo-300">
                🔒 {activeMilestoneToast.title}
              </span>
              <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[9px] font-bold text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200">
                {activeMilestoneToast.status}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-600 dark:text-slate-400">
              {activeMilestoneToast.type === "time_capsule"
                ? `Time-locked until ${activeMilestoneToast.unlockDate}. Unlocks automatically on maturity.`
                : `Requires multi-trustee consensus: ${activeMilestoneToast.currentSignatures}/${activeMilestoneToast.requiredSignatures} verified signatures.`}
            </p>
          </div>
        )}

        {/* Person Dossier Drawer */}
        <PersonDrawer
          member={selectedMember}
          kinshipInfo={kinshipData}
          onClose={() => setSelectedMember(null)}
        />

        {/* Emergency Medical Dossier Modal */}
        <EmergencyAlertDossierModal
          alertData={activeEmergencyData}
          isOpen={emergencyModalOpen}
          onClose={() => setEmergencyModalOpen(false)}
        />

        {loading ? (
          <div className="flex h-full w-full items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-800 dark:border-slate-700 dark:border-t-slate-200" />
              <p className="text-xs text-slate-500 dark:text-slate-400">Loading family graph...</p>
            </div>
          </div>
        ) : (
          <ReactFlow
            nodes={styledNodes}
            edges={styledEdges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            minZoom={0.35}
            maxZoom={2.2}
          >
            <Background color="#94a3b8" gap={16} />
            <Controls
              className="!border-slate-300 !bg-white dark:!border-slate-700 dark:!bg-slate-800 [&>button]:!border-slate-300 [&>button]:!bg-white [&>button]:!fill-slate-700 hover:[&>button]:!bg-slate-100 dark:[&>button]:!border-slate-700 dark:[&>button]:!bg-slate-800 dark:[&>button]:!fill-slate-200 dark:hover:[&>button]:!bg-slate-700"
            />
            <MiniMap
              nodeColor={(node) => {
                const data = node.data as FamilyMemberData;
                if (data?.hasEmergencyAlert) return "#e11d48";
                if (data?.relation_to_head === "HEAD") return "#d97706";
                if (data?.generation === 1) return "#16a34a";
                if (data?.generation === 3) return "#0284c7";
                return "#64748b";
              }}
              maskColor="rgba(241, 245, 249, 0.7)"
            />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}

export default function FamilyTreePage() {
  return (
    <ReactFlowProvider>
      <FamilyTreeCanvas />
    </ReactFlowProvider>
  );
}
