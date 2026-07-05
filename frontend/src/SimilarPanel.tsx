import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface Asset {
  id: number; filename: string; asset_type: string; size: number;
  thumbnail_status: string; ai_status?: string;
  tags: { id: number; name: string; source: string }[];
  modified_at?: string; width?: number; height?: number; duration?: number;
  _distance?: number;
}

const f=(b:number)=>{for(const u of["B","KB","MB","GB"]){if(b<1024)return `${b}${u}`;b=Math.floor(b/1024);}return `${b}TB`;};

export default function SimilarPanel({ assetId, onClose, onSelect }: { assetId: number; onClose: () => void; onSelect?: (id: number) => void }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<Asset[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/assets/${assetId}/similar?limit=10`)
      .then(r => r.json())
      .then(d => { setItems(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [assetId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{backgroundColor: "rgba(0,0,0,0.3)"}} onClick={onClose}>
      <div className="w-full max-w-4xl max-h-[85vh] min-h-[300px] rounded-xl shadow-2xl flex flex-col overflow-hidden" style={{backgroundColor: S.c}} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3" style={{borderBottom: `1px solid ${S.h}`}}>
          <h2 className="text-sm font-medium" style={{color: S.i}}>{t("similar.title")}</h2>
          <button onClick={onClose} className="text-xs px-2 py-1 rounded" style={{color: S.ms, backgroundColor: S.s}}>✕ {t("common.close")}</button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading && (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm" style={{color: S.m}}>{t("similar.searching")}</p>
            </div>
          )}
          {!loading && items && items.length === 0 && (
            <div className="flex flex-col items-center justify-center h-48">
              <p className="text-3xl mb-2">🔍</p>
              <p className="text-sm" style={{color: S.m}}>{t("similar.not_found")}</p>
            </div>
          )}
          {!loading && items && items.length > 0 && (
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {items.map(a => (
                <div key={a.id} className="rounded-lg overflow-hidden border cursor-pointer hover:brightness-95 transition-all" style={{borderColor: S.h, backgroundColor: S.c}} onClick={() => onSelect?.(a.id)}>
                  <div className="aspect-square flex items-center justify-center" style={{backgroundColor: S.s}}>
                    {a.thumbnail_status==="done"
                      ? <img src={`/api/thumbnails/${a.id}`} className="w-full h-full object-cover"/>
                      : <span className="text-2xl">{a.asset_type==="video"?"🎬":a.asset_type==="audio"?"🎵":"📄"}</span>}
                  </div>
                  <div className="p-2">
                    <p className="text-[10px] font-medium truncate" style={{color: S.i}}>{a.filename}</p>
                    <p className="text-[9px] mt-0.5" style={{color: S.ms}}>{f(a.size)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
