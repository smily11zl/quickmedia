import { useState, useEffect, useRef } from "react";
import ModelManager from "./ModelManager";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface Props {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: Props) {
  const [tab, setTab] = useState<"basic" | "models" | "prompts">("basic");
  const [cfn, setCfn] = useState(1);
  const [cto, setCto] = useState(300);
  const [initCfn, setInitCfn] = useState(1);
  const [initCto, setInitCto] = useState(300);
  const [os, setOs] = useState("");

  const [pt, setPt] = useState<"vision"|"text"|"speech"|"video_summary">("vision");
  const [pd, setPd] = useState<any>(null);
  const [pe, setPe] = useState("");
  const [initPe, setInitPe] = useState("");
  const [ps, setPs] = useState("");
  const dr = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/api/config").then(r => r.json()).then(c => {
      setCfn(c.video_frames || 1); setInitCfn(c.video_frames || 1);
      setCto(c.timeout || 300); setInitCto(c.timeout || 300);
    });
    fetch("/api/prompts").then(r => r.json()).then(d => {
      setPd(d);
      const v = d.vision?.custom || d.vision?.default || "";
      setPe(v); setInitPe(v);
    });
  }, []);

  const svS = () => {
    fetch("/api/config", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({video_frames:cfn,timeout:cto})})
      .then(r => { if(r.ok){ setOs("设置已保存"); setInitCfn(cfn); setInitCto(cto); setTimeout(() => setOs(""), 1500); }
        else { setOs("保存失败"); setTimeout(() => setOs(""), 3000); }})
      .catch(() => { setOs("保存失败"); setTimeout(() => setOs(""), 3000); });
  };

  const svP = () => {
    const def = pd?.[pt]?.default || "";
    const v = pe === def ? "" : pe;
    fetch("/api/prompts", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type:pt, custom:v})})
      .then(r => { if(r.ok){ setPs("已保存"); setInitPe(pe); setTimeout(() => setPs(""), 2000); }
        else { setPs("保存失败"); setTimeout(() => setPs(""), 3000); }})
      .catch(() => { setPs("保存失败"); setTimeout(() => setPs(""), 3000); });
  };

  const reP = () => {
    const def = pd?.[pt]?.default || "";
    setPe(def);
    fetch("/api/prompts", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type:pt, custom:""})})
      .then(r => { if(r.ok){ setPs("已恢复默认"); setInitPe(def); setTimeout(() => setPs(""), 2000); }
        else { setPs("恢复失败"); setTimeout(() => setPs(""), 3000); }})
      .catch(() => { setPs("恢复失败"); setTimeout(() => setPs(""), 3000); });
  };

  const basicDirty = cfn !== initCfn || cto !== initCto;
  const promptDirty = pe !== initPe;

  useEffect(() => {
    const orig = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = orig; };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{backgroundColor: "rgba(0,0,0,0.2)"}} onClick={onClose}>
      <div className="w-full max-w-4xl max-h-[85vh] min-h-[520px] rounded-xl shadow-2xl flex flex-col overflow-hidden" style={{backgroundColor: S.c}} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3" style={{borderBottom: `1px solid ${S.h}`}}>
          <h2 className="text-sm font-medium" style={{fontFamily:"'Tiempos Headline',Garamond,serif",color:S.i}}>设置</h2>
          <button onClick={onClose} className="text-xs px-2 py-1 rounded hover:brightness-95" style={{color: S.ms, backgroundColor: S.s}}>✕</button>
        </div>

        <div className="flex gap-1 px-5 py-2" style={{borderBottom: `1px solid ${S.h}`}}>
          {[{k:"basic" as const,l:"基础配置"},{k:"models" as const,l:"模型管理"},{k:"prompts" as const,l:"AI 提示词"}].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)}
              className="text-xs px-3 py-1.5 rounded" style={{backgroundColor: tab===t.k ? S.r : "transparent", color: tab===t.k ? S.w : S.ms}}>{t.l}</button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "basic" && (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-[11px]" style={{color:S.ms}}>视频采样帧数</label>
                  <input type="number" min={1} max={20} value={cfn} onChange={e => setCfn(parseInt(e.target.value)||1)}
                    className="w-full text-xs px-2 py-1.5 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
                <div><label className="text-[11px]" style={{color:S.ms}}>请求超时 (秒)</label>
                  <input type="number" min={30} max={600} value={cto} onChange={e => setCto(parseInt(e.target.value)||300)}
                    className="w-full text-xs px-2 py-1.5 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
              </div>
              <div className="flex gap-2 items-center">
                <button onClick={svS} className="text-xs px-3 py-1.5 rounded-md" style={{backgroundColor: basicDirty ? S.r : S.d, color: basicDirty ? S.w : S.ms, cursor: basicDirty ? "pointer" : "default"}}>保存</button>
                {os && <span className="text-[10px]" style={{color: os.includes("失败") ? "#c64545" : S.m}}>{os}</span>}
              </div>
            </div>
          )}

          {tab === "models" && (
            <div className="-mx-5 -my-4">
              <ModelManager onClose={() => {}} standalone={false} />
            </div>
          )}

          {tab === "prompts" && (
            <div className="flex flex-col gap-3">
              <div className="flex gap-1">
                {(["vision","text","speech","video_summary"] as const).map(t => (
                  <button key={t} onClick={() => { setPt(t); const v = pd?.[t]?.custom || pd?.[t]?.default || ""; setPe(v); setInitPe(v); }}
                    className="text-[10px] px-2 py-1 rounded" style={{backgroundColor: pt===t ? S.r : "transparent", color: pt===t ? S.w : S.ms}}>
                    {t==="vision"?"图片":t==="text"?"文档":t==="speech"?"语音":"视频"}
                  </button>
                ))}
              </div>
              {pd?.[pt]?.presets && pd[pt].presets.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {pd[pt].presets.map((p: any) => (
                    <button key={p.name} onClick={() => { setPe(p.content); dr.current?.focus(); }}
                      className="text-[10px] px-2 py-0.5 rounded border" style={{borderColor:S.h, color:S.m, backgroundColor:S.c}}>{p.name}</button>
                  ))}
                  <button onClick={() => { setPe(pd[pt]?.default||""); dr.current?.focus(); }}
                    className="text-[10px] px-2 py-0.5 rounded border" style={{borderColor:S.h, color:S.ms, backgroundColor:S.c}}>默认</button>
                </div>
              )}
              <textarea ref={dr} value={pe} onChange={e => setPe(e.target.value)} rows={6}
                className="w-full text-[10px] p-2 rounded-md resize-y outline-none"
                style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c,fontFamily:"monospace"}} placeholder="自定义提示词..."/>
              {pd?.[pt]?.system_format && (
                <div className="text-[9px] p-2 rounded-md leading-relaxed" style={{color:S.ms,backgroundColor:S.s,fontFamily:"monospace"}}>
                  <span className="text-[10px] font-medium" style={{color:S.i}}>输出格式（系统固定）</span><br/>{pd[pt].system_format}
                </div>
              )}
              <div className="flex gap-2 items-center">
                <button onClick={svP} className="text-xs px-3 py-1.5 rounded-md"
                  style={{backgroundColor: promptDirty ? S.r : S.d, color: promptDirty ? S.w : S.ms, cursor: promptDirty ? "pointer" : "default"}}>保存自定义</button>
                <button onClick={reP} className="text-xs px-3 py-1.5 rounded-md"
                  style={{backgroundColor: S.s, color: S.m, cursor:"pointer"}}>恢复默认</button>
                {ps && <span className="text-[10px]" style={{color: ps.includes("失败") ? "#c64545" : S.m}}>{ps}</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
