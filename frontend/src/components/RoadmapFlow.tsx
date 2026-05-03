import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Position,
  type Edge,
  type Node,
} from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";
import type { RoadmapResponse, RoadmapNode } from "../lib/api";

const NODE_W = 240;
const NODE_H = 96;

const LEVEL_STYLE: Record<string, string> = {
  beginner: "border-emerald-500/60 bg-emerald-500/10",
  intermediate: "border-amber-500/60 bg-amber-500/10",
  advanced: "border-rose-500/60 bg-rose-500/10",
};

function layout(nodes: Node[], edges: Edge[]) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 80 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const p = g.node(n.id);
    return {
      ...n,
      position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    };
  });
}

function NodeCard({ data }: { data: RoadmapNode }) {
  const cls = LEVEL_STYLE[data.level] ?? "border-border bg-muted";
  const content = (
    <>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{data.skill}</div>
      <div className="font-semibold text-sm leading-tight mt-0.5">{data.title}</div>
      <div className="text-xs text-muted-foreground mt-1">
        {data.level} · ~{data.estimated_hours}ч
      </div>
    </>
  );
  if (data.resource_url) {
    return (
      <a
        href={data.resource_url}
        target="_blank"
        rel="noreferrer"
        className={`block rounded-lg border-2 px-3 py-2 shadow-sm hover:shadow-md transition ${cls}`}
        style={{ width: NODE_W }}
        title={data.description ?? ""}
      >
        {content}
      </a>
    );
  }
  return (
    <div
      className={`rounded-lg border-2 px-3 py-2 shadow-sm ${cls}`}
      style={{ width: NODE_W }}
      title={data.description ?? ""}
    >
      {content}
    </div>
  );
}

const nodeTypes = { roadmap: NodeCard };

export function RoadmapFlow({ roadmap }: { roadmap: RoadmapResponse }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const { nodes, edges } = useMemo(() => {
    const rawNodes: Node[] = roadmap.nodes.map((n) => ({
      id: n.id,
      type: "roadmap",
      data: n,
      position: { x: 0, y: 0 },
    }));
    const rawEdges: Edge[] = roadmap.edges.map((e, i) => ({
      id: `e-${i}-${e.from}-${e.to}`,
      source: e.from,
      target: e.to,
      animated: true,
      style: { strokeWidth: 1.5 },
    }));
    return { nodes: layout(rawNodes, rawEdges), edges: rawEdges };
  }, [roadmap]);

  if (!mounted) {
    return <div className="h-[640px] w-full rounded-lg border bg-muted/20" />;
  }

  return (
    <div className="h-[640px] w-full rounded-lg border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} />
        <Controls />
        <MiniMap pannable zoomable />
      </ReactFlow>
    </div>
  );
}