import { useRef, useCallback, useEffect, useMemo, useState, memo } from "react";
import { useTranslation } from "react-i18next";
import ForceGraph2D, { type NodeObject } from "react-force-graph-2d";
import { forceCollide } from "d3-force";

interface GraphData {
  nodes: { id: number; name: string; description?: string; asset_count: number }[];
  edges: { node_id: number; asset_id: number; filename: string; asset_type: string; ai_summary?: string; thumbnail_status?: string }[];
  unassigned: { id: number; filename: string; asset_type: string; thumbnail_status?: string }[];
}

interface Props {
  graphData: GraphData;
  selectedNodeId: number | null;
  selectedNodeName: string;
  onSelectNode: (nodeId: number | null, nodeName?: string) => void;
  onSelectAsset: (assetId: number) => void;
  searchResults: { id: number; filename: string; asset_type: string }[];
  filteredAssets: { id: number }[];
  hasActiveFilter: boolean;
  expandedNodes: Set<number>;
  onExpandedChange: (nodes: Set<number>) => void;
  onReload: () => void;
  onAssetDrop?: (assetId: number, nodeId: number | number[], unassign: boolean) => void;
}

const ASSET_COLORS: Record<string, string> = {
  image: "#5b9ecf", video: "#c95a8a", audio: "#7eb84a", document: "#c89e40",
};

interface FgNode extends NodeObject {
  label: string;
  isAgg: boolean;
  isUnassigned?: boolean;
  assetType?: string;
  count?: number;
  aiSummary?: string;
  hasThumbnail?: boolean;
}

function GraphView({ graphData, onSelectNode, onSelectAsset, searchResults: _sr, filteredAssets, hasActiveFilter, expandedNodes, onExpandedChange, onReload, onAssetDrop }: Props) {
  const { t } = useTranslation();
  const ASSET_LABELS: Record<string, string> = { image: t("asset.type_image"), video: t("asset.type_video"), audio: t("asset.type_audio"), document: t("asset.type_document") };
  const fgRef = useRef<any>(null);
  const expandedRef = useRef(expandedNodes);
  expandedRef.current = expandedNodes;

  const nodeMap = useRef<Map<string, FgNode>>(new Map());
  const linkMap = useRef<Map<string, any>>(new Map());
  const nodeLinkMap = useRef<Map<string, Set<string>>>(new Map());
  const assetTypeMap = useRef<Map<string, string>>(new Map());
  const thumbCache = useRef<Map<number, HTMLImageElement | null>>(new Map());
  const [graphVersion, setGraphVersion] = useState(0);
  const [zoomPercent, setZoomPercent] = useState(100);
  const nodeCountRef = useRef(0);
  const linkCountRef = useRef(0);
  const prevExpandedCountRef = useRef(0);
  const linkHashRef = useRef("");

  const savedZoom = useRef(1);
  const chargeSettled = useRef(false);
  const dragTargetAggId = useRef<string | null>(null);
  const dragHighlightRef = useRef(0);

  const searchIdSet = useMemo(() => {
    const ids = new Set<number>();
    if (filteredAssets?.length) {
      filteredAssets.forEach((a) => ids.add(a.id));
    }
    return ids;
  }, [filteredAssets]);

  const edgeMap = useMemo(() => {
    const em = new Map<number, {asset_id: number; filename: string; asset_type: string; ai_summary?: string; thumbnail_status?: string}[]>();
    graphData.edges.forEach((e) => {
      if (!em.has(e.node_id)) em.set(e.node_id, []);
      em.get(e.node_id)!.push({asset_id: e.asset_id, filename: e.filename, asset_type: e.asset_type, ai_summary: e.ai_summary, thumbnail_status: e.thumbnail_status});
    });
    return em;
  }, [graphData.edges]);

  const visibleAggIds = useMemo(() => {
    const set = new Set<string>();
    for (const [nid, assets] of edgeMap) {
      if (assets.some((a: any) => searchIdSet.has(a.asset_id))) {
        set.add(`node-${nid}`);
      }
    }
    // Unassigned node: visible if any unassigned asset is in the filtered set
    if (graphData.unassigned?.some((a: any) => searchIdSet.has(a.id))) {
      set.add("unassigned");
    }
    return set;
  }, [edgeMap, searchIdSet, graphData.unassigned]);

  useEffect(() => {
    const atm = assetTypeMap.current;
    graphData.unassigned.forEach((a) => atm.set(`asset-${a.id}`, a.asset_type));
  }, [graphData.unassigned]);

  // Preload thumbnails — canvas refresh only, no React render
  useEffect(() => {
    const tc = thumbCache.current;
    console.log("[GraphView:thumbnails] unassigned:", graphData.unassigned?.length, "edges:", graphData.edges?.length);
    const allAssets = [
      ...graphData.unassigned,
      ...graphData.edges.map((e) => ({id: e.asset_id, asset_type: e.asset_type, thumbnail_status: e.thumbnail_status})),
    ];
    allAssets.forEach((a) => {
      if ((a.asset_type === "image" || a.asset_type === "video") && a.thumbnail_status === "done" && !tc.has(a.id)) {
        const img = new Image();
        img.onload = () => { tc.set(a.id, img); try { fgRef.current?.refresh?.(); } catch {} };
        img.onerror = () => tc.set(a.id, null);
        img.src = `/api/thumbnails/${a.id}`;
        tc.set(a.id, undefined as any);
      }
    });
  }, [graphData]);

  // Sync graph incrementally
  useEffect(() => {
    console.log("[GraphView:sync] nodes:", graphData.nodes?.length, "unassigned:", graphData.unassigned?.length);
    const nm = nodeMap.current;
    const lm = linkMap.current;
    const nlm = nodeLinkMap.current;
    const atm = assetTypeMap.current;

    const currentAggIds = new Set(graphData.nodes.map((n) => `node-${n.id}`));

    const removeLink = (key: string) => { lm.delete(key); const parts = key.split("->"); nlm.get(parts[0])?.delete(key); nlm.get(parts[1])?.delete(key); };
    const removeNode = (id: string) => { nm.delete(id); atm.delete(id); Array.from(nlm.get(id) || []).forEach(removeLink); nlm.delete(id); };

    // ── Aggregation nodes ──
    for (const [id] of nm) { if (id.startsWith("node-") && !currentAggIds.has(id)) removeNode(id); }
    graphData.nodes.forEach((n) => {
      const id = `node-${n.id}`;
      if (!nm.has(id)) nm.set(id, { id, label: n.name, isAgg: true, count: n.asset_count, x: -200 + (Math.random() - 0.5) * 800, y: (Math.random() - 0.5) * 600 } as FgNode);
      else { const ex = nm.get(id)!; ex.label = n.name; ex.count = n.asset_count; }
    });

    // ── Unassigned node (pinned far right) ──
    if (graphData.unassigned.length > 0) {
      if (!nm.has("unassigned")) nm.set("unassigned", { id: "unassigned", label: t("common.unassigned"), isAgg: true, isUnassigned: true, count: graphData.unassigned.length, x: 700, y: -200 } as FgNode);
      else nm.get("unassigned")!.count = graphData.unassigned.length;
    } else { nm.delete("unassigned"); }

    // ── Unassigned assets ──
    const currentUnassignedIds = new Set(graphData.unassigned.map((a) => `asset-${a.id}`));
    for (const [id, node] of nm) {
      if (!node.isAgg && !currentUnassignedIds.has(id)) {
        const stillNeeded = Array.from(expandedNodes).some((nid) => (edgeMap.get(nid) || []).some((e) => `asset-${e.asset_id}` === id));
        if (!stillNeeded) removeNode(id);
      }
    }
    graphData.unassigned.forEach((a) => {
      const aid = `asset-${a.id}`;
      if (!nm.has(aid)) nm.set(aid, { id: aid, label: a.filename, isAgg: false, assetType: a.asset_type } as FgNode);
      atm.set(aid, a.asset_type);
    });

    // ── Expanded assets (ring layout) ──
    const getParentPos = (nid: number) => { const p = nm.get(`node-${nid}`); return p?.x != null && p?.y != null ? { x: p.x, y: p.y } : null; };
    const expandedAssetIds = new Set<string>();
    expandedNodes.forEach((nid) => {
      const assets = edgeMap.get(nid) || [];
      const ringRadius = 30;
      assets.forEach((e, idx) => {
        const assetId = `asset-${e.asset_id}`;
        expandedAssetIds.add(assetId);
        if (!nm.has(assetId)) {
          const pos = getParentPos(nid);
          const angle = (idx / assets.length) * Math.PI * 2;
          const label = (e.filename || "").length > 10 ? (e.filename || "").slice(0, 10) + "..." : (e.filename || "");
          nm.set(assetId, { id: assetId, label, isAgg: false, assetType: e.asset_type, aiSummary: e.ai_summary, hasThumbnail: e.thumbnail_status === "done", ...(pos ? { x: pos.x + Math.cos(angle) * ringRadius, y: pos.y + Math.sin(angle) * ringRadius } : {}) } as FgNode);
        }
      });
    });
    for (const [id, node] of nm) { if (!node.isAgg && !expandedAssetIds.has(id) && !currentUnassignedIds.has(id)) removeNode(id); }

    // ── Links ──
    const nodeIds = new Set(nm.keys());
    const newLinkKeys = new Set<string>();
    graphData.unassigned.forEach((a) => {
      const key = `unassigned->asset-${a.id}`; newLinkKeys.add(key);
      if (!lm.has(key)) { lm.set(key, { source: "unassigned", target: `asset-${a.id}` }); if (!nlm.has("unassigned")) nlm.set("unassigned", new Set()); if (!nlm.has(`asset-${a.id}`)) nlm.set(`asset-${a.id}`, new Set()); nlm.get("unassigned")!.add(key); nlm.get(`asset-${a.id}`)!.add(key); }
    });
    expandedNodes.forEach((nid) => {
      const srcId = `node-${nid}`; if (!nodeIds.has(srcId)) return;
      (edgeMap.get(nid) || []).forEach((e) => {
        const tgtId = `asset-${e.asset_id}`; if (!nodeIds.has(tgtId)) return;
        const key = `${srcId}->${tgtId}`; newLinkKeys.add(key);
        if (!lm.has(key)) { lm.set(key, { source: srcId, target: tgtId }); if (!nlm.has(srcId)) nlm.set(srcId, new Set()); if (!nlm.has(tgtId)) nlm.set(tgtId, new Set()); nlm.get(srcId)!.add(key); nlm.get(tgtId)!.add(key); }
      });
    });
    for (const key of lm.keys()) { if (!newLinkKeys.has(key)) removeLink(key); }

    const newNodeCount = nm.size, newLinkCount = lm.size, newExpandedCount = expandedNodes.size;
    const edgeKeys = Array.from(lm.keys()).sort().join(",");
    const prevHash = `${nodeCountRef.current}:${linkCountRef.current}:${prevExpandedCountRef.current}:${linkHashRef.current}`;
    const newHash = `${newNodeCount}:${newLinkCount}:${newExpandedCount}:${edgeKeys}`;
    nodeCountRef.current = newNodeCount; linkCountRef.current = newLinkCount; prevExpandedCountRef.current = newExpandedCount; linkHashRef.current = edgeKeys;

    if (newHash !== prevHash) {
      const aggNodes = Array.from(nm.values()).filter((n) => n.isAgg && n.id !== "unassigned");
      console.log("Aggregation node pos:", aggNodes.map((n) => `${n.label} (${n.x?.toFixed(0)}, ${n.y?.toFixed(0)})`).join(" | "));
      savedZoom.current = fgRef.current?.zoom?.() || 1;
      try { fgRef.current?.d3Force?.("collision", forceCollide().radius((d: any) => d.isAgg ? 30 : 15)); } catch {}
      setGraphVersion((v) => v + 1);
      setTimeout(() => {
        fgRef.current?.zoom?.(savedZoom.current, 0);
      }, 80);
    }
  }, [graphData, expandedNodes, edgeMap]);

  const fgData = useMemo(() => ({ nodes: Array.from(nodeMap.current.values()), links: Array.from(linkMap.current.values()) }), [graphVersion]);

  useEffect(() => {
    requestAnimationFrame(() => {
      try {
        fgRef.current?.d3Force?.("link")?.distance?.((link: any) => {
          const src = typeof link.source === "object" ? link.source.id : link.source;
          const tgt = typeof link.target === "object" ? link.target.id : link.target;
          if (src === "unassigned" || tgt === "unassigned") return 140;
          // Dynamic: match node radius + 60px margin
          const aggNode = typeof link.source === "object" ? link.source : link.target;
          const count = aggNode?.count || 1;
          const radius = Math.max(12, Math.min(55, count * 5));
          return radius + 80;
        });
        fgRef.current?.d3Force?.("center")?.strength?.(0);
        fgRef.current?.d3Force?.("charge")?.strength?.(-20);
        // Collision: only for aggregation nodes, prevents overlap without drift
        try {
          fgRef.current?.d3Force?.("collision", forceCollide().radius((d: any) => d.isAgg ? 30 : 15));
        } catch {}
      } catch {}
    });
  }, []);

  const nodeCanvasObject = useCallback((node: FgNode, ctx: CanvasRenderingContext2D, scale: number) => {
    const x = node.x!, y = node.y!;
    // Dim non-matching nodes when search results are active
    let alpha = 1;
    if (hasActiveFilter) {
      if (node.isAgg) {
        alpha = visibleAggIds.has(node.id as string) ? 1 : 0.15;
      } else {
        const aid = parseInt(String(node.id).replace("asset-", ""));
        if (!isNaN(aid) && !searchIdSet.has(aid)) alpha = 0.15;
      }
    }
    ctx.globalAlpha = alpha;
    if (node.isAgg) {
      const r = node.isUnassigned ? 16 : Math.max(12, Math.min(55, (node.count || 1) * 5));
      ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI);
      // Color depth by radius: smaller=lighter coral, larger=darker
      if (node.isUnassigned) {
        ctx.fillStyle = "#8698b0";
      } else {
        const depth = (r - 12) / 43;
        const l = 55 - depth * 25; const s = 65 + depth * 15;
        ctx.fillStyle = `hsl(14, ${s}%, ${l}%)`;
      }
      ctx.fill();
      // Drag highlight ring
      if (dragTargetAggId.current === node.id) {
        ctx.beginPath(); ctx.arc(x, y, r + 6, 0, 2 * Math.PI);
        ctx.strokeStyle = node.isUnassigned ? "rgba(134,152,176,0.6)" : "rgba(204,120,92,0.6)";
        ctx.lineWidth = 2.5 / scale;
        ctx.setLineDash([4, 3]); ctx.stroke(); ctx.setLineDash([]);
      }
      if (node.isUnassigned) { ctx.setLineDash([4, 3]); ctx.strokeStyle = "#6a7a90"; ctx.lineWidth = 1.5; ctx.stroke(); ctx.setLineDash([]); }
      // Label below
      ctx.font = `${Math.max(10, 12 / scale)}px Inter, sans-serif`; ctx.fillStyle = "#3d3d3a"; ctx.textAlign = "center";
      ctx.fillText(node.label, x, y + r + 14 / scale);
      // Count inside circle
      if (node.count) {
        const fontSize = Math.max(10, Math.min(22, node.isUnassigned ? 12 : r * 0.6));
        ctx.font = `bold ${fontSize}px Inter, sans-serif`;
        ctx.fillStyle = node.isUnassigned ? "#e0e7f0" : "#ffffff";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(String(node.count), x, y + 1);
        ctx.textBaseline = "alphabetic";
      }
    } else {
      const color = ASSET_COLORS[node.assetType || ""] || "#c97a5e";
      const assetId = parseInt(String(node.id).replace("asset-", ""));
      const img = !isNaN(assetId) ? thumbCache.current.get(assetId) : undefined;
      const showLabel = scale >= 1.0 && !!node.label;
      if (img && (node.assetType === "image" || node.assetType === "video")) {
        const maxDim = 60, ratio = img.naturalWidth / img.naturalHeight;
        let w = maxDim, h = maxDim;
        if (ratio > 1) h = maxDim / ratio; else w = maxDim * ratio;
        ctx.save(); ctx.beginPath(); ctx.rect(x - w / 2, y - h / 2, w, h); ctx.clip();
        ctx.drawImage(img, x - w / 2, y - h / 2, w, h); ctx.restore();
        ctx.strokeStyle = color; ctx.lineWidth = 1.5 / scale; ctx.strokeRect(x - w / 2, y - h / 2, w, h);
      } else {
        const r = 3.5; ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill();
        if (showLabel) { ctx.font = `${Math.max(9, 10 / scale)}px Inter, sans-serif`; ctx.fillStyle = "#5c5a54"; ctx.textAlign = "center"; ctx.fillText(node.label, x, y + r + 12 / scale); }
      }
    }
  }, [searchIdSet]);

  const handleNodeClick = useCallback((node: FgNode) => {
    if (node.isAgg) {
      if (node.id === "unassigned") { onSelectNode(null, t("common.unassigned")); }
      else if (String(node.id).startsWith("node-")) {
        const nid = parseInt(String(node.id).replace("node-", ""));
        const next = new Set(expandedRef.current);
        if (next.has(nid)) next.delete(nid); else next.add(nid);
        onExpandedChange(next);
      }
    } else { const aid = parseInt(String(node.id).replace("asset-", "")); if (!isNaN(aid)) onSelectAsset(aid); }
  }, [onSelectNode, onSelectAsset, onExpandedChange]);

  const S = { c: "#faf9f5", h: "#e6dfd8", i: "#141413", m: "#6c6a64" };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", background: S.c }}>
      <ForceGraph2D ref={fgRef} graphData={fgData} nodeId="id" nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={(node, color, ctx) => {
          const n = node as FgNode;
          const r = n.isAgg
            ? (n.isUnassigned ? 16 : Math.max(12, Math.min(55, (n.count || 1) * 5)))
            : 5;
          ctx.beginPath(); ctx.arc(node.x!, node.y!, r, 0, 2 * Math.PI); ctx.fillStyle = color; ctx.fill();
        }}
        linkWidth={2} linkColor={() => "#e0dcd4"} onNodeClick={handleNodeClick}
        onNodeDrag={(node) => {
          const n = node as FgNode;
          if (n.isAgg) return;
          const ax = node.x!, ay = node.y!;
          // Freeze only the targeted agg node, unfreeze previous
          const prevFrozen = dragTargetAggId.current;
          dragTargetAggId.current = null;
          nodeMap.current.forEach((target) => {
            if (!target.isAgg) return;
            // Unassigned node: use fixed radius
            const r = target.isUnassigned ? 16 : Math.max(12, Math.min(55, (target.count || 1) * 5));
            const dx = ax - (target.x || 0), dy = ay - (target.y || 0);
            if (Math.sqrt(dx * dx + dy * dy) < r + 20) {
              // Unfreeze previous target if different from new
              if (prevFrozen && prevFrozen !== String(target.id)) {
                const old = nodeMap.current.get(prevFrozen);
                if (old) { old.fx = undefined; old.fy = undefined; }
              }
              dragTargetAggId.current = String(target.id);
              if (target.x != null && target.y != null) {
                target.fx = target.x; target.fy = target.y;
              }
            } else if (prevFrozen === String(target.id)) {
              // Moved away from previous target, unfreeze it
              target.fx = undefined; target.fy = undefined;
              dragTargetAggId.current = null;
            }
          });
          if (dragHighlightRef.current !== (dragTargetAggId.current ? 1 : 0)) {
            dragHighlightRef.current = dragTargetAggId.current ? 1 : 0;
            try { fgRef.current?.refresh?.(); } catch {}
          }
        }}
        onNodeDragEnd={(node) => {
          const n = node as FgNode;
          const targetId = dragTargetAggId.current;
          dragTargetAggId.current = null;
          dragHighlightRef.current = 0;
          // Unfreeze all
          nodeMap.current.forEach((target) => {
            if (target.isAgg) { target.fx = undefined; target.fy = undefined; }
          });
          try { fgRef.current?.refresh?.(); } catch {}
          if (n.isAgg || !targetId || !onAssetDrop) return;
          const assetId = parseInt(String(n.id).replace("asset-", ""));
          if (isNaN(assetId)) return;
          if (targetId === "unassigned") {
            // Find all nodes this asset belongs to
            const nodes = [] as number[];
            for (const [nid, assets] of edgeMap) {
              if (assets.some((e: any) => e.asset_id === assetId)) {
                nodes.push(nid);
              }
            }
            if (nodes.length > 0) {
              onAssetDrop(assetId, nodes, true);
            }
          } else {
            const nodeId = parseInt(targetId.replace("node-", ""));
            const existingAssets = edgeMap.get(nodeId) || [];
            if (existingAssets.some((e: any) => e.asset_id === assetId)) return;
            onAssetDrop(assetId, nodeId, false);
          }
        }}
        onBackgroundClick={() => onSelectNode(null)}
        onZoom={(z: { k: number }) => setZoomPercent(Math.round(z.k * 100))}
        onEngineStop={() => {
          if (chargeSettled.current) return;
          chargeSettled.current = true;
          try { fgRef.current?.d3Force?.("charge")?.strength?.(-1); } catch {}
          try { fgRef.current?.refresh?.(); } catch {}
        }}
        cooldownTicks={100} d3VelocityDecay={0.4} d3AlphaDecay={0.015}
      />
      <div style={{ position: "absolute", top: 8, right: 8, zIndex: 10, background: "rgba(250,249,245,0.92)", padding: "8px 12px", borderRadius: 6, border: `1px solid ${S.h}`, fontSize: 12, color: S.m, lineHeight: "20px" }}>
        <div style={{ fontWeight: 600, color: S.i, marginBottom: 4 }}>{t("graph.legend")}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: "50%", background: "#e8623a" }} />{t("graph.aggregation_node")}（{t("graph.node_size")}={t("graph.asset_count")}）</div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ display: "inline-block", width: 12, height: 12, borderRadius: "50%", border: "2px dashed #6a7a90", background: "#8698b0" }} />{t("graph.unassigned_node")}</div>
        {Object.entries(ASSET_COLORS).map(([t, c]) => <div key={t} style={{ display: "flex", alignItems: "center", gap: 6 }}><span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: c }} />{ASSET_LABELS[t] || t}</div>)}
      </div>
      <div style={{ position: "absolute", bottom: 8, left: 8, zIndex: 10, display: "flex", gap: 4 }}>
        <button onClick={() => { const z = fgRef.current?.zoom() || 1; fgRef.current?.zoom(z * 1.2, 400); }} style={{ width: 28, height: 28, border: `1px solid ${S.h}`, borderRadius: 4, background: S.c, cursor: "pointer", color: S.i, fontSize: 16 }}>+</button>
        <button onClick={() => { const z = fgRef.current?.zoom() || 1; fgRef.current?.zoom(z * 0.8, 400); }} style={{ width: 28, height: 28, border: `1px solid ${S.h}`, borderRadius: 4, background: S.c, cursor: "pointer", color: S.i, fontSize: 16 }}>−</button>
        <span style={{ fontSize: 11, color: S.m, lineHeight: "28px", padding: "0 4px", minWidth: 36, textAlign: "center" }}>{zoomPercent}%</span>
        <button onClick={() => fgRef.current?.zoomToFit(400, 50)} style={{ width: 28, height: 28, border: `1px solid ${S.h}`, borderRadius: 4, background: S.c, cursor: "pointer", color: S.i }}>⌂</button>
        <button onClick={onReload} style={{ width: 28, height: 28, border: `1px solid ${S.h}`, borderRadius: 4, background: S.c, cursor: "pointer" }}>🔄</button>
      </div>
    </div>
  );
}

function arePropsEqual(_prev: Props, _next: Props) {
  // Allow onReload to differ (inline function); compare data props
  return (
    _prev.graphData === _next.graphData &&
    _prev.selectedNodeId === _next.selectedNodeId &&
    _prev.selectedNodeName === _next.selectedNodeName &&
    _prev.searchResults === _next.searchResults &&
    _prev.filteredAssets === _next.filteredAssets &&
    _prev.hasActiveFilter === _next.hasActiveFilter &&
    _prev.expandedNodes === _next.expandedNodes
  );
}

export default memo(GraphView, arePropsEqual);
