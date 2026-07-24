import { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import i18n from "./i18n";
import ModelManager from "./ModelManager";
import SettingsModal from "./SettingsModal";
import SimilarPanel from "./SimilarPanel";
import NodePanel from "./NodePanel";
import GraphView from "./GraphView";
import Toast from "./Toast";
import ConfirmModal from "./ConfirmModal";

interface Asset {
  id: number; filename: string; asset_type: string; size: number;
  width?: number; height?: number; duration?: number; path: string;
  description?: string; visual_description?: string;
  ai_description?: string; ai_summary?: string;
  ocr_text?: string; transcript?: string; video_summary?: string;
  ai_status?: string;
  score?: number; view_count?: number; open_count?: number;
  scanned_at?: string;
  doc_preview?: string;
  _stars?: number;
  thumbnail_status: string; modified_at?: string;
  tags: { id: number; name: string; source: string }[];
  _distance?: number;
}
interface TagInfo { id: number; name: string; count: number; }

const f=(b:number)=>{for(const u of["B","KB","MB","GB"]){if(b<1024)return `${b}${u}`;b=Math.floor(b/1024);}return `${b}TB`;};
const S={c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};
const docI=(a:Asset)=>{const x=a.filename.split(".").pop()?.toLowerCase()||"";const m:Record<string,string>={pdf:"📕",md:"📝",txt:"📝",csv:"📊",json:"📋",xlsx:"📊",docx:"📄"};return m[x]||"📄";};
const aiT=(s?:string)=>{if(!s||s==="-")return null;const cl:{[k:string]:string}={done:"#5db872",processing:"#e8a55a",failed:"#c64545",pending:"#6c6a64",cancelled:"#8b75a6"};const m:{[k:string]:string}={done:i18n.t("asset.detail_ai_done"),processing:i18n.t("asset.detail_ai_processing"),pending:i18n.t("asset.detail_ai_pending"),failed:i18n.t("asset.detail_ai_failed"),cancelled:i18n.t("asset.detail_ai_cancelled")};return <span className="text-[10px]" style={{color:cl[s]||S.ms}}>{m[s]||s}</span>;};

const DocPreview = ({id}:{id:number}) => {
  const [txt,setTxt]=useState("");
  useEffect(()=>{fetch(`/api/assets/${id}/preview`).then(r=>r.json()).then(d=>setTxt(d.text||""));},[id]);
  if(!txt) return null;
  return <p className="text-[9px] mt-1 text-center leading-relaxed" style={{color:S.m, maxWidth:"100%", overflow:"hidden", display:"-webkit-box", WebkitLineClamp:3, WebkitBoxOrient:"vertical"}}>{txt.slice(0,120)}</p>;
};

function App() {
  const [as,sa]=useState<Asset[]>([]);
  const [fmts,sfmts]=useState<string[]>([]);
  const [searchResults,sr]=useState<Asset[]>([]);
  const [didSearch,sds]=useState(false);
  const [didSearchMode,sdsMode]=useState<string>("");
  const [tg,stg]=useState<TagInfo[]>([]);
  const [tf,stf]=useState<string|null>(null);
  const [gf,sgf]=useState<number|null>(null);
  const [q,sq]=useState("");
  const [smode,ssmode]=useState<"ai"|"keyword"|"semantic"|"combined">("combined");
  const [aiSearchReady, setAiSearchReady] = useState(false);
  const [slc,sslc]=useState(false);
  const [cp,scp]=useState<number|null>(null);
  const [sel,sl]=useState<Asset|null>(null);
  const [ed,se]=useState(false);
  const [dv,sd]=useState("");
  const [nt,sn]=useState("");
  const [so,sso]=useState(false);
  const [settingsTab, setSettingsTab] = useState<string>("basic");
  const [mm,smm]=useState(false);
  const [vw,sv]=useState<"graph"|"grid"|"list">("grid");
  const [sb,ssb]=useState<"name"|"size"|"date"|"score"|"hot"|"recent">("hot");
  const [ms,sm]=useState<Set<number>>(new Set());
  const [ff,sf]=useState<Set<string>>(new Set());
  const [af,saf]=useState<Set<string>>(new Set());
  const [tgf,stgf]=useState<Set<number>>(new Set());
  const [df,sdf]=useState({from:"",to:""});
  const [mf,smf]=useState({from:"",to:""});
  const [fop,sfop]=useState(false);
  const [aop,saop]=useState(false);
  const [top,stop]=useState(false);
  const [missingConfig,setMC]=useState(false);
  const [qStat,setQStat]=useState<{pending:number;processing_name:string|null}>({pending:0,processing_name:null});
  const [activeTab, setActiveTab] = useState<"search" | "nodes">("search");
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [selectedNodeName, setSelectedNodeName] = useState<string>("");
  const [scm, sscm] = useState(false);
  const { t } = useTranslation();
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [graphData, setGraphData] = useState({nodes:[] as any[],edges:[] as any[],unassigned:[] as any[]});
  const [graphKey, setGraphKey] = useState(0);
  const [nodeRefreshKey, setNodeRefreshKey] = useState(0);
  const graphInitRef = useRef(false);
  const scanningRef = useRef(false);
  const dr=useRef<HTMLTextAreaElement>(null);
  const [counts, setCounts] = useState({image: 0, video: 0, audio: 0, document: 0});
  const [toast, setToast] = useState<{ message: string; type?: "info" | "error" } | null>(null);
  const [confirmDeleteAsset, setConfirmDeleteAsset] = useState<Asset | null>(null);
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState<any>(null);
  const [queueClearConfirm, setQueueClearConfirm] = useState(false);

  const ckCfg=()=>{Promise.all([fetch("/api/config/watch-paths").then(r=>r.json()),fetch("/api/task-models").then(r=>r.json())]).then(([wp,tm])=>{const hasWp=wp.paths&&wp.paths.length>0;const hasTm=!!(tm&&Object.values(tm).every((x:any)=>x.model));setMC(!hasWp||!hasTm);const sa=tm?.search_ai;const ready=!!(sa?.provider && sa?.model);setAiSearchReady(ready);});};
  useEffect(()=>{fetch("/api/formats").then(r=>r.json()).then(sfmts);ckCfg();setInterval(ckCfg,30000);},[]);
  // One-time: default to AI search when model is configured on first load
  useEffect(()=>{fetch("/api/task-models").then(r=>r.json()).then(tm=>{if(tm?.search_ai?.provider && tm?.search_ai?.model&&!q){ssmode("ai");}});},[]);
  useEffect(()=>{fetch("/api/tags").then(r=>r.json()).then(stg);},[]);
  useEffect(()=>{fetch("/api/queue/status").then(r=>r.json()).then(setQStat);const i=setInterval(()=>fetch("/api/queue/status").then(r=>r.json()).then(setQStat),5000);return ()=>clearInterval(i);},[]);

  const doSearch=()=>{
    if(!q.trim()){sq("");sr([]);sds(false);sdsMode("");fa();return;}
    if(smode==="ai"){sslc(true);setSelectedNodeId(null);setSelectedNodeName("");fetch(`/api/search?q=${encodeURIComponent(q)}&mode=ai`).then(r=>r.json()).then(d=>{const items=d.items||[];sa(items);if(d.counts)setCounts(d.counts);sr(items);sds(true);sdsMode("ai");}).catch(()=>setToast({message:"AI \u641c\u7d22\u5931\u8d25",type:"error"})).finally(()=>sslc(false));return;}
    sslc(true);
    setSelectedNodeId(null); setSelectedNodeName("");
    fetch(`/api/search?q=${encodeURIComponent(q)}&mode=${smode}`).then(r=>r.json()).then(d=>{if(d.warning){setToast({message:d.warning,type:"info"});sslc(false);return;}const items = d.items||d||[]; sa(items); if(d.counts)setCounts(d.counts); if(smode!=="keyword"){sr(items);sds(true);sdsMode(smode);if(smode==="semantic"||smode==="combined")ssb("score");}}).catch(()=>{if((smode as string)==="ai")setToast({message:t("search.ai_failed"),type:"error"});}).finally(()=>sslc(false));
  };
  const fa=()=>{const p=new URLSearchParams();if(tf)p.set("type",tf);p.set("limit","200");if(ff.size>0)p.set("formats",[...ff].join(","));if(af.size>0)p.set("ai_status",[...af].join(","));if(tgf.size>0)p.set("tags",[...tgf].join(","));if(df.from)p.set("date_from",df.from);if(df.to)p.set("date_to",df.to);if(mf.from)p.set("mdate_from",mf.from);if(mf.to)p.set("mdate_to",mf.to);fetch(`/api/assets?${p}`).then(r=>r.json()).then(d=>{sa(d.items); if(d.counts)setCounts(d.counts);});};
  useEffect(()=>{if(didSearch||selectedNodeId)return;fa();},[tf,ff,af,df,mf,tgf]);useEffect(()=>{const u=async()=>{const r=await fetch("/api/assets?limit=500");const d=await r.json();const m:Record<number,any>={};d.items.forEach((a:any)=>m[a.id]=a);sa((p:any[])=>{let c=false;const n=p.map(a=>{const f=m[a.id];if(f&&a.ai_status!==f.ai_status){c=true;return{...a,ai_status:f.ai_status,analyzed_at:f.analyzed_at};}return a;});return c?n:p;});};const i=setInterval(u,3000);return ()=>clearInterval(i);},[]);

  // Poll selected asset if it's being processed
  useEffect(()=>{
    if(!sel) return;
    const i=setInterval(()=>{if(scanningRef.current)return;fetch(`/api/assets/${sel.id}`).then(r=>r.json()).then(a=>{sl(a);sd(a.description||"");se(false);});},5000);
    return ()=>clearInterval(i);
  },[sel?.id,sel?.ai_status]);

  // V12: Load assets when a node is selected
  useEffect(()=>{
    if (selectedNodeId) {
      fetch(`/api/nodes/${selectedNodeId}/assets`).then(r=>r.json()).then(d=>{
        sa(d.items); sr([]); sds(false); sdsMode(""); sq("");
        stf(null); sgf(null);
        if (d.counts) setCounts(d.counts);
      });
    }
  },[selectedNodeId]);

  useEffect(()=>{
    if(vw==="graph") fetch("/api/graph").then(r=>r.json()).then(d=>{
      setGraphData(d);
      if(!graphInitRef.current && d.nodes.length>0){
        setExpandedNodes(new Set(d.nodes.map((n:any)=>n.id)));
        graphInitRef.current = true;
      }
    });
  },[vw]);

  let fs=(q&&smode!=="keyword"&&didSearch)?searchResults:as;
  if(didSearch||selectedNodeId){
    if(tf)fs=fs.filter(a=>a.asset_type===tf);
    if(ff.size>0)fs=fs.filter(a=>{const x=a.filename.split(".").pop()?.toLowerCase()||"";return ff.has(x);});
    if(af.size>0)fs=fs.filter(a=>{const s=a.ai_status||(a.visual_description||a.ai_summary?"done":"pending");return af.has(s);});
    if(tgf.size>0)fs=fs.filter(a=>a.tags.some(t=>tgf.has(t.id)));
    if(df.from)fs=fs.filter(a=>(a.modified_at||"")>=df.from);
    if(df.to)fs=fs.filter(a=>(a.modified_at||"").slice(0,10)<=df.to);
    if(mf.from)fs=fs.filter(a=>(a.modified_at||"")>=mf.from);
    if(mf.to)fs=fs.filter(a=>(a.modified_at||"").slice(0,10)<=mf.to);
  }
  if(gf)fs=fs.filter(a=>a.tags.some(t=>t.id===gf));
  fs=[...fs].sort((a,b)=>{if(sb==="score")return(b.score||0)-(a.score||0);if(sb==="recent")return(b.scanned_at||"").localeCompare(a.scanned_at||"");if(sb==="hot")return((b.view_count||0)+(b.open_count||0)*3)-((a.view_count||0)+(a.open_count||0)*3)||(b.scanned_at||"").localeCompare(a.scanned_at||"");if(sb==="size")return b.size-a.size;if(sb==="date")return(b.modified_at||"").localeCompare(a.modified_at||"");return a.filename.localeCompare(b.filename);});

  const selA=(id:number)=>{fetch(`/api/assets/${id}?click=1`).then(r=>r.json()).then(a=>{sl(a);sd(a.description||"");se(false);});};
  const svD=()=>{if(!sel)return;fetch(`/api/assets/${sel.id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({description:dv})}).then(()=>{sl({...sel,description:dv});se(false);});};
  const adT=()=>{if(!sel||!nt.trim())return;fetch(`/api/assets/${sel.id}/tags/by-name`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:nt.trim()})}).then(r=>r.json()).then(t=>{sl({...sel,tags:[...sel.tags,{id:t.id,name:t.name,source:"manual"}]});sn("");fetch("/api/tags").then(r=>r.json()).then(stg);fa();});};
  const rmT=(tid:number)=>{if(!sel)return;fetch(`/api/assets/${sel.id}/tags/${tid}`,{method:"DELETE"}).then(()=>{sl({...sel,tags:sel.tags.filter(t=>t.id!==tid)});fetch("/api/tags").then(r=>r.json()).then(stg);});};
  const tgA=(id:number)=>{const n=new Set(ms);n.has(id)?n.delete(id):n.add(id);sm(n);};
  const cq=()=>{setQueueClearConfirm(true);};
  const bd=()=>{setBatchDeleteConfirm({title:t("batch.delete_selected"),message:t("batch.delete_confirm",{count:ms.size}),action:()=>{fetch("/api/assets/batch-delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({ids:[...ms]})}).then(r=>r.json()).then(d=>{if(d.ok){sm(new Set());sa([]);fa();}});}});};
  const bRe=()=>{fetch("/api/assets/batch-reanalyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({asset_ids:[...ms]})}).then(()=>{sm(new Set());});};
  const delA=(id:number)=>{fetch(`/api/assets/${id}`,{method:"DELETE"}).then(()=>{sl(null);fa();});};

  const types=[{k:null,l:t("asset.filter_all"),n:counts.image+counts.video+counts.audio+counts.document},{k:"image",l:t("asset.type_image"),n:counts.image},{k:"video",l:t("asset.type_video"),n:counts.video},{k:"audio",l:t("asset.type_audio"),n:counts.audio},{k:"document",l:t("asset.type_document"),n:counts.document}];
  const hl=(text:string):any=>{if(!q)return text;const i=text.toLowerCase().indexOf(q.toLowerCase());if(i<0)return text;return <>{text.slice(0,i)}<span style={{color:S.r,fontWeight:600}}>{text.slice(i,i+q.length)}</span>{text.slice(i+q.length)}</>;};

  return (
    <div className="flex h-screen" style={{backgroundColor:S.c}}>
      <aside className="w-64 flex flex-col gap-0.5 p-4 border-r h-full" style={{borderColor:S.h}}>
        <h1 style={{fontFamily:"'Tiempos Headline',Garamond,serif",fontSize:22,fontWeight:400,color:S.i}} className="mb-4">QuickMedia</h1>
        <div className="flex gap-0 mb-3">
          <button onClick={()=>setActiveTab("search")} className="flex-1 text-xs py-1.5 rounded-t-md font-medium" style={{fontFamily:"'Inter',sans-serif",backgroundColor:activeTab==="search"?S.d:"transparent",color:activeTab==="search"?S.i:S.ms,borderBottom:activeTab==="search"?`2px solid ${S.r}`:"2px solid transparent"}}>{t("search.tab_filter")}</button>
          <button onClick={()=>setActiveTab("nodes")} className="flex-1 text-xs py-1.5 rounded-t-md font-medium" style={{fontFamily:"'Inter',sans-serif",backgroundColor:activeTab==="nodes"?S.d:"transparent",color:activeTab==="nodes"?S.i:S.ms,borderBottom:activeTab==="nodes"?`2px solid ${S.r}`:"2px solid transparent"}}>{t("search.tab_nodes")}</button>
        </div>
        <div className="flex-1 overflow-y-auto flex flex-col gap-0.5">
{activeTab==="search" ? (
        <>
        <div className="flex flex-col gap-1 mb-3">
          <div className="relative w-full">
            <input type="text" placeholder={t("search.placeholder")} value={q} onChange={e=>sq(e.target.value)} onKeyDown={e=>e.key==="Enter"&&doSearch()} className="w-full px-3 py-1.5 text-sm rounded-md outline-none pr-6" style={{fontFamily:"'Inter',sans-serif",backgroundColor:S.c,border:`1px solid ${S.h}`,color:S.i}}/>
            {q&&<button onClick={()=>{sq("");sr([]);sds(false);sdsMode("");fa();}} className="absolute right-2 top-1/2 -translate-y-1/2 text-xs" style={{color:S.ms}}>✕</button>}
          </div>
          <div className="flex gap-1">
            <select value={smode} onChange={e=>{const v=e.target.value;if(v==="ai"&&!aiSearchReady){setToast({message:"AI \u641c\u7d22\u672a\u914d\u7f6e\u6a21\u578b\uff0c\u8bf7\u5728\u8bbe\u7f6e\u4e2d\u7ed1\u5b9a",type:"info"});setSettingsTab("models");sso(true);return;}ssmode(v as any);if(didSearch&&(didSearchMode==="semantic"||didSearchMode==="combined"))ssb("score");else if(v==="keyword"||v==="ai")ssb("hot");}} className="flex-1 text-[11px] px-1 py-1.5 rounded-md outline-none" style={{border:`1px solid ${S.h}`,color:S.m,backgroundColor:S.c}}>
              <option value="ai">AI {!aiSearchReady?'🔴':''}</option>
              <option value="combined">{t("search.mode_combined")}</option>
              <option value="semantic">{t("search.mode_semantic")}</option>
              <option value="keyword">{t("search.mode_keyword")}</option>
            </select>
            <button onClick={doSearch} className="text-[11px] px-3 py-1 rounded-md" style={{backgroundColor:S.r,color:S.w}}>{t("common.search")}</button>
          </div>
        </div>
        <div className="text-xs mb-1" style={{color:S.ms}}>{t("asset.filter_type")}</div>
        {types.map(t=>(<button key={t.l} onClick={()=>{stf(t.k);sgf(null);}} className="text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",backgroundColor:tf===t.k?S.d:"transparent",color:tf===t.k?S.i:S.m,fontWeight:tf===t.k?500:400}}>{t.l}<span className="float-right opacity-50">({t.n})</span></button>))}
        <div className="text-xs mb-1 mt-3" style={{color:S.ms}}>{t("asset.filter_created")}</div>
        <div className="flex gap-1 items-center">
          <input type="date" value={df.from} onChange={e=>{sdf({...df,from:e.target.value});}} className="flex-1 px-1 py-0.5 rounded border text-[11px]" style={{borderColor:S.h,color:S.i,backgroundColor:S.c}}/>
          <span className="text-[10px]" style={{color:S.ms}}>~</span>
          <input type="date" value={df.to} onChange={e=>{sdf({...df,to:e.target.value});}} className="flex-1 px-1 py-0.5 rounded border text-[11px]" style={{borderColor:S.h,color:S.i,backgroundColor:S.c}}/>
        </div>
        <div className="text-xs mb-1 mt-2" style={{color:S.ms}}>{t("asset.filter_modified")}</div>
        <div className="flex gap-1 items-center">
          <input type="date" value={mf.from} onChange={e=>{smf({...mf,from:e.target.value});}} className="flex-1 px-1 py-0.5 rounded border text-[11px]" style={{borderColor:S.h,color:S.i,backgroundColor:S.c}}/>
          <span className="text-[10px]" style={{color:S.ms}}>~</span>
          <input type="date" value={mf.to} onChange={e=>{smf({...mf,to:e.target.value});}} className="flex-1 px-1 py-0.5 rounded border text-[11px]" style={{borderColor:S.h,color:S.i,backgroundColor:S.c}}/>
        </div>
        <div className="text-xs mb-1 mt-2" style={{color:S.ms}}>{t("asset.filter_format")}</div>
        <div className="relative">
          <button onClick={()=>sfop(!fop)} className="w-full flex items-center justify-between px-2 py-1 rounded border text-xs" style={{borderColor:ff.size>0?S.r:S.h,color:ff.size>0?S.r:S.ms,backgroundColor:S.c}}>
            <span>{ff.size>0?`已选 ${ff.size} 项`:t("asset.filter_select")}</span>
            {ff.size>0&&<span onClick={e=>{e.stopPropagation();sf(new Set());}} className="ml-1 text-[10px]" style={{color:S.ms}}>✕</span>}
          </button>
          {fop&&<div className="fixed inset-0 z-[5]" onClick={()=>sfop(false)}/>}
          {fop&&<div className="absolute top-full left-0 right-0 mt-1 p-2 rounded border shadow-sm z-10 flex gap-1 flex-wrap" style={{borderColor:S.h,backgroundColor:S.c}}>
            {fmts.map(f=><button key={f} onClick={()=>{const n=new Set(ff);n.has(f)?n.delete(f):n.add(f);sf(n);}} className={"px-1.5 py-0.5 rounded text-[11px] "+(ff.has(f)?"font-medium":"")} style={{color:ff.has(f)?S.r:S.ms,backgroundColor:ff.has(f)?S.rb:"transparent"}}>{f.toUpperCase()}</button>)}
          </div>}
        </div>
        <div className="text-xs mb-1 mt-2" style={{color:S.ms}}>{t("asset.filter_ai")}</div>
        <div className="relative">
          <button onClick={()=>saop(!aop)} className="w-full flex items-center justify-between px-2 py-1 rounded border text-xs" style={{borderColor:af.size>0?S.r:S.h,color:af.size>0?S.r:S.ms,backgroundColor:S.c}}>
            <span>{af.size>0?`已选 ${af.size} 项`:t("asset.filter_select")}</span>
            {af.size>0&&<span onClick={e=>{e.stopPropagation();saf(new Set());}} className="ml-1 text-[10px]" style={{color:S.ms}}>✕</span>}
          </button>
          {aop&&<div className="fixed inset-0 z-[5]" onClick={()=>saop(false)}/>}
          {aop&&<div className="absolute top-full left-0 right-0 mt-1 p-2 rounded border shadow-sm z-10 flex gap-1 flex-wrap" style={{borderColor:S.h,backgroundColor:S.c}}>
            {[{k:"done",l:t("asset.detail_ai_done"),c:"#5db872"},{k:"processing",l:t("asset.detail_ai_processing"),c:"#e8a55a"},{k:"pending",l:t("asset.detail_ai_pending"),c:"#6c6a64"},{k:"failed",l:t("asset.detail_ai_failed"),c:"#c64545"},{k:"cancelled",l:t("asset.filter_cancelled"),c:"#8b75a6"}].map(s=><button key={s.k} onClick={()=>{const n=new Set(af);n.has(s.k)?n.delete(s.k):n.add(s.k);saf(n);}} className={"px-1.5 py-0.5 rounded text-[11px] "+(af.has(s.k)?"font-medium":"")} style={{color:s.c,fontWeight:af.has(s.k)?"bold":"normal",backgroundColor:af.has(s.k)?S.rb:"transparent"}}>{s.l}</button>)}
          </div>}
        </div>
        <div className="text-xs mb-1 mt-2" style={{color:S.ms}}>{t("asset.filter_tags")}</div>
        <div className="relative">
          <button onClick={()=>stop(!top)} className="w-full flex items-start justify-between px-2 py-1 rounded border text-xs min-h-[28px]" style={{borderColor:tgf.size>0?S.r:S.h,color:tgf.size>0?S.r:S.ms,backgroundColor:S.c}}>
            <span className="text-left leading-relaxed flex-1">{tgf.size>0?<>{tg.filter(t=>tgf.has(t.id)).map(t=>t.name).join("，")}<span className="ml-1" style={{color:S.ms}}>({tgf.size})</span></>:t("asset.filter_select")}</span>
            <span className="flex items-center gap-1 ml-1 flex-shrink-0">
              {tgf.size>0&&<span onClick={e=>{e.stopPropagation();stgf(new Set());}} className="text-[10px]" style={{color:S.ms}}>✕</span>}
            </span>
          </button>
          {top&&<div className="fixed inset-0 z-[5]" onClick={()=>stop(false)}/>}
          {top&&<div className="absolute top-full left-0 right-0 mt-1 p-2 rounded border shadow-sm z-10 max-h-64 overflow-y-auto" style={{borderColor:S.h,backgroundColor:S.c}}>
            <div className="flex justify-between items-center mb-1">
              <span className="text-[10px]" style={{color:S.ms}}>{tgf.size>0?t("filter.selected",{count: tgf.size}):t("filter.all_tags")}</span>
              {tgf.size>0&&<button onClick={()=>{stgf(new Set());}} className="text-[10px] px-1.5 py-0.5 rounded" style={{color:S.r,backgroundColor:S.rb}}>{t("filter.clear_all")}</button>}
            </div>
            <div className="flex gap-1 flex-wrap">
              {tg.filter(t=>t.count>0).sort((a,b)=>b.count-a.count).map(t=><button key={t.id} onClick={()=>{const n=new Set(tgf);n.has(t.id)?n.delete(t.id):n.add(t.id);stgf(n);}} className={"px-1.5 py-0.5 rounded text-[11px] "+(tgf.has(t.id)?"font-medium":"")} style={{color:tgf.has(t.id)?S.r:S.ms,backgroundColor:tgf.has(t.id)?S.rb:"transparent"}}>{t.name}</button>)}
            </div>
          </div>}
        </div>
        </>
        ) : (
          <NodePanel onSelectNode={(nid:number|null,name?:string)=>{setSelectedNodeId(nid);setSelectedNodeName(name||"");if(!nid){sds(false);fa();}}} selectedNodeId={selectedNodeId} onRefreshAssets={(nodeId:number)=>{fetch(`/api/nodes/${nodeId}/assets`).then(r=>r.json()).then(d=>{sa(d.items);if(d.counts)setCounts(d.counts);});}} refreshKey={nodeRefreshKey} onGraphRefresh={(newNodeId?:number)=>{fetch("/api/graph").then(r=>r.json()).then(d=>{setGraphData(d);if(newNodeId)setExpandedNodes((prev:Set<number>)=>new Set(prev).add(newNodeId));else setExpandedNodes(new Set(d.nodes.map((n:any)=>n.id)));});}} onGraphFullReload={()=>{fetch("/api/graph").then(r=>r.json()).then(d=>{setGraphData(d);setExpandedNodes(new Set(d.nodes.map((n:any)=>n.id)));setGraphKey(k=>k+1);});}} onSelectAsset={(aid:number)=>{selA(aid);}}  selectedAssetId={sel?.id} unassigned={graphData.unassigned} />
        )}
        </div>
        <div className="mt-auto pt-4 flex flex-col gap-1 relative" style={{borderTop:`1px solid ${S.h}`}}>
          <button onClick={()=>sscm(!scm)} className="w-full text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",color:S.m}}>🔍 {t("common.scan")}</button>
          {scm&&<div className="fixed inset-0 z-[5]" onClick={()=>sscm(false)}/>}
          {scm&&<div className="absolute bottom-full left-0 right-0 mb-1 p-2 rounded border shadow-sm z-10 flex flex-col gap-0.5" style={{borderColor:S.h,backgroundColor:S.c}}>
            <button onClick={()=>{sscm(false);fetch("/api/config/watch-paths").then(r=>r.json()).then(d=>{if(!d.paths||d.paths.length===0){setToast({message:t("scan.no_folders"),type:"error"});sso(true);}else{fetch("/api/scan",{method:"POST"}).then(r=>r.json()).then(d=>{setToast({message:d.message,type:"info"});fa();})}})}} className="text-left px-2 py-1 rounded text-xs" style={{color:S.i}} onMouseEnter={e=>{(e.target as HTMLElement).style.backgroundColor=S.s}} onMouseLeave={e=>{(e.target as HTMLElement).style.backgroundColor="transparent"}}>📂 {t("scan.scan_folder")}</button>
            <button onClick={()=>{sscm(false);scanningRef.current=true;fetch("/api/file-picker",{method:"POST"}).then(r=>r.json()).then(d=>{if(d.path)fetch("/api/scan-file",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:d.path})}).then(r=>r.json()).then(d=>{setToast({message:d.message,type:"info"});fa();});}).finally(()=>{scanningRef.current=false;});}} className="text-left px-2 py-1 rounded text-xs" style={{color:S.i}} onMouseEnter={e=>{(e.target as HTMLElement).style.backgroundColor=S.s}} onMouseLeave={e=>{(e.target as HTMLElement).style.backgroundColor="transparent"}}>📄 {t("scan.select_file")}</button>
            <button onClick={()=>{sscm(false);scanningRef.current=true;fetch("/api/folder-picker",{method:"POST"}).then(r=>r.json()).then(d=>{if(d.path)fetch("/api/scan-folder",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:d.path})}).then(r=>r.json()).then(d=>{setToast({message:d.message,type:"info"});fa();});}).finally(()=>{scanningRef.current=false;});}} className="text-left px-2 py-1 rounded text-xs" style={{color:S.i}} onMouseEnter={e=>{(e.target as HTMLElement).style.backgroundColor=S.s}} onMouseLeave={e=>{(e.target as HTMLElement).style.backgroundColor="transparent"}}>📁 {t("scan.select_folder")}</button>
          </div>}
          <button onClick={()=>sso(true)} className="w-full text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",color:S.m}}>⚙ {t("common.settings")}{missingConfig?<span className="w-2 h-2 rounded-full inline-block ml-1" style={{backgroundColor:"#c64545"}}></span>:null}</button>
        </div>
      </aside>
      {slc && <div className="fixed inset-0 z-40 flex items-center justify-center" style={{backgroundColor: "rgba(250,249,245,0.7)"}}><div className="text-center"><div className="animate-spin text-2xl mb-2">⏳</div><p className="text-sm" style={{color: "#6c6a64"}}>{t("search.searching")}</p></div></div>}
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="px-6 pt-4 pb-2">
        {ms.size>0&&<div className="flex items-center gap-3 mb-3 px-3 py-2 rounded-lg" style={{backgroundColor:S.d}}><span className="text-xs" style={{color:S.b}}>已选 {ms.size} 个</span><button onClick={()=>sm(new Set(fs.map(a=>a.id)))} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor:S.s,color:S.m}}>{t("batch.select_all")}</button><button onClick={()=>sm(new Set())} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor:S.s,color:S.m}}>{t("batch.deselect")}</button><button onClick={bRe} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>{t("batch.reanalyze")}</button><button onClick={bd} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:"#c64545",color:S.w}}>{t("batch.delete_selected")}</button></div>}
        <div className="flex gap-2 mb-4 items-center">
          <div className="flex gap-1 rounded-md p-0.5" style={{backgroundColor:S.s}}>
            <button onClick={()=>sv("grid")} className="px-2 py-1 text-xs rounded" style={{backgroundColor:vw==="grid"?S.c:"transparent",color:S.i}}>{t("view.grid")}</button>
            <button onClick={()=>sv("list")} className="px-2 py-1 text-xs rounded" style={{backgroundColor:vw==="list"?S.c:"transparent",color:S.i}}>{t("view.list")}</button>
            <button onClick={()=>sv("graph")} className="px-2 py-1 text-xs rounded" style={{backgroundColor:(vw as string)==="graph"?S.c:"transparent",color:S.i}}>{t("view.graph")}</button>
          </div>
          <select value={sb} onChange={e=>{const v=e.target.value;ssb(v as any);if(v==="hot"&&!didSearch)fa();}} className="text-xs px-2 py-1 rounded-md outline-none" style={{border:`1px solid ${S.h}`,color:S.m,backgroundColor:S.c}}>
            <option value="hot">{t("common.sort_hot")}</option><option value="recent">{t("common.sort_recent")}</option><option value="name">{t("common.sort_name")}</option><option value="size">{t("common.sort_size")}</option><option value="date">{t("common.sort_date")}</option>{(q&&didSearch&&(didSearchMode==="semantic"||didSearchMode==="combined"))&&<option value="score">{t("common.sort_score")}</option>}
          </select>
          {qStat.processing_name && <span className="text-[10px]" style={{color: '#e8a55a'}}>{t("queue.processing")}: {qStat.processing_name}</span>}
          {qStat.pending > 0 && <span className="text-[10px]" style={{color: S.ms}}>{t("queue.pending_count",{count: qStat.pending})}</span>}{qStat.pending > 0 && <button onClick={cq} className="text-[10px] ml-2 underline cursor-pointer" style={{color: S.ms}}>{t("queue.clear_all")}</button>}
          <span className="text-xs ml-auto" style={{color:S.ms}}>{t("common.item_count",{count: fs.length})}</span>
        </div>
        {vw!=="graph"&&selectedNodeId && (
          <div className="flex items-center gap-2 mb-3 px-3 py-1.5 rounded-md" style={{backgroundColor:S.rb, borderLeft:`3px solid ${S.r}`}}>
            <span className="text-xs" style={{color:S.r, fontFamily:"'Inter',sans-serif"}}>
              {t("node_filter.label",{name: selectedNodeName})}
            </span>
            <button
              onClick={()=>{setSelectedNodeId(null);setSelectedNodeName("");fa();}}
              className="text-xs px-2 py-0.5 rounded ml-auto font-medium"
              style={{color:S.r}}
              title={t("node_filter.clear_title")}
            >
              ✕ {t("node_filter.clear_text")}
            </button>
          </div>
        )}
        </div>
        <div className="flex-1 relative">
        <div className={`absolute inset-0${vw!=="graph"?" hidden":""}`}>
          <GraphView
            key={graphKey}
            graphData={graphData}
            selectedNodeId={selectedNodeId}
            selectedNodeName={selectedNodeName}
            onSelectNode={(nid:number|null,name?:string)=>{setSelectedNodeId(nid);setSelectedNodeName(name||"");if(!nid){sds(false);fa();}}}
            onSelectAsset={(aid:number)=>{selA(aid);}} 
            searchResults={searchResults}
            filteredAssets={fs}
            hasActiveFilter={!!(tf||ff.size>0||af.size>0||tgf.size>0||(q&&didSearch)||selectedNodeId)}
            expandedNodes={expandedNodes}
            onExpandedChange={setExpandedNodes}
            onReload={()=>{fetch("/api/graph").then(r=>r.json()).then(d=>{setGraphData(d);setExpandedNodes(new Set(d.nodes.map((n:any)=>n.id)));setGraphKey(k=>k+1);});}}
            onAssetDrop={(assetId:number, nodeId:number|number[], unassign:boolean)=>{
              if (unassign) {
                // Remove asset from all connected nodes back to unassigned
                const nodeIds = Array.isArray(nodeId) ? nodeId : [nodeId];
                Promise.all(nodeIds.map(nid =>
                  fetch(`/api/nodes/${nid}/assets/${assetId}`, { method: "DELETE" })
                )).then(results => {
                  const allOk = results.every(r => r.ok);
                  if (allOk || results.some(r => r.ok)) {
                    setNodeRefreshKey(k => k + 1);
                    // Refresh graph data from API instead of manual patch
                    fetch("/api/graph").then(r => r.json()).then(d => setGraphData(d));
                  }
                });
              } else {
              const nid = nodeId as number;
              fetch(`/api/nodes/${nid}/assets`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({asset_ids: [assetId]}),
              }).then(r=>r.json()).then(d=>{
                if (d.ok) {
                  setExpandedNodes((prev:Set<number>) => new Set(prev).add(nid));
                  setNodeRefreshKey(k => k + 1);
                  setGraphData((prev:any) => {
                    const exists = prev.edges.some((e:any) => e.asset_id === assetId && e.node_id === nid);
                    if (exists) return prev;
                    return {
                      nodes: prev.nodes.map((n:any) =>
                        n.id === nid ? {...n, asset_count: (n.asset_count||0) + 1} : n
                      ),
                      edges: [...prev.edges, {node_id: nid, asset_id: assetId}],
                      unassigned: prev.unassigned.filter((a:any) => a.id !== assetId),
                    };
                  });
                }
              });
              }
            }}
          />
        </div>
        <div className={`absolute inset-0 overflow-y-auto px-6 pb-6${vw==="graph"?" hidden":""}`}>
        {vw==="grid"?(
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {fs.map(a=>(<div key={a.id} onClick={()=>selA(a.id)} draggable onDragStart={(e)=>{e.dataTransfer.setData("text/plain",JSON.stringify({asset_id:a.id,source_node_id:null,filename:a.filename}));e.dataTransfer.effectAllowed="move";}} className="rounded-xl overflow-hidden cursor-pointer transition-shadow hover:shadow-sm relative" style={{backgroundColor:S.c,border:sel?.id===a.id?`2px solid ${S.r}`:`1px solid ${S.h}`}}>
              <div className="aspect-square flex flex-col items-center justify-center relative" style={{backgroundColor:S.s}}>
                {a.thumbnail_status==="done"?<img src={`/api/thumbnails/${a.id}?t=${a.modified_at||''}`} className="w-full h-full object-cover"/>:a.asset_type==="image"?<span className="text-sm animate-pulse" style={{color:S.m}}>{t("common.generating")}</span>:<>
                  <span className="text-4xl">{a.asset_type==="video"?"🎬":a.asset_type==="audio"?"🎵":a.asset_type==="document"?docI(a):"📄"}</span>
                  {a.asset_type==="document" && <DocPreview id={a.id} />}
                </>}
                {a._stars&&<span className="absolute top-1 right-1 text-xs"><span style={{color:"#e8a55a"}}>{"★".repeat(a._stars)}</span></span>}<span className="absolute top-1 left-1" onClick={e=>{e.stopPropagation();tgA(a.id);}}><input type="checkbox" checked={ms.has(a.id)} readOnly className="w-4 h-4 rounded accent-[#cc785c]"/></span>
              </div>
              <div className="p-3"><p className="text-sm font-medium truncate" style={{fontFamily:"'Inter',sans-serif",color:S.i}}>{hl(a.filename as any)}</p><p className="text-xs mt-0.5" style={{color:S.ms}}>{a.width&&a.height?`${a.width}×${a.height}`:a.duration?`${Math.round(a.duration)}秒`:""} {f(a.size)}{aiT(a.ai_status)&&<span className="ml-2">{aiT(a.ai_status)}</span>}</p>
                {a.tags.length>0&&<div className="flex gap-1 mt-1.5 flex-wrap">{a.tags.slice(0,3).map(t=>(<span key={t.id} className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{fontFamily:"'Inter',sans-serif",border:t.source==="auto"?`1px dashed ${S.ms}`:"none",backgroundColor:t.source==="auto"?"transparent":S.d,color:t.source==="auto"?S.m:S.b}}>{t.name}</span>))}</div>}
              </div>
            </div>))}
          </div>
        ):(
          <div className="flex flex-col gap-0.5">
            {fs.map(a=>(<div key={a.id} onClick={()=>selA(a.id)} draggable onDragStart={(e)=>{e.dataTransfer.setData("text/plain",JSON.stringify({asset_id:a.id,source_node_id:null,filename:a.filename}));e.dataTransfer.effectAllowed="move";}} className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer" style={{backgroundColor:sel?.id===a.id?S.d:"transparent",border:sel?.id===a.id?`1px solid ${S.r}`:`1px solid transparent`}}>
              <span className="text-lg">{a.asset_type==="video"?"🎬":a.asset_type==="audio"?"🎵":a.asset_type==="image"?"🖼️":"📄"}</span>
              <span className="text-sm flex-1 truncate" style={{color:S.i}}>{hl(a.filename)}</span>
              <span className="w-10 text-center">{aiT(a.ai_status)}</span>
              <span className="text-xs" style={{color:S.ms}}>{a.width&&a.height?`${a.width}×${a.height}`:a.duration?`${Math.round(a.duration)}秒`:""} {f(a.size)}</span>
              <span className="text-xs" style={{color:S.ms}}>{a.modified_at?.slice(0,10)||""}</span>
              <input type="checkbox" checked={ms.has(a.id)} onClick={e=>e.stopPropagation()} onChange={()=>tgA(a.id)} className="w-4 h-4 rounded accent-[#cc785c]"/>
            </div>))}
          </div>
        )}
        {fs.length===0&&<div className="text-center mt-20"><p className="text-4xl mb-4">📁</p><p style={{fontFamily:"'Inter',sans-serif",color:S.b}}>{t("detail.empty_title")}</p><p className="text-sm mt-2" style={{color:S.m}}>{t("detail.empty_hint")}</p></div>}
        </div>
        </div>
      </main>
      {sel&&<aside className="w-80 border-l overflow-y-auto p-4 flex flex-col gap-3" style={{borderColor:S.h,backgroundColor:S.c}}>
        <div className="flex justify-between items-center"><h2 className="text-sm font-medium truncate flex-1" style={{fontFamily:"'Inter',sans-serif",color:S.i}}>{sel.filename}</h2><button onClick={()=>setConfirmDeleteAsset(sel)} className="text-xs px-1.5 py-0.5 rounded" style={{color:S.r}} title={t("asset.detail_delete_btn")}>🗑</button><button onClick={()=>sl(null)} className="text-lg leading-none px-1" style={{color:S.ms}}>✕</button></div>
        {sel.thumbnail_status==="done"?<img src={`/api/thumbnails/${sel.id}?quality=full&t=${sel.modified_at||''}`} className="w-full rounded-lg" style={{border:`1px solid ${S.h}`,backgroundColor:S.s}}/>:<div className="w-full aspect-square rounded-lg flex items-center justify-center" style={{backgroundColor:S.s}}><span className="text-5xl">{sel.asset_type==="video"?"🎬":sel.asset_type==="audio"?"🎵":sel.asset_type==="document"?docI(sel):"📄"}</span></div>}
        <div><div className="text-[11px] mb-0.5" style={{color:S.ms}}>{t("asset.detail_path")} <span onClick={()=>{fetch(`/api/assets/${sel.id}/open`,{method:"POST"});fetch("/api/finder/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:sel.path})});}} className="cursor-pointer ml-1" title={t("asset.detail_open")}>📂</span></div><p className="text-xs break-all" style={{color:S.b}}>{sel.path}</p></div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div><span style={{color:S.ms}}>{t("asset.detail_type")}</span><p style={{color:S.b}}>{sel.asset_type}</p></div>
          <div><span style={{color:S.ms}}>{t("asset.detail_size")}</span><p style={{color:S.b}}>{f(sel.size)}</p></div>
          {sel.width&&sel.height&&<div><span style={{color:S.ms}}>{t("asset.detail_dimensions")}</span><p style={{color:S.b}}>{sel.width}×{sel.height}</p></div>}
          {sel.duration&&<div><span style={{color:S.ms}}>{t("asset.detail_duration")}</span><p style={{color:S.b}}>{Math.round(sel.duration)}{t("common.seconds")}</p></div>}
          {sel.modified_at&&<div><span style={{color:S.ms}}>{t("asset.detail_modified")}</span><p style={{color:S.b}}>{sel.modified_at.slice(0,10)}</p></div>}
        </div>
        {sel.ai_status&&sel.ai_status!=="-"&&<div className="text-xs flex items-center gap-2"><span style={{color:S.ms}}>{t("asset.detail_ai_status")}: </span><span style={{color:sel.ai_status==="done"?"#5db872":sel.ai_status==="processing"?"#e8a55a":sel.ai_status==="failed"?"#c64545":S.m}}>{sel.ai_status==="done"?t("asset.detail_ai_done"):sel.ai_status==="processing"?t("asset.detail_ai_processing") + "...":sel.ai_status==="pending"?t("asset.detail_ai_pending"):sel.ai_status==="cancelled"?t("asset.detail_ai_cancelled"):sel.ai_status}</span>{sel.ai_status==="failed"?<button onClick={()=>fetch(`/api/assets/${sel.id}/retry-ai`,{method:"POST"}).then(()=>selA(sel.id)).then(()=>fa())} className="text-xs px-2 py-0.5 rounded-md" style={{backgroundColor:S.r,color:S.w}}>{t("asset.detail_ai_retry")}</button>:<button onClick={()=>fetch(`/api/assets/${sel.id}/reanalyze`,{method:"POST"}).then(()=>{selA(sel.id);})} className="text-xs px-2 py-0.5 rounded-md" style={{backgroundColor:S.d,color:S.b}}>{t("asset.detail_reanalyze")}</button>}</div>}
        {(sel.visual_description||sel.ai_summary||sel.video_summary)&& <div><button onClick={() => scp(sel.id)} className="text-xs px-2 py-1 rounded-md" style={{backgroundColor: S.rb, color: S.r}}>🔍 {t("asset.detail_similar")}</button></div>}
        {sel.visual_description&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_ai_desc")}</div><p className="text-xs" style={{color:S.b}}>{sel.visual_description}</p></div>}
        {sel.ocr_text&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_ocr")}</div><p className="text-xs" style={{color:S.b}}>{sel.ocr_text}</p></div>}
        {sel.transcript&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_transcript")}</div><p className="text-xs max-h-32 overflow-y-auto whitespace-pre-wrap" style={{color:S.b}}>{sel.transcript}</p></div>}
        {sel.ai_summary&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_summary")}</div><p className="text-xs" style={{color:S.b}}>{sel.ai_summary}</p></div>}
        {sel.video_summary&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_video_summary")}</div><p className="text-xs" style={{color:S.b}}>{sel.video_summary}</p></div>}
        <div style={{borderTop:`1px solid ${S.h}`}}/>
        <div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.detail_description")}</div>
          {ed?<div><textarea ref={dr} value={dv} onChange={e=>sd(e.target.value)} className="w-full text-sm p-2 rounded-md outline-none resize-none" rows={3} style={{fontFamily:"'Inter',sans-serif",border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><div className="flex gap-2 mt-1"><button onClick={svD} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>{t("asset.detail_save")}</button><button onClick={()=>{se(false);sd(sel.description||"");}} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.d,color:S.b}}>{t("asset.detail_cancel")}</button></div></div>:<p onClick={()=>{se(true);setTimeout(()=>dr.current?.focus(),0);}} className="text-sm cursor-pointer p-2 rounded-md min-h-[2rem]" style={{fontFamily:"'Inter',sans-serif",color:sel.description?S.b:S.ms,backgroundColor:S.s}}>{sel.description||(t("asset.detail_add_desc")+"...")}</p>}
        </div>
        <div><div className="text-[11px] mb-1" style={{color:S.ms}}>{t("asset.filter_tags")}</div>
          <div className="flex gap-1.5 flex-wrap mb-2">{sel.tags.map(t=>(<span key={t.id} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium group" style={{fontFamily:"'Inter',sans-serif",border:t.source==="auto"?`1px dashed ${S.r}`:`1px solid ${S.h}`,backgroundColor:t.source==="auto"?S.rb:S.d,color:t.source==="auto"?S.r:S.b,cursor:"pointer"}}>{t.name}<span onClick={()=>rmT(t.id)} className="text-[10px] opacity-0 group-hover:opacity-100">✕</span></span>))}</div>
          <div className="flex gap-2"><input type="text" placeholder={t("asset.detail_new_tag")} value={nt} onChange={e=>sn(e.target.value)} onKeyDown={e=>e.key==="Enter"&&adT()} className="flex-1 text-xs px-2 py-1 rounded-md outline-none" style={{fontFamily:"'Inter',sans-serif",border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={adT} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>{t("asset.detail_select")}</button></div>
        </div>
      </aside>}
      {so && <SettingsModal onClose={() => {sso(false);ckCfg();}} initialTab={settingsTab} initialModelTab={settingsTab==="models"?"tasks":undefined} onModelSave={()=>setTimeout(ckCfg,500)} />}
      {mm && <ModelManager onClose={() => smm(false)} />}
      {cp && <SimilarPanel assetId={cp} onClose={() => scp(null)} onSelect={(id) => selA(id)} />}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {queueClearConfirm && (<ConfirmModal title={t("queue.clear_all")} message={t("queue.clear_confirm")} confirmText={t("common.delete")} confirmColor="error" onConfirm={()=>{fetch("/api/ai-queue",{method:"DELETE"}).then(r=>r.json()).then(d=>{if(d.ok){setQStat({pending:0,processing_name:null});}});setQueueClearConfirm(false);}} onCancel={()=>setQueueClearConfirm(false)}/>)}
      {batchDeleteConfirm && (<ConfirmModal title={batchDeleteConfirm.title} message={batchDeleteConfirm.message} confirmText={t("common.delete")} confirmColor="error" onConfirm={()=>{batchDeleteConfirm.action();setBatchDeleteConfirm(null);}} onCancel={()=>setBatchDeleteConfirm(null)}/>)}
      {confirmDeleteAsset && (
        <ConfirmModal
          title={t("asset.detail_delete")}
          message={t("asset.detail_delete_confirm", {name: confirmDeleteAsset.filename})}
          confirmText={t("asset.detail_delete_btn")}
          confirmColor="error"
          onConfirm={() => { delA(confirmDeleteAsset.id); setConfirmDeleteAsset(null); }}
          onCancel={() => setConfirmDeleteAsset(null)}
        />
      )}
    </div>
  );
}
export default App;
