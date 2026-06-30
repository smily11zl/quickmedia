import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
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
      .then(r => { if(r.ok){ setOs(translate("settings.saved")); setInitCfn(cfn); setInitCto(cto); setTimeout(() => setOs(""), 1500); }
        else { setOs(translate("settings.save_failed")); setTimeout(() => setOs(""), 3000); }})
      .catch(() => { setOs(translate("settings.save_failed")); setTimeout(() => setOs(""), 3000); });
  };

  const svP = () => {
    const def = pd?.[pt]?.default || "";
    const v = pe === def ? "" : pe;
    fetch("/api/prompts", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type:pt, custom:v})})
      .then(r => { if(r.ok){ setPs(translate("settings.prompt_saved")); setInitPe(pe); setTimeout(() => setPs(""), 2000);
        // Update local cache so tab switch shows new value
        setPd((prev: any) => prev ? {...prev, [pt]: {...prev[pt], custom: v}} : prev);
      }})
      .catch(() => { setPs(translate("settings.save_failed")); setTimeout(() => setPs(""), 3000); });
  };

  const reP = () => {
    const def = pd?.[pt]?.default || "";
    setPe(def);
    fetch("/api/prompts", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({type:pt, custom:""})})
      .then(r => { if(r.ok){ setPs(translate("settings.prompt_reset")); setInitPe(def); setTimeout(() => setPs(""), 2000);
        setPd((prev: any) => prev ? {...prev, [pt]: {...prev[pt], custom: ""}} : prev);
      }})
      .catch(() => { setPs(translate("settings.restore_failed")); setTimeout(() => setPs(""), 3000); });
  };

  
  const [ftp,setFtp]=useState<{name:string;path:string;recursive:boolean;max_depth:number;enabled:boolean}[]>([]);
  const [fSaving,setFSaving]=useState(false);
  const { t: translate, i18n } = useTranslation();
  const [fMsg,setFMsg]=useState("");
  const [tabDots,setTabDots]=useState<Record<string,boolean>>({});
  useEffect(()=>{if(tab==="folders")fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>setFtp(d.paths||[]));fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>{setTabDots(prev=>({...prev,folders:!d.paths||d.paths.length===0}));if(onModelSave)onModelSave();});fetch("/api/task-models").then(r=>r.json()).then(d=>{const has=!!(d&&Object.values(d).every((x:any)=>x.model));setTabDots(prev=>({...prev,models:!has}));});},[tab]);
  const addPath=()=>setFtp([...ftp,{path:"",recursive:true,max_depth:3,enabled:true,name:""}]);
  const updPath=(i:number,f:any)=>setFtp(ftp.map((x,j)=>j===i?{...x,...f}:x));
  const delPath=(i:number)=>setFtp(ftp.filter((_,j)=>j!==i));
  const savePaths=()=>{setFSaving(true);fetch("/api/config/watch-paths",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({paths:ftp})}).then(r=>{setFSaving(false);setFMsg(r.ok?translate("settings.prompt_saved"):translate("settings.save_failed"));fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>{setTabDots(prev=>({...prev,folders:!d.paths||d.paths.length===0}));if(onModelSave)onModelSave();});setTimeout(()=>setFMsg(""),2000);}).catch(()=>{setFSaving(false);setFMsg(translate("settings.save_failed"));setTimeout(()=>setFMsg(""),3000);});};
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
          <h2 className="text-sm font-medium" style={{fontFamily:"'Tiempos Headline',Garamond,serif",color:S.i}}>{translate("settings.title")}</h2>
          <button onClick={onClose} className="text-xs px-2 py-1 rounded hover:brightness-95" style={{color: S.ms, backgroundColor: S.s}}>✕</button>
        </div>

        <div className="flex gap-1 px-5 py-2" style={{borderBottom: `1px solid ${S.h}`}}>
          {[{k:"basic" as const,l:translate("settings.tab_basic"),el:null},{k:"models" as const,l:translate("settings.tab_models"),el:tabDots.models?<span className="inline-block w-1.5 h-1.5 rounded-full ml-1" style={{backgroundColor:"#c64545"}}></span>:null},{k:"prompts" as const,l:translate("settings.tab_prompts"),el:null},{k:"folders" as const,l:translate("settings.tab_folders"),el:tabDots.folders?<span className="inline-block w-1.5 h-1.5 rounded-full ml-1" style={{backgroundColor:"#c64545"}}></span>:null}].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)}
              className="text-xs px-3 py-1.5 rounded" style={{backgroundColor: tab===t.k ? S.r : "transparent", color: tab===t.k ? S.w : S.ms}}>{t.l}{t.el}</button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {tab === "basic" && (
            <div className="flex flex-col gap-3">
              <div><label className="text-[11px]" style={{color:S.ms}}>{translate("settings.language")}</label>
                <select value={i18n.language} onChange={e=>{localStorage.setItem("language",e.target.value);document.cookie=`qm_lang=${e.target.value};path=/;max-age=31536000`;i18n.changeLanguage(e.target.value);window.location.reload();}} className="w-full text-xs px-2 py-1.5 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}>
                  <option value="zh">{translate("settings.language_zh")}</option>
                  <option value="en">{translate("settings.language_en")}</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="text-[11px]" style={{color:S.ms}}>{translate("settings.video_frames")}</label>
                  <input type="number" min={1} max={20} value={cfn} onChange={e => setCfn(parseInt(e.target.value)||1)}
                    className="w-full text-xs px-2 py-1.5 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
                <div><label className="text-[11px]" style={{color:S.ms}}>{translate("settings.timeout")}</label>
                  <input type="number" min={30} max={600} value={cto} onChange={e => setCto(parseInt(e.target.value)||300)}
                    className="w-full text-xs px-2 py-1.5 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
              </div>
              <div className="flex gap-2 items-center">
                <button onClick={svS} className="text-xs px-3 py-1.5 rounded-md" style={{backgroundColor: basicDirty ? S.r : S.d, color: basicDirty ? S.w : S.ms, cursor: basicDirty ? "pointer" : "default"}}>{translate("common.save")}</button>
                {os && <span className="text-[10px]" style={{color: os.includes("失败") ? "#c64545" : S.m}}>{os}</span>}
              </div>
            </div>
          )}

          {tab === "models" && (
            <div className="-mx-5 -my-4">
              <ModelManager onClose={() => {}} standalone={false} initialTab={initialModelTab} onModelsSaved={()=>{fetch("/api/task-models").then(r=>r.json()).then(d=>{const has=!!(d&&Object.values(d).every((x:any)=>x.model));setTabDots(prev=>({...prev,models:!has}));}).then(()=>{if(onModelSave)onModelSave();});}} />
            </div>
          )}

          {tab === "folders" && (<div className="flex flex-col gap-3"><button onClick={addPath} className="text-xs px-3 py-1 rounded-md w-fit" style={{backgroundColor:S.d,color:S.b}}>{translate("settings.add_folder")}</button>{ftp.map((p,i)=>(<div key={i} className="p-3 rounded-lg" style={{border:`1px solid ${S.h}`}}><div className="flex gap-2 items-center mb-2"><input type="text" placeholder={translate("settings.folder_name")} value={p.name||""} onChange={e=>updPath(i,{name:e.target.value})} className="text-xs px-2 py-1 rounded-md outline-none flex-1" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={()=>delPath(i)} className="text-xs px-2 py-1 rounded" style={{color:"#c64545"}}>✕</button></div><div className="flex gap-2 items-center"><input type="text" placeholder={translate("settings.folder_path")} value={p.path} onChange={e=>updPath(i,{path:e.target.value})} className="flex-1 text-xs px-2 py-1 rounded-md outline-none" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={()=>pickFolder(i)} className="text-xs px-2 py-1 rounded-md" style={{backgroundColor:S.s,color:S.m}}>📁</button></div><div className="flex gap-3 mt-2 items-center"><label className="flex items-center gap-1 text-[10px]" style={{color:S.ms}}><input type="checkbox" checked={p.recursive} onChange={e=>updPath(i,{recursive:e.target.checked})} className="accent-[#cc785c]"/>{translate("settings.recursive")}</label><label className="text-[10px]" style={{color:S.ms}}>{translate("settings.depth")} <input type="number" min={1} max={10} value={p.max_depth||3} onChange={e=>updPath(i,{max_depth:parseInt(e.target.value)||3})} className="w-12 text-[10px] px-1 py-0.5 rounded outline-none ml-1" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></label><label className="flex items-center gap-1 text-[10px]" style={{color:S.ms}}><input type="checkbox" checked={p.enabled!==false} onChange={e=>updPath(i,{enabled:e.target.checked})} className="accent-[#cc785c]"/>{translate("settings.enabled")}</label></div></div>))}<div className="flex gap-2 items-center"><button onClick={savePaths} className="text-xs px-3 py-1 rounded-md w-fit" style={{backgroundColor: S.r, color: S.w}}>{fSaving?translate("common.processing"):translate("common.save")}</button>{fMsg&&<span className="text-[10px]" style={{color:fMsg.includes("失败")?"#c64545":S.m}}>{fMsg}</span>}</div></div>)}
          {tab === "prompts" && (
            <div className="flex flex-col gap-3">
              {/* 三组切换 */}
              <div className="flex gap-1">
                {([{type:"vision",l:translate("prompt.group_analysis")},{type:"aggregation_full",l:translate("prompt.group_aggregation")},{type:"search_ai",l:translate("prompt.group_search")}]).map(g => (
                  <button key={g.type} onClick={() => {
                    const groupMap: Record<string, string> = {vision:"vision",aggregation_full:"aggregation_full",search_ai:"search_ai"};
                    const defaultType = groupMap[g.type];
                    setPt(defaultType as any);
                    const v = pd?.[defaultType]?.custom || pd?.[defaultType]?.default || "";
                    setPe(v); setInitPe(v);
                  }}
                    className="text-[10px] px-3 py-1 rounded-t" style={{
                      backgroundColor: (pt?.startsWith("aggregation")&&g.type==="aggregation_full")||(pt==="search_ai"&&g.type==="search_ai")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g.type==="vision") ? S.d : "transparent",
                      color: (pt?.startsWith("aggregation")&&g.type==="aggregation_full")||(pt==="search_ai"&&g.type==="search_ai")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g.type==="vision") ? S.i : S.ms,
                      borderBottom: (pt?.startsWith("aggregation")&&g.type==="aggregation_full")||(pt==="search_ai"&&g.type==="search_ai")||(["vision","text","speech","video_vision","video_summary"].includes(pt)&&g.type==="vision") ? `2px solid ${S.r}` : "2px solid transparent",
                    }}>
                    {g.l}
                  </button>
                ))}
              </div>
              {/* 子类型按钮 */}
              <div className="flex gap-1 flex-wrap">
                {(["vision","text","speech","video_vision","video_summary"].includes(pt) ? (
                  ["vision","text","speech","video_vision","video_summary"] as const
                ) : pt?.startsWith("aggregation") ? (
                  ["aggregation_full","aggregation_full_append","aggregation_append","aggregation_analyze_append"] as const
                ) : (
                  ["search_ai"] as const
                )).map(t => (
                  <button key={t} onClick={() => { setPt(t as any); const v = pd?.[t]?.custom || pd?.[t]?.default || ""; setPe(v); setInitPe(v); }}
                    className="text-[10px] px-2 py-1 rounded" style={{backgroundColor: pt===t ? S.r : "transparent", color: pt===t ? S.w : S.ms}}>
                    {t==="vision"?translate("prompt.vision"):t==="text"?translate("prompt.text"):t==="speech"?translate("prompt.speech"):t==="video_summary"?translate("prompt.video_summary"):t==="video_vision"?translate("prompt.video_vision")
                    :t==="aggregation_full"?translate("prompt.aggregation_full"):t==="aggregation_full_append"?translate("prompt.aggregation_full_append"):t==="aggregation_append"?translate("prompt.aggregation_append"):t==="aggregation_analyze_append"?translate("prompt.aggregation_analyze_append")
                    :translate("prompt.search_ai")}
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
                    className="text-[10px] px-2 py-0.5 rounded border" style={{borderColor:S.h, color:S.ms, backgroundColor:S.c}}>{translate("common.default")}</button>
                </div>
              )}
              <textarea ref={dr} value={pe} onChange={e => setPe(e.target.value)} rows={6}
                className="w-full text-[10px] p-2 rounded-md resize-y outline-none"
                style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c,fontFamily:"monospace"}} placeholder={translate("settings.prompt_placeholder")}/>
              {pt?.startsWith("aggregation") || pt === "search_ai" ? (
                <div className="text-[9px]" style={{color: S.ms}}>
                  {translate("settings.variables")}:{pt==="aggregation_full"?translate("settings.var_assets_list")
                  :pt==="aggregation_full_append"?translate("settings.var_assets_nodes")
                  :pt==="aggregation_append"?translate("settings.var_assets_nodes")
                  :pt==="aggregation_analyze_append"?translate("settings.var_analyze_append")
                  :pt==="search_ai"?translate("settings.var_search_ai")
                  :""}
                </div>
              ) : null}
              {pd?.[pt]?.system_format && (
                <div className="text-[9px] p-2 rounded-md leading-relaxed" style={{color:S.ms,backgroundColor:S.s,fontFamily:"monospace"}}>
                  <span className="text-[10px] font-medium" style={{color:S.i}}>{translate("settings.output_format")}</span><br/>{pd[pt].system_format}
                </div>
              )}
              <div className="flex gap-2 items-center">
                <button onClick={svP} className="text-xs px-3 py-1.5 rounded-md"
                  style={{backgroundColor: promptDirty ? S.r : S.d, color: promptDirty ? S.w : S.ms, cursor: promptDirty ? "pointer" : "default"}}>{translate("settings.save_custom")}</button>
                <button onClick={reP} className="text-xs px-3 py-1.5 rounded-md"
                  style={{backgroundColor: S.s, color: S.m, cursor:"pointer"}}>{translate("settings.restore_default")}</button>
                {ps && <span className="text-[10px]" style={{color: ps.includes("失败") ? "#c64545" : S.m}}>{ps}</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
