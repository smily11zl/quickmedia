import { useState, useEffect, useRef } from "react";
import AddAssetModal from "./AddAssetModal";
import Toast from "./Toast";
import ConfirmModal from "./ConfirmModal";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface Node {
  id: number;
  name: string;
  description: string;
  asset_count: number;
  created_at?: string;
}

interface AggStatus {
  status: string;
  task?: {
    mode: string;
    status: string;
    error?: string;
  };
}

interface Props {
  onSelectNode: (nodeId: number | null, nodeName?: string) => void;
  selectedNodeId: number | null;
  onRefreshAssets?: (nodeId: number) => void;
  refreshKey?: number;
  onGraphRefresh?: (newNodeId?: number) => void;
  onGraphFullReload?: () => void;
  onSelectAsset?: (id: number) => void;
  selectedAssetId?: number | null;
  unassigned?: { id: number; filename: string; asset_type: string }[];
}

function NodePanel({ onSelectNode, selectedNodeId, onRefreshAssets, refreshKey, onGraphRefresh, onGraphFullReload, onSelectAsset, selectedAssetId, unassigned }: Props) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [aggStatus, setAggStatus] = useState<AggStatus>({ status: "idle" });
  const lastAggMode = useRef("");
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: number } | null>(null);
  const [editNode, setEditNode] = useState<{ id: number; name: string; desc: string } | null>(null);
  const [addModal, setAddModal] = useState<{ nodeId: number; nodeName: string } | null>(null);
  const [removeModal, setRemoveModal] = useState<{ nodeId: number; nodeName: string } | null>(null);
  const [toast, setToast] = useState<{ message: string; type?: "info" | "error" } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [deletingNodeId, setDeletingNodeId] = useState<number | null>(null);
  const [creatingNode, setCreatingNode] = useState(false);
  const [analyzingNodeId, setAnalyzingNodeId] = useState<number | null>(null);
  const [confirmFullAgg, setConfirmFullAgg] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [unassignedExpanded, setUnassignedExpanded] = useState(false);

  const refreshNodeAssets = (nodeId: number) => {

    setNodeAssets(prev => { const m = new Map(prev); m.delete(nodeId); return m; });
    expandedNodes.forEach(nid => {
      fetch('/api/nodes/' + nid + '/assets').then(r => r.json()).then(d => {
        setNodeAssets(prev => new Map(prev.set(nid, d.items || [])));
      });
    });
    fetchNodes();
  };
  const [nodeAssets, setNodeAssets] = useState(new Map());

  const fetchNodes = () => {
    fetch("/api/nodes")
      .then((r) => r.json())
      .then(setNodes);
  };

  useEffect(() => { fetchNodes(); setNodeAssets(new Map()); expandedNodes.forEach(nid => { fetch('/api/nodes/' + nid + '/assets').then(r => r.json()).then(d => { setNodeAssets(prev => new Map(prev.set(nid, d.items || []))); }); }); }, [refreshKey]);

  const fetchStatus = () => {
    fetch("/api/aggregation/status")
      .then((r) => r.json())
      .then(setAggStatus);
  };

  useEffect(() => {
    fetchNodes();
    fetchStatus();
    const i = setInterval(fetchStatus, 3000);
    return () => clearInterval(i);
  }, []);

  // Refetch nodes when aggregation completes
  useEffect(() => {
    if (aggStatus.task?.status === "done") {
      setNodeAssets(new Map()); // clear all caches
      fetchNodes();
      if (lastAggMode.current === "full") {
        onGraphFullReload?.();
      } else {
        onGraphRefresh?.();
      }
      lastAggMode.current = "";
    }
  }, [aggStatus.task?.status]);

  const runAggregation = (mode: string) => {
    fetch("/api/aggregation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          lastAggMode.current = mode;
          fetchStatus();
        } else {
          setToast({ message: d.detail || "提交失败", type: "error" });
        }
      });
  };

  const deleteNode = (id: number) => {
    setConfirmDelete(id);
  };

  const doDelete = () => {
    if (!confirmDelete) return;
    setDeletingNodeId(confirmDelete);
    fetch(`/api/nodes/${confirmDelete}`, { method: "DELETE" }).then((r) => {
      if (r.ok) {
        setTimeout(() => {
          setNodes(nodes.filter((n) => n.id !== confirmDelete));
          if (selectedNodeId === confirmDelete) onSelectNode(null);
          setDeletingNodeId(null);
          onGraphRefresh?.();
          setNodeAssets(prev => { const m = new Map(prev); m.delete(confirmDelete); return m; }); expandedNodes.forEach(nid => { if (nid !== confirmDelete) fetch('/api/nodes/' + nid + '/assets').then(r => r.json()).then(d => { setNodeAssets(prev => new Map(prev.set(nid, d.items || []))); }); });
        }, 300);
      } else {
        setDeletingNodeId(null);
      }
      setConfirmDelete(null);
    });
  };

  const saveEdit = () => {
    if (!editNode) return;
    fetch(`/api/nodes/${editNode.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editNode.name, description: editNode.desc }),
    }).then(() => {
      setEditNode(null);
      fetchNodes();
    });
  };

  const saveCreate = () => {
    if (!editNode || !editNode.name.trim()) return;
    fetch("/api/nodes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editNode.name.trim(), description: editNode.desc }),
    }).then((r) => r.json()).then((d) => {
      setEditNode(null);
      setCreatingNode(false);
      fetchNodes();
      onGraphRefresh?.(d.id);
      return d.id;
    });
  };

  const saveCreateAndAnalyze = () => {
    if (!editNode || !editNode.name.trim()) return;
    fetch("/api/nodes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editNode.name.trim(), description: editNode.desc }),
    }).then((r) => r.json()).then((d) => {
      setEditNode(null);
      setCreatingNode(false);
      fetchNodes();
      onGraphRefresh?.(d.id);
      // Trigger analyze_append on the new node
      setTimeout(() => runAnalyzeAppend(d.id), 200);
    });
  };

  const runAnalyzeAppend = (nodeId: number) => {
    setAnalyzingNodeId(nodeId);
    fetch(`/api/nodes/${nodeId}/analyze-append`, { method: "POST" })
      .then((r) => r.json())
      .then((d) => {
        setAnalyzingNodeId(null);
        if (d.ok) {
          setToast({ message: `分析完成，已添加 ${d.added} 个素材`, type: "info" });
          fetchNodes();
          onGraphRefresh?.();
          // If this node is currently selected, refresh asset list
          if (selectedNodeId === nodeId && onRefreshAssets) {
            onRefreshAssets(nodeId);
          }
          setNodeAssets(prev => { const m = new Map(prev); m.delete(nodeId); return m; }); expandedNodes.forEach(nid => { fetch('/api/nodes/' + nid + '/assets').then(r => r.json()).then(d => { setNodeAssets(prev => new Map(prev.set(nid, d.items || []))); }); });
        } else {
          setToast({ message: "分析失败", type: "error" });
        }
      })
      .catch(() => {
        setAnalyzingNodeId(null);
        setToast({ message: "分析失败", type: "error" });
      });
  };

  
  // Auto-refresh grid/list when selected node assets change
  useEffect(() => {
    if (selectedNodeId && nodeAssets.has(selectedNodeId) && onRefreshAssets) {
      onRefreshAssets(selectedNodeId);
    }
  }, [nodeAssets]);

  const isRunning = aggStatus.task?.status === "pending" || aggStatus.task?.status === "processing";
  const isFailed = aggStatus.task?.status === "failed";

  return (
    <div className="flex flex-col gap-2">
      {/* Action buttons */}
      <div className="flex gap-1 flex-wrap">
        <button
          onClick={() => {
            if (nodes.length > 0) setConfirmFullAgg(true);
            else runAggregation("full");
          }}
          disabled={isRunning}
          className="text-[11px] px-2 py-1 rounded font-medium"
          style={{
            backgroundColor: isRunning ? S.s : S.r,
            color: isRunning ? S.ms : S.w,
            cursor: isRunning ? "not-allowed" : "pointer",
            opacity: isRunning ? 0.6 : 1,
          }}
        >
          全量分析
        </button>
        {nodes.length > 0 && (
          <>
            <button
              onClick={() => runAggregation("full_append")}
              disabled={isRunning}
              className="text-[11px] px-2 py-1 rounded font-medium"
              style={{
                backgroundColor: isRunning ? S.s : S.r,
                color: isRunning ? S.ms : S.w,
                cursor: isRunning ? "not-allowed" : "pointer",
                opacity: isRunning ? 0.6 : 1,
              }}
            >
              全量追加
            </button>
            <button
              onClick={() => runAggregation("append")}
              disabled={isRunning}
              className="text-[11px] px-2 py-1 rounded font-medium"
              style={{
                backgroundColor: isRunning ? S.s : S.r,
                color: isRunning ? S.ms : S.w,
                cursor: isRunning ? "not-allowed" : "pointer",
                opacity: isRunning ? 0.6 : 1,
              }}
            >
              追加分析
            </button>
          </>
        )}
      </div>

      {/* New node button */}
      <button
        onClick={() => { setCreatingNode(true); setEditNode({ id: 0, name: "", desc: "" }); }}
        className="w-full text-left px-3 py-1.5 rounded-md text-sm border border-dashed"
        style={{
          fontFamily: "'Inter', sans-serif",
          color: S.m,
          borderColor: S.h,
          backgroundColor: "transparent",
        }}
      >
        + 新建节点
      </button>

      {/* Status banner */}
      {isRunning && (
        <div
          className="text-xs px-2 py-1.5 rounded text-center"
          style={{ backgroundColor: "#fef3c7", color: "#92400e" }}
        >
          聚合分析中...
        </div>
      )}
      {isFailed && (
        <div
          className="text-xs px-2 py-1.5 rounded"
          style={{ backgroundColor: "#fee2e2", color: "#991b1b" }}
        >
          聚合失败: {aggStatus.task?.error || "未知错误"}
        </div>
      )}

      {/* Node list */}
      <div className="flex flex-col gap-0.5" style={{ maxHeight: "calc(100vh - 250px)", overflowY: "auto" }}>
        {nodes.map((node) => (
          <div key={node.id} style={{
            opacity: deletingNodeId === node.id ? 0 : 1,
            transition: "opacity 0.3s ease",
            pointerEvents: deletingNodeId === node.id ? "none" : "auto",
          }}>
            <div className="flex items-center">
              <button
                data-testid="expand-arrow"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpandedNodes(prev => {
                    const next = new Set(prev);
                    if (next.has(node.id)) {
                      next.delete(node.id);
                    } else {
                      next.add(node.id);
                      if (!nodeAssets.has(node.id)) {
                        fetch("/api/nodes/" + node.id + "/assets").then(r => r.json()).then(d => {
                          setNodeAssets(prevMap => new Map(prevMap.set(node.id, d.items || [])));
                        });
                      }
                    }
                    return next;
                  });
                }}
                className="text-[11px] px-0.5 hover:opacity-70"
                style={{ color: S.ms, cursor: "pointer", background: "none", border: "none" }}
                title="展开/折叠"
              >
                {expandedNodes.has(node.id) ? "▼" : "▶"}
              </button>
              <button
                onClick={() => { if (node.id === selectedNodeId) onSelectNode(null); else onSelectNode(node.id, node.name); }}
                onContextMenu={(e) => {
                  e.preventDefault();
                  setCtxMenu({ x: e.clientX, y: e.clientY, nodeId: node.id });
                }}
                onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}
                onDrop={(e) => {
                  e.preventDefault();
                  try {
                    const raw = e.dataTransfer.getData("text/plain");

                    const data = JSON.parse(raw);
                    if (data.source_node_id === node.id) return;
                    // Check if already in this node
                    const existing = nodeAssets.get(node.id);
                    if (existing && existing.some((a: any) => a.id === data.asset_id)) {
                      setToast({ message: "\u8282\u70b9\uff1a" + node.name + "\u5df2\u6536\u5f55\u7d20\u6750" + data.filename, type: "info" });
                      return;
                    }
                    fetch("/api/nodes/" + node.id + "/assets", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ asset_ids: [data.asset_id] }),
                    }).then(r => r.json()).then(d => {
                      if (d.ok) {
                        setToast({ message: "\u5df2\u5206\u914d\u5230\u8282\u70b9\uff1a" + node.name, type: "info" });
                        // Refresh source and target caches
                        if (data.source_node_id && data.source_node_id !== "unassigned") {
                          fetch("/api/nodes/" + data.source_node_id + "/assets").then(r => r.json()).then(d2 => {
                            setNodeAssets(prev => new Map(prev.set(data.source_node_id, d2.items || [])));
                          });
                        } else {
                          // source was unassigned - graph will refresh
                        }
                        fetch("/api/nodes/" + node.id + "/assets").then(r => r.json()).then(d2 => {
                          setNodeAssets(prev => new Map(prev.set(node.id, d2.items || [])));
                        });
                        fetchNodes();
                        onGraphRefresh?.();
                        if (selectedNodeId === node.id && onRefreshAssets) onRefreshAssets(node.id);
                        if (data.source_node_id && selectedNodeId === data.source_node_id && onRefreshAssets) onRefreshAssets(data.source_node_id);
                      }
                    });
                  } catch {}
                }}
                className="flex-1 min-w-0 text-left pl-1 py-1.5 rounded-md text-sm hover:bg-opacity-50 transition-colors"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  backgroundColor: selectedNodeId === node.id ? S.d : S.s,
                  color: S.i,
                  borderLeft: selectedNodeId === node.id ? `3px solid ${S.r}` : "3px solid transparent",
                }}
              >
                <div className="flex justify-between items-center">
                  <span className="truncate">{node.name}</span>
                  <div className="flex items-center gap-1">
                    {analyzingNodeId === node.id && (
                      <span
                        className="inline-block rounded-full border-2 border-t-transparent animate-spin"
                        style={{ width: 14, height: 14, borderColor: `${S.r} transparent ${S.r} ${S.r}` }}
                        title="分析中..."
                      />
                    )}
                    <span className="text-[10px]" style={{ color: S.ms }}>
                      ({node.asset_count})
                    </span>
                  </div>
                </div>
                {node.description && (
                  <p className="text-[10px] truncate mt-0.5" style={{ color: S.ms }}>
                    {node.description}
                  </p>
                )}
              </button>
            </div>
            {expandedNodes.has(node.id) && (
              <div className="ml-5 mt-0.5">
                {!nodeAssets.has(node.id) ? (
                  <span className="text-[10px]" style={{ color: S.ms }}>加载中...</span>
                ) : nodeAssets.get(node.id)!.length === 0 ? (
                  <span className="text-[10px]" style={{ color: S.ms }}>暂无素材</span>
                ) : (
                  nodeAssets.get(node.id)!.map((a: any) => (
                    <div key={a.id} onClick={() => onSelectAsset?.(a.id)}
                      className="flex items-center gap-1.5 py-0.5 px-1 rounded cursor-pointer hover:brightness-95"
                      style={{ color: S.i, backgroundColor: selectedAssetId === a.id ? S.rb : "transparent" }}
                      title={a.filename}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData("text/plain", JSON.stringify({
                          asset_id: a.id,
                          source_node_id: node.id,
                          filename: a.filename,
                        }));
                        e.dataTransfer.effectAllowed = "move";

                      }}
                    >
                      <span className="text-[10px] flex-shrink-0" style={{ color: S.ms }}>
                        {a.asset_type === "image" ? "图片" : a.asset_type === "video" ? "视频" : a.asset_type === "audio" ? "音频" : "文档"}
                      </span>
                      <span className="text-[10px] truncate">{a.filename}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
        {/* Unassigned virtual node */}
        {unassigned && (
          <div style={{
            borderTop: "1px dashed " + S.h,
            marginTop: 4,
            paddingTop: 4,
          }}>
            <div className="flex items-center">
              <button
                onClick={() => setUnassignedExpanded(prev => !prev)}
                className="text-[11px] px-0.5 hover:opacity-70"
                style={{ color: S.ms, cursor: "pointer", background: "none", border: "none" }}
                title="展开/折叠"
              >
                {unassignedExpanded ? "\u25bc" : "\u25b6"}
              </button>
              <div className="flex-1 text-left pl-1 py-1.5 rounded-md text-sm" style={{ color: S.ms, fontStyle: "italic", opacity: 0.8 }}
                onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}
                onDrop={(e) => {
                  e.preventDefault();
                  try {
                    const raw = e.dataTransfer.getData("text/plain");

                    const data = JSON.parse(raw);
                    if (data.source_node_id === "unassigned") return;
                    // Disconnect from ALL nodes containing this asset
                    Promise.all(
                      Array.from(nodeAssets.keys()).map(nid => 
                        fetch("/api/nodes/" + nid + "/assets/" + data.asset_id, { method: "DELETE" })
                          .catch(() => {})
                      )
                    ).then(() => {
                      // Also delete from source_node_id if not already covered
                      if (data.source_node_id && !nodeAssets.has(data.source_node_id)) {
                        return fetch("/api/nodes/" + data.source_node_id + "/assets/" + data.asset_id, { method: "DELETE" }).catch(() => {});
                      }
                    }).then(() => {
                      setToast({ message: "\u5df2\u53d6\u6d88\u5206\u914d", type: "info" });
                      setNodeAssets(new Map()); // clear all caches
                      expandedNodes.forEach(nid => {
                        fetch("/api/nodes/" + nid + "/assets").then(r => r.json()).then(d => {
                          setNodeAssets(prev => new Map(prev.set(nid, d.items || [])));
                        });
                      });
                      fetchNodes();
                      onGraphRefresh?.();
                      if (data.source_node_id && selectedNodeId === data.source_node_id && onRefreshAssets) onRefreshAssets(data.source_node_id);
                    });
                  } catch {}
                }}
              >
                <span>未分配</span>
                <span className="text-[10px] ml-1" style={{ color: S.ms }}>({unassigned.length})</span>
              </div>
            </div>
            {unassignedExpanded && (
              <div className="ml-5 mt-0.5">
                {unassigned.length === 0 ? (
                  <span className="text-[10px]" style={{ color: S.ms }}>暂无素材</span>
                ) : (
                  unassigned.map((a) => (
                    <div key={a.id} onClick={() => onSelectAsset?.(a.id)}
                      className="flex items-center gap-1.5 py-0.5 px-1 rounded cursor-pointer hover:brightness-95"
                      style={{ color: S.i, backgroundColor: selectedAssetId === a.id ? S.rb : "transparent" }}
                      title={a.filename}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData("text/plain", JSON.stringify({
                            asset_id: a.id,
                            source_node_id: "unassigned",
                            filename: a.filename,
                          }));
                          e.dataTransfer.effectAllowed = "move";
                        }}
                      >
                      <span className="text-[10px] flex-shrink-0" style={{ color: S.ms }}>
                        {a.asset_type === "image" ? "图片" : a.asset_type === "video" ? "视频" : a.asset_type === "audio" ? "音频" : "文档"}
                      </span>
                      <span className="text-[10px] truncate">{a.filename}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
        {nodes.length === 0 && !isRunning && (
          <p className="text-xs text-center py-4" style={{ color: S.ms }}>
            暂无聚合节点，点击"全量分析"开始
          </p>
        )}
      </div>

      {/* Context menu */}
      {ctxMenu && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setCtxMenu(null)} />
          <div
            className="fixed z-50 rounded-md shadow-lg border py-1 min-w-[140px]"
            style={{ left: ctxMenu.x, top: ctxMenu.y, backgroundColor: S.c, borderColor: S.h }}
          >
            <button
              onClick={() => {
                const n = nodes.find((nd) => nd.id === ctxMenu.nodeId);
                if (n) setEditNode({ id: n.id, name: n.name, desc: n.description || "" });
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.i }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              重命名 / 编辑描述
            </button>
            <button
              onClick={() => {
                runAnalyzeAppend(ctxMenu.nodeId);
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.i }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              分析追加到此节点
            </button>
            <button
              onClick={() => {
                deleteNode(ctxMenu.nodeId);
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.r }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.rb)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              删除节点
            </button>
            <div className="border-t my-0.5" style={{ borderColor: S.h }} />
            <button
              onClick={() => {
                const n = nodes.find((nd) => nd.id === ctxMenu.nodeId);
                if (n) setAddModal({ nodeId: n.id, nodeName: n.name });
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.i }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              手动添加素材
            </button>
            <button
              onClick={() => {
                const n = nodes.find((nd) => nd.id === ctxMenu.nodeId);
                if (n) setRemoveModal({ nodeId: n.id, nodeName: n.name });
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.i }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              手动移除素材
            </button>
            <div className="border-t my-0.5" style={{ borderColor: S.h }} />
            <button
              onClick={() => {
                const n = nodes.find((nd) => nd.id === ctxMenu.nodeId);
                onSelectNode(ctxMenu.nodeId, n?.name);
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.i }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              查看素材
            </button>
          </div>
        </>
      )}

      {/* Edit / Create node modal */}
      {editNode && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => { setEditNode(null); setCreatingNode(false); }} />
          <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ backgroundColor: "rgba(0,0,0,0.15)" }}
          >
            <div
              className="rounded-xl p-5 w-80 shadow-lg border"
              style={{ backgroundColor: S.c, borderColor: S.h }}
            >
              <h3 className="text-sm font-medium mb-3" style={{ color: S.i }}>
                {creatingNode ? "新建节点" : "编辑节点"}
              </h3>
              <div className="flex flex-col gap-3">
                <div>
                  <label className="text-[11px] mb-1 block" style={{ color: S.ms }}>
                    节点名
                  </label>
                  <input
                    type="text"
                    value={editNode.name}
                    onChange={(e) => setEditNode({ ...editNode, name: e.target.value })}
                    className="w-full px-2 py-1 text-sm rounded-md outline-none border"
                    style={{ borderColor: S.h, color: S.i, backgroundColor: S.c }}
                  />
                </div>
                <div>
                  <label className="text-[11px] mb-1 block" style={{ color: S.ms }}>
                    描述
                  </label>
                  <textarea
                    value={editNode.desc}
                    onChange={(e) => setEditNode({ ...editNode, desc: e.target.value })}
                    className="w-full px-2 py-1 text-sm rounded-md outline-none border resize-none"
                    rows={3}
                    style={{ borderColor: S.h, color: S.i, backgroundColor: S.c }}
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => { setEditNode(null); setCreatingNode(false); }}
                    className="text-xs px-3 py-1 rounded-md"
                    style={{ backgroundColor: S.s, color: S.m }}
                  >
                    取消
                  </button>
                  <button
                    onClick={creatingNode ? saveCreate : saveEdit}
                    disabled={creatingNode && !editNode.name.trim()}
                    className="text-xs px-3 py-1 rounded-md font-medium"
                    style={{
                      backgroundColor: (creatingNode && !editNode.name.trim()) ? S.h : S.r,
                      color: S.w,
                    }}
                  >
                    保存
                  </button>
                  {creatingNode && (
                    <button
                      onClick={saveCreateAndAnalyze}
                      disabled={!editNode.name.trim()}
                      className="text-xs px-3 py-1 rounded-md font-medium"
                      style={{
                        backgroundColor: !editNode.name.trim() ? S.h : S.r,
                        color: S.w,
                      }}
                    >
                      保存并分析
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
      {addModal && (
        <AddAssetModal
          nodeId={addModal.nodeId}
          nodeName={addModal.nodeName}
          onClose={() => { setAddModal(null); if (addModal) { setNodeAssets(prev => { const m = new Map(prev); m.delete(addModal.nodeId); return m; }); expandedNodes.forEach(nid => { fetch('/api/nodes/' + nid + '/assets').then(r => r.json()).then(d => { setNodeAssets(prev => new Map(prev.set(nid, d.items || []))); }); }); fetchNodes(); if (selectedNodeId === addModal.nodeId && onRefreshAssets) onRefreshAssets(addModal.nodeId); } }}
          onAdded={() => { fetchNodes(); onGraphRefresh?.(); if (selectedNodeId === addModal?.nodeId && onRefreshAssets) onRefreshAssets(addModal.nodeId); }}
        />
      )}
      {removeModal && (
        <AddAssetModal
          nodeId={removeModal.nodeId}
          nodeName={removeModal.nodeName}
          mode="remove"
          onClose={() => { const rnid = removeModal?.nodeId; setRemoveModal(null); if (rnid) refreshNodeAssets(rnid); if (selectedNodeId === rnid && onRefreshAssets) onRefreshAssets(rnid); }}
          onAdded={() => {
            fetchNodes();
            onGraphRefresh?.();
            if (selectedNodeId === removeModal.nodeId && onRefreshAssets) {
              onRefreshAssets(removeModal.nodeId);
            }
          }}
        />
      )}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {confirmFullAgg && (
        <ConfirmModal
          title="全量分析"
          message={`将删除全部 ${nodes.length} 个已有节点，重新分析所有素材生成新节点。此操作不可撤销。`}
          confirmText="继续分析"
          confirmColor="error"
          onConfirm={() => { setConfirmFullAgg(false); runAggregation("full"); }}
          onCancel={() => setConfirmFullAgg(false)}
        />
      )}
      {confirmDelete !== null && (
        <ConfirmModal
          title="删除节点"
          message={`确定删除「${nodes.find(n => n.id === confirmDelete)?.name || ""}」？素材不会被删除。`}
          confirmText="删除"
          confirmColor="error"
          loading={deletingNodeId === confirmDelete}
          onConfirm={doDelete}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}

export default NodePanel;
