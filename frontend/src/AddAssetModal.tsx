import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface Asset {
  id: number;
  filename: string;
  asset_type: string;
  size: number;
  path: string;
  visual_description?: string;
  ai_summary?: string;
  thumbnail_status: string;
}

const f=(b:number)=>{for(const u of["B","KB","MB","GB"]){if(b<1024)return `${b}${u}`;b=Math.floor(b/1024);}return `${b}TB`;};

interface Props {
  nodeId: number;
  nodeName: string;
  onClose: () => void;
  onAdded: () => void;
  mode?: "add" | "remove";
}

function AddAssetModal({ nodeId, nodeName, onClose, onAdded: _onAdded, mode = "add" }: Props) {
  const { t } = useTranslation();
  const [allAssets, setAllAssets] = useState<Asset[]>([]);
  const [filtered, setFiltered] = useState<Asset[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const url = mode === "remove"
      ? `/api/nodes/${nodeId}/assets?limit=500`
      : "/api/assets?limit=500";
    fetch(url)
      .then((r) => r.json())
      .then((d) => {
        const items = d.items || [];
        setAllAssets(items);
        setFiltered(items);
      });
  }, [nodeId, mode]);

  useEffect(() => {
    if (!query.trim()) {
      setFiltered(allAssets);
      return;
    }
    const q = query.toLowerCase();
    setFiltered(
      allAssets.filter(
        (a) =>
          a.filename.toLowerCase().includes(q) ||
          (a.visual_description || "").toLowerCase().includes(q) ||
          (a.ai_summary || "").toLowerCase().includes(q)
      )
    );
  }, [query, allAssets]);

  const toggle = (id: number) => {
    const n = new Set(selected);
    n.has(id) ? n.delete(id) : n.add(id);
    setSelected(n);
  };

  const selectAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map((a) => a.id)));
    }
  };

  const submit = () => {
    if (selected.size === 0) return;
    setLoading(true);
    if (mode === "remove") {
      // Batch unassign: call DELETE for each selected asset
      Promise.all(
        [...selected].map((aid) =>
          fetch(`/api/nodes/${nodeId}/assets/${aid}`, { method: "DELETE" })
        )
      )
        .then(() => { onClose(); })
        .finally(() => setLoading(false));
    } else {
      fetch(`/api/nodes/${nodeId}/assets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_ids: [...selected] }),
      })
        .then(() => { onClose(); })
        .finally(() => setLoading(false));
    }
  };

  const docI = (a: Asset) => {
    const x = a.filename.split(".").pop()?.toLowerCase() || "";
    const m: Record<string, string> = { pdf: "📕", md: "📝", txt: "📝", csv: "📊", json: "📋", xlsx: "📊", docx: "📄" };
    return m[x] || "📄";
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: "rgba(250,249,245,0.7)" }}>
        <div className="rounded-xl p-5 w-[480px] max-h-[80vh] flex flex-col shadow-lg border" style={{ backgroundColor: S.c, borderColor: S.h }}>
          <h3 className="text-sm font-medium mb-3" style={{ color: S.i }}>
            {mode === "remove" ? t("add_asset.remove_from", {name: nodeName}) : t("add_asset.add_to", {name: nodeName})}
          </h3>

          {/* Search */}
          <div className="relative mb-3">
            <input
              type="text"
              placeholder={t("add_asset.search_placeholder")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full px-3 py-1.5 text-sm rounded-md outline-none border"
              style={{ borderColor: S.h, color: S.i, backgroundColor: S.c }}
            />
            {query && (
              <button onClick={() => setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-xs" style={{ color: S.ms }}>✕</button>
            )}
          </div>

          {/* Select toolbar */}
          <div className="flex items-center gap-2 mb-2">
            <button onClick={selectAll} className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: S.s, color: S.m }}>
              {selected.size === filtered.length && filtered.length > 0 ? t("add_asset.deselect_all") : t("add_asset.select_all")}
            </button>
            <span className="text-[10px]" style={{ color: S.ms }}>
              {t("add_asset.selected_count", {selected: selected.size, total: filtered.length})}
            </span>
          </div>

          {/* Asset list */}
          <div className="flex-1 overflow-y-auto mb-3" style={{ maxHeight: "50vh" }}>
            <div className="flex flex-col gap-0.5">
              {filtered.map((a) => (
                <div
                  key={a.id}
                  onClick={() => toggle(a.id)}
                  className="flex items-center gap-3 px-2 py-1.5 rounded cursor-pointer hover:bg-opacity-50"
                  style={{ backgroundColor: selected.has(a.id) ? S.rb : "transparent" }}
                  onMouseEnter={(e) => { if (!selected.has(a.id)) e.currentTarget.style.backgroundColor = S.s; }}
                  onMouseLeave={(e) => { if (!selected.has(a.id)) e.currentTarget.style.backgroundColor = "transparent"; }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(a.id)}
                    readOnly
                    className="w-4 h-4 rounded accent-[#cc785c] flex-shrink-0"
                  />
                  <span className="text-sm">{a.asset_type === "video" ? "🎬" : a.asset_type === "audio" ? "🎵" : a.asset_type === "image" ? "🖼️" : docI(a)}</span>
                  <span className="text-sm flex-1 truncate" style={{ color: S.i }}>{a.filename}</span>
                  <span className="text-[10px] flex-shrink-0" style={{ color: S.ms }}>{f(a.size)}</span>
                </div>
              ))}
              {filtered.length === 0 && (
                <p className="text-xs text-center py-4" style={{ color: S.ms }}>{t("add_asset.no_match")}</p>
              )}
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-2 justify-end">
            <button onClick={onClose} className="text-xs px-3 py-1.5 rounded-md" style={{ backgroundColor: S.s, color: S.m }}>
              {t("common.cancel")}
            </button>
            <button
              onClick={submit}
              disabled={selected.size === 0 || loading}
              className="text-xs px-3 py-1.5 rounded-md font-medium"
              style={{ backgroundColor: selected.size > 0 ? S.r : S.s, color: selected.size > 0 ? S.w : S.ms, cursor: selected.size > 0 ? "pointer" : "not-allowed" }}
            >
              {mode === "remove"
                ? (loading ? t("add_asset.removing") : t("add_asset.confirm_remove", {count: selected.size}))
                : (loading ? t("add_asset.adding") : t("add_asset.confirm_add", {count: selected.size}))}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default AddAssetModal;
