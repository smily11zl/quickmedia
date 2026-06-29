import { useState, useEffect, useRef } from "react";
import ModelManager from "./ModelManager";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface Props { initialTab?: string; onModelSave?: () => void;
  onClose: () => void;
  initialModelTab?: string;
}

export default function SettingsModal({ onClose, initialTab, onModelSave, initialModelTab }: Props) {
  const [tab, setTab] = useState<"basic" | "models" | "prompts" | "folders">((initialTab as any)||"basic");
  const [cfn, setCfn] = useState(1);
  const [cto, setCto] = useState(300);
  const [initCfn, setInitCfn] = useState(1);
  const [initCto, setInitCto] = useState(300);
  const [os, setOs] = useState("");

  const [pt, setPt] = useState<"vision"|"text"|"speech"|"video_summary"|"video_vision"|"search_ai"|"aggregation_full"|"aggregation_full_append"|"aggregation_append"|"aggregation_analyze_append">("vision");
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
      .then(r => { if(r.ok){ setPs("已保存"); setInitPe(pe); setTimeout(() => setPs(""), 2000);
        // Update local cache so tab switch shows new value
        setPd((prev: any) => prev ? {...prev, [pt]: {...prev[pt], custom: v}} : prev);
      }})
      .catch(() => { setPs("保存失败"); setTimeout(() => setPs(""), 3000); });
  };

  const reP = () => {
    const def = pd?.[pt]?.default || "";
    setPe(def);
    fetch("/api/prompts", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type:pt, custom:""})})
      .then(r => { if(r.ok){ setPs("已恢复默认"); setInitPe(def); setTimeout(() => setPs(""), 2000);
        setPd((prev: any) => prev ? {...prev, [pt]: {...prev[pt], custom: ""}} : prev);
      }})
      .catch(() => { setPs("恢复失败"); setTimeout(() => setPs(""), 3000); });
  };

  
  const [ftp,setFtp]=useState<{name:string;path:string;recursive:boolean;max_depth:number;enabled:boolean}[]>([]);
  const [fSaving,setFSaving]=useState(false);
  const [fMsg,setFMsg]=useState("");
  const [tabDots,setTabDots]=useState<Record<string,boolean>>({});
  useEffect(()=>{if(tab==="folders")fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>setFtp(d.paths||[]));fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>{setTabDots(prev=>({...prev,folders:!d.paths||d.paths.length===0}));if(onModelSave)onModelSave();});fetch("/api/task-models").then(r=>r.json()).then(d=>{const has=!!(d&&Object.values(d).every((x:any)=>x.model));setTabDots(prev=>({...prev,models:!has}));});},[tab]);
  const addPath=()=>setFtp([...ftp,{path:"",recursive:true,max_depth:3,enabled:true,name:""}]);
  const updPath=(i:number,f:any)=>setFtp(ftp.map((x,j)=>j===i?{...x,...f}:x));
  const delPath=(i:number)=>setFtp(ftp.filter((_,j)=>j!==i));
  const savePaths=()=>{setFSaving(true);fetch("/api/config/watch-paths",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({paths:ftp})}).then(r=>{setFSaving(false);setFMsg(r.ok?"已保存":"保存失败");fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>{setTabDots(prev=>({...prev,folders:!d.paths||d.paths.length===0}));if(onModelSave)onModelSave();});setTimeout(()=>setFMsg(""),2000);}).catch(()=>{setFSaving(false);setFMsg("保存失败");setTimeout(()=>setFMsg(""),3000);});};
  const pickFolder=async(i:number)=>{try{const r=await fetch("/api/folder-picker",{method:"POST"});const d=await r.json();if(d.path)updPath(i,{path:d.path});}catch(e){}}
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
          {[{k:"basic" as const,l:"基础配置",el:null},{k:"models" as const,l:"模型管理",el:tabDots.models?<span className="inline-block w-1.5 h-1.5 rounded-full ml-1" style={{backgroundColor:"#c64545"}}></span>:null},{k:"prompts" as const,l:"AI 提示词",el:null},{k:"folders" as const,l:"文件夹",el:tabDots.folders?<span className="inline-block w-1.5 h-1.5 rounded-full ml-1" style={{backgroundColor:"#c64545"}}></span>:null}].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)}
              className="text-xs px-3 py-1.5 rounded" style={{backgroundColor: tab===t.k ? S.r : "transparent", color: tab===t.k ? S.w : S.ms}}>{t.l}{t.el}</button>
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
              <ModelManager onClose={() => {}} standalone={false} initialTab={initialModelTab} onModelsSaved={()=>{fetch("/api/task-models").then(r=>r.json()).then(d=>{const has=!!(d&&Object.values(d).every((x:any)=>x.model));setTabDots(prev=>({...prev,models:!has}));}).then(()=>{if(onModelSave)onModelSave();});}} />
            </div>
          )}

          {tab === "folders" && (<div className="flex flex-col gap-3"><button onClick={addPath} className="text-xs px-3 py-1 rounded-md w-fit" style={{backgroundColor:S.d,color:S.b}}>+ 添加文件夹</button>{ftp.map((p,i)=>(<div key={i} className="p-3 rounded-lg" style={{border:`1px solid ${S.h}`}}><div className="flex gap-2 items-center mb-2"><input type="text" placeholder="名称" value={p.name||""} onChange={e=>updPath(i,{name:e.target.value})} className="text-xs px-2 py-1 rounded-md outline-none flex-1" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={()=>delPath(i)} className="text-xs px-2 py-1 rounded" style={{color:"#c64545"}}>✕</button></div><div className="flex gap-2 items-center"><input type="text" placeholder="路径" value={p.path} onChange={e=>updPath(i,{path:e.target.value})} className="flex-1 text-xs px-2 py-1 rounded-md outline-none" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={()=>pickFolder(i)} className="text-xs px-2 py-1 rounded-md" style={{backgroundColor:S.s,color:S.m}}>📁</button></div><div className="flex gap-3 mt-2 items-center"><label className="flex items-center gap-1 text-[10px]" style={{color:S.ms}}><input type="checkbox" checked={p.recursive} onChange={e=>updPath(i,{recursive:e.target.checked})} className="accent-[#cc785c]"/>递归</label><label className="text-[10px]" style={{color:S.ms}}>深度 <input type="number" min={1} max={10} value={p.max_depth||3} onChange={e=>updPath(i,{max_depth:parseInt(e.target.value)||3})} className="w-12 text-[10px] px-1 py-0.5 rounded outline-none ml-1" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></label><label className="flex items-center gap-1 text-[10px]" style={{color:S.ms}}><input type="checkbox" checked={p.enabled!==false} onChange={e=>updPath(i,{enabled:e.target.checked})} className="accent-[#cc785c]"/>启用</label></div></div>))}<div className="flex gap-2 items-center"><button onClick={savePaths} className="text-xs px-3 py-1 rounded-md w-fit" style={{backgroundColor: S.r, color: S.w}}>{fSaving?"保存中...":"保存"}</button>{fMsg&&<span className="text-[10px]" style={{color:fMsg.includes("失败")?"#c64545":S.m}}>{fMsg}</span>}</div></div>)}
          {tab === "prompts" && (
            <div className="flex flex-col gap-3">
              {/* 三组切换 */}
              <div className="flex gap-1">
                {(["分析","聚合","搜索"] as const).map(g => (
                  <button key={g} onClick={() => {
                    const groupMap: Record<string, string> = {"分析":"vision","聚合":"aggregation_full","搜索":"search_ai"};
                    const defaultType = groupMap[g];
                    setPt(defaultType as any);
                    const v = pd?.[defaultType]?.custom || pd?.[defaultType]?.default || "";
                    setPe(v); setInitPe(v);
                  }}
                    className="text-[10px] px-3 py-1 rounded-t" style={{
                      backgroundColor: (pt.startsWith("aggregation")&&g==="聚合")||(pt==="search_ai"&&g==="搜索")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g==="分析") ? S.d : "transparent",
                      color: (pt.startsWith("aggregation")&&g==="聚合")||(pt==="search_ai"&&g==="搜索")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g==="分析") ? S.i : S.ms,
                      borderBottom: (pt.startsWith("aggregation")&&g==="聚合")||(pt==="search_ai"&&g==="搜索")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g==="分析") ? `2px solid ${S.r}` : "2px solid transparent",
                    }}>
                    {g}
                  </button>
                ))}
              </div>
              {/* 子类型按钮 */}
              <div className="flex gap-1 flex-wrap">
                {(["vision","text","speech","video_vision","video_summary"].includes(pt) ? (
                  ["vision","text","speech","video_vision","video_summary"] as const
                ) : pt.startsWith("aggregation") ? (
                  ["aggregation_full","aggregation_full_append","aggregation_append","aggregation_analyze_append"] as const
                ) : (
                  ["search_ai"] as const
                )).map(t => (
                  <button key={t} onClick={() => { setPt(t as any); const v = pd?.[t]?.custom || pd?.[t]?.default || ""; setPe(v); setInitPe(v); }}
                    className="text-[10px] px-2 py-1 rounded" style={{backgroundColor: pt===t ? S.r : "transparent", color: pt===t ? S.w : S.ms}}>
                    {t==="vision"?"图片":t==="text"?"文档":t==="speech"?"语音":t==="video_summary"?"视频综合":t==="video_vision"?"视频视觉"
                    :t==="aggregation_full"?"全量聚合":t==="aggregation_full_append"?"全量追加":t==="aggregation_append"?"追加分析":t==="aggregation_analyze_append"?"节点追加"
                    :"搜索"}
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
              {pt.startsWith("aggregation") || pt === "search_ai" ? (
                <div className="text-[9px]" style={{color: S.ms}}>
                  可用变量：{pt==="aggregation_full"?"{assets} 素材列表"
                  :pt==="aggregation_full_append"?"{assets} 素材列表, {nodes} 已有节点"
                  :pt==="aggregation_append"?"{assets} 素材列表, {nodes} 已有节点"
                  :pt==="aggregation_analyze_append"?"{node_name} 节点名, {node_description} 节点描述, {existing_assets} 已有素材摘要, {candidates} 候选素材"
                  :pt==="search_ai"?"{assets} 素材列表, {query} 搜索查询"
                  :""}
                </div>
              ) : null}
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
