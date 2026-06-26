import { useState, useEffect } from "react";
import AddAssetModal from "./AddAssetModal";

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
}

function NodePanel({ onSelectNode, selectedNodeId }: Props) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [aggStatus, setAggStatus] = useState<AggStatus>({ status: "idle" });
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; nodeId: number } | null>(null);
  const [editNode, setEditNode] = useState<{ id: number; name: string; desc: string } | null>(null);
  const [addModal, setAddModal] = useState<{ nodeId: number; nodeName: string } | null>(null);

  const fetchNodes = () => {
    fetch("/api/nodes")
      .then((r) => r.json())
      .then(setNodes);
  };

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
      fetchNodes();
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
          fetchStatus();
        } else {
          alert(d.detail || "提交失败");
        }
      });
  };

  const deleteNode = (id: number) => {
    if (!confirm("确认删除此节点？")) return;
    fetch(`/api/nodes/${id}`, { method: "DELETE" }).then(() => {
      setNodes(nodes.filter((n) => n.id !== id));
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

  const isRunning = aggStatus.task?.status === "pending" || aggStatus.task?.status === "processing";
  const isFailed = aggStatus.task?.status === "failed";

  return (
    <div className="flex flex-col gap-2">
      {/* Action buttons */}
      <div className="flex gap-1 flex-wrap">
        <button
          onClick={() => runAggregation("full")}
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
          <div key={node.id}>
            <button
              onClick={() => { if (node.id === selectedNodeId) onSelectNode(null); else onSelectNode(node.id, node.name); }}
              onContextMenu={(e) => {
                e.preventDefault();
                setCtxMenu({ x: e.clientX, y: e.clientY, nodeId: node.id });
              }}
              className="w-full text-left px-3 py-1.5 rounded-md text-sm hover:bg-opacity-50 transition-colors"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: selectedNodeId === node.id ? S.d : S.s,
                color: S.i,
                borderLeft: selectedNodeId === node.id ? `3px solid ${S.r}` : "3px solid transparent",
              }}
            >
              <div className="flex justify-between items-center">
                <span className="truncate">{node.name}</span>
                <span className="text-[10px] opacity-50" style={{ color: S.ms }}>
                  ({node.asset_count})
                </span>
              </div>
              {node.description && (
                <p className="text-[10px] truncate mt-0.5" style={{ color: S.ms }}>
                  {node.description}
                </p>
              )}
            </button>
          </div>
        ))}
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
              style={{ fontFamily: "'Inter', sans-serif", color: S.m }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              手动添加素材
            </button>
            <div className="border-t my-0.5" style={{ borderColor: S.h }} />
            <button
              onClick={() => {
                const n = nodes.find((nd) => nd.id === ctxMenu.nodeId);
                onSelectNode(ctxMenu.nodeId, n?.name);
                setCtxMenu(null);
              }}
              className="w-full text-left px-3 py-1.5 text-xs hover:bg-opacity-50"
              style={{ fontFamily: "'Inter', sans-serif", color: S.m }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = S.s)}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
            >
              查看素材
            </button>
          </div>
        </>
      )}

      {/* Edit node modal */}
      {editNode && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setEditNode(null)} />
          <div
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ backgroundColor: "rgba(250,249,245,0.7)" }}
          >
            <div
              className="rounded-xl p-5 w-80 shadow-lg border"
              style={{ backgroundColor: S.c, borderColor: S.h }}
            >
              <h3 className="text-sm font-medium mb-3" style={{ color: S.i }}>
                编辑节点
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
                    onClick={() => setEditNode(null)}
                    className="text-xs px-3 py-1 rounded-md"
                    style={{ backgroundColor: S.s, color: S.m }}
                  >
                    取消
                  </button>
                  <button
                    onClick={saveEdit}
                    className="text-xs px-3 py-1 rounded-md font-medium"
                    style={{ backgroundColor: S.r, color: S.w }}
                  >
                    保存
                  </button>
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
          onClose={() => setAddModal(null)}
          onAdded={() => fetchNodes()}
        />
      )}
    </div>
  );
}

export default NodePanel;
