import { useState, useEffect, useRef } from "react";

interface Asset {
  id: number; filename: string; asset_type: string; size: number;
  width?: number; height?: number; duration?: number; path: string;
  description?: string; ai_description?: string; ai_summary?: string;
  ocr_text?: string; transcript?: string; video_summary?: string;
  ai_status?: string;
  thumbnail_status: string; modified_at?: string;
  tags: { id: number; name: string; source: string }[];
}
interface Stats { total: number; image: number; video: number; audio: number; document: number; }
interface TagInfo { id: number; name: string; count: number; }

const f=(b:number)=>{for(const u of["B","KB","MB","GB"]){if(b<1024)return`${b}${u}`;b=Math.floor(b/1024);}return`${b}TB`;};
const S={c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};
const aiT=(s?:string)=>{if(!s||s==="-")return null;const m:{[k:string]:string}={done:"已完成",processing:"分析中...",pending:"等待分析",failed:"失败"};return <span className="text-[10px]" style={{color:S.ms}}>{m[s]||s}</span>;};

function App() {
  const [as,sa]=useState<Asset[]>([]);
  const [st,ss]=useState<Stats>({total:0,image:0,video:0,audio:0,document:0});
  const [tg,stg]=useState<TagInfo[]>([]);
  const [tf,stf]=useState<string|null>(null);
  const [gf,sgf]=useState<number|null>(null);
  const [q,sq]=useState("");
  const [sel,sl]=useState<Asset|null>(null);
  const [ed,se]=useState(false);
  const [dv,sd]=useState("");
  const [nt,sn]=useState("");
  const [sh,ssh]=useState(false);
  const [cu,scu]=useState("");
  const [cm,scm]=useState("");
  const [os,sos]=useState("");
  const [cfn,scfn]=useState(1);
  const [cto,scto]=useState(300);
  const [vw,sv]=useState<"grid"|"list">("grid");
  const [sb,ssb]=useState<"name"|"size"|"date">("name");
  const [ms,sm]=useState<Set<number>>(new Set());
  const dr=useRef<HTMLTextAreaElement>(null);

  useEffect(()=>{fetch("/api/stats").then(r=>r.json()).then(ss);},[]);
  useEffect(()=>{fetch("/api/tags").then(r=>r.json()).then(stg);},[]);
  const fa=()=>{if(q){fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r=>r.json()).then(sa);return;}const p=new URLSearchParams();if(tf)p.set("type",tf);p.set("limit","200");fetch(`/api/assets?${p}`).then(r=>r.json()).then(d=>sa(d.items));};
  useEffect(()=>{fa();},[tf,q]);

  let fs=as;if(gf)fs=as.filter(a=>a.tags.some(t=>t.id===gf));
  fs=[...fs].sort((a,b)=>{if(sb==="size")return b.size-a.size;if(sb==="date")return(b.modified_at||"").localeCompare(a.modified_at||"");return a.filename.localeCompare(b.filename);});

  const selA=(id:number)=>{fetch(`/api/assets/${id}`).then(r=>r.json()).then(a=>{sl(a);sd(a.description||"");se(false);});};
  const svD=()=>{if(!sel)return;fetch(`/api/assets/${sel.id}`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({description:dv})}).then(()=>{sl({...sel,description:dv});se(false);});};
  const adT=()=>{if(!sel||!nt.trim())return;fetch(`/api/assets/${sel.id}/tags/by-name`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:nt.trim()})}).then(r=>r.json()).then(t=>{sl({...sel,tags:[...sel.tags,{id:t.id,name:t.name,source:"manual"}]});sn("");fetch("/api/tags").then(r=>r.json()).then(stg);fa();});};
  const rmT=(tid:number)=>{if(!sel)return;fetch(`/api/assets/${sel.id}/tags/${tid}`,{method:"DELETE"}).then(()=>{sl({...sel,tags:sel.tags.filter(t=>t.id!==tid)});fetch("/api/tags").then(r=>r.json()).then(stg);});};
  const cfT=(tid:number)=>{if(!sel)return;fetch(`/api/assets/${sel.id}/tags/${tid}`,{method:"DELETE"}).then(()=>fetch(`/api/assets/${sel.id}/tags/${tid}`,{method:"POST"})).then(()=>{sl({...sel,tags:sel.tags.map(t=>t.id===tid?{...t,source:"manual"}:t)});});};
  const svS=()=>{fetch("/api/config",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({ollama_url:cu,model:cm,video_frames:cfn,timeout:cto})}).then(()=>ssh(false));};
  const tO=()=>{fetch("/api/config/test-ollama",{method:"POST"}).then(r=>r.json()).then(d=>{sos(d.connected?`已连接: ${d.models.join(", ")}`:`失败: ${d.error}`);});};
  const tgA=(id:number)=>{const n=new Set(ms);n.has(id)?n.delete(id):n.add(id);sm(n);};
  const bRe=()=>{fetch("/api/assets/batch-reanalyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({asset_ids:[...ms]})}).then(()=>{sm(new Set());fa();});};
  const delA=(id:number)=>{fetch(`/api/assets/${id}`,{method:"DELETE"}).then(()=>{sl(null);fa();});};

  const types=[{k:null,l:"全部素材",n:st.total},{k:"image",l:"图片",n:st.image},{k:"video",l:"视频",n:st.video},{k:"audio",l:"音频",n:st.audio},{k:"document",l:"文档",n:st.document}];

  const hl=(text:string):any=>{if(!q)return text;const i=text.toLowerCase().indexOf(q.toLowerCase());if(i<0)return text;return <>{text.slice(0,i)}<span style={{color:S.r,fontWeight:600}}>{text.slice(i,i+q.length)}</span>{text.slice(i+q.length)}</>;};

  return (
    <div className="flex h-screen" style={{backgroundColor:S.c}}>
      <aside className="w-56 flex flex-col gap-0.5 p-4 border-r overflow-y-auto" style={{borderColor:S.h}}>
        <h1 style={{fontFamily:"'Tiempos Headline',Garamond,serif",fontSize:22,fontWeight:400,color:S.i}} className="mb-4">QuickMedia</h1>
        <input type="text" placeholder="搜索..." value={q} onChange={e=>sq(e.target.value)} className="w-full px-3 py-1.5 text-sm rounded-md mb-3 outline-none" style={{fontFamily:"'Inter',sans-serif",backgroundColor:S.c,border:`1px solid ${S.h}`,color:S.i}}/>
        <div className="text-xs mb-2" style={{color:S.ms}}>类型</div>
        {types.map(t=>(<button key={t.l} onClick={()=>{stf(t.k);sgf(null);}} className="text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",backgroundColor:tf===t.k?S.d:"transparent",color:tf===t.k?S.i:S.m,fontWeight:tf===t.k?500:400}}>{t.l}<span className="float-right opacity-50">({t.n})</span></button>))}
        {tg.filter(t=>t.count>0).length>0&&(<>
          <div className="text-xs mb-2 mt-4" style={{color:S.ms}}>标签</div>
          {tg.filter(t=>t.count>0).sort((a,b)=>b.count-a.count).map(t=>(<button key={t.id} onClick={()=>{sgf(gf===t.id?null:t.id);stf(null);}} className="text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",backgroundColor:gf===t.id?S.d:"transparent",color:gf===t.id?S.i:S.m,fontWeight:gf===t.id?500:400}}>{t.name}<span className="float-right opacity-50">({t.count})</span></button>))}
        </>)}
        <div className="mt-auto pt-4 flex flex-col gap-1" style={{borderTop:`1px solid ${S.h}`}}>
          <button onClick={()=>fetch("/api/scan",{method:"POST"}).then(r=>r.json()).then(d=>{alert(d.message);fa();})} className="w-full text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",color:S.m}}>🔍 扫描新素材</button>
          <button onClick={()=>{ssh(!sh);if(!sh){fetch("/api/config").then(r=>r.json()).then(c=>{scu(c.ollama_url);scm(c.model);scfn(c.video_frames||1);scto(c.timeout||300);});}}} className="w-full text-left px-3 py-1.5 rounded-md text-sm" style={{fontFamily:"'Inter',sans-serif",backgroundColor:sh?S.d:"transparent",color:sh?S.i:S.m}}>⚙ 设置</button>
        </div>
      </aside>
      {sh&&(<aside className="w-72 border-r overflow-y-auto p-4 flex flex-col gap-3" style={{borderColor:S.h,backgroundColor:S.c}}>
        <h2 className="text-sm font-medium" style={{color:S.i}}>设置</h2>
        <div><label className="text-[11px]" style={{color:S.ms}}>Ollama URL</label><input type="text" value={cu} onChange={e=>scu(e.target.value)} className="w-full text-xs px-2 py-1 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
        <div><label className="text-[11px]" style={{color:S.ms}}>模型</label><input type="text" value={cm} onChange={e=>scm(e.target.value)} className="w-full text-xs px-2 py-1 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
        <div><label className="text-[11px]" style={{color:S.ms}}>视频采样帧数</label><input type="number" min={1} max={20} value={cfn} onChange={e=>scfn(parseInt(e.target.value)||1)} className="w-full text-xs px-2 py-1 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
        <div><label className="text-[11px]" style={{color:S.ms}}>请求超时 (秒)</label><input type="number" min={30} max={600} value={cto} onChange={e=>scto(parseInt(e.target.value)||300)} className="w-full text-xs px-2 py-1 rounded-md outline-none mt-0.5" style={{border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/></div>
        <div className="flex gap-2"><button onClick={tO} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor:S.d,color:S.b}}>检测连接</button><button onClick={svS} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor:S.r,color:S.w}}>保存</button></div>
        {os&&<p className="text-xs" style={{color:os.startsWith("已连接")?S.m:S.r}}>{os}</p>}
      </aside>)}
      <main className="flex-1 overflow-y-auto p-6">
        {ms.size>0&&<div className="flex items-center gap-3 mb-3 px-3 py-2 rounded-lg" style={{backgroundColor:S.d}}><span className="text-xs" style={{color:S.b}}>已选 {ms.size} 个</span><button onClick={bRe} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>重新分析已选</button><button onClick={()=>sm(new Set())} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor:S.s,color:S.m}}>取消选择</button></div>}
        <div className="flex gap-2 mb-4 items-center">
          <div className="flex gap-1 rounded-md p-0.5" style={{backgroundColor:S.s}}>
            <button onClick={()=>sv("grid")} className="px-2 py-1 text-xs rounded" style={{backgroundColor:vw==="grid"?S.c:"transparent",color:S.i}}>▦ 网格</button>
            <button onClick={()=>sv("list")} className="px-2 py-1 text-xs rounded" style={{backgroundColor:vw==="list"?S.c:"transparent",color:S.i}}>☰ 列表</button>
          </div>
          <select value={sb} onChange={e=>ssb(e.target.value as any)} className="text-xs px-2 py-1 rounded-md outline-none" style={{border:`1px solid ${S.h}`,color:S.m,backgroundColor:S.c}}>
            <option value="name">按名称</option><option value="size">按大小</option><option value="date">按时间</option>
          </select>
          <span className="text-xs ml-auto" style={{color:S.ms}}>{fs.length} 个素材</span>
        </div>
        {vw==="grid"?(
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {fs.map(a=>(<div key={a.id} onClick={()=>selA(a.id)} className="rounded-xl overflow-hidden cursor-pointer transition-shadow hover:shadow-sm relative" style={{backgroundColor:S.c,border:sel?.id===a.id?`2px solid ${S.r}`:`1px solid ${S.h}`}}>
              <div className="aspect-square flex items-center justify-center relative" style={{backgroundColor:S.s}}>
                {a.thumbnail_status==="done"?<img src={`/api/thumbnails/${a.id}?t=${a.modified_at||''}`} className="w-full h-full object-cover"/>:a.asset_type==="image"?<span className="text-sm animate-pulse" style={{color:S.m}}>生成中...</span>:<span className="text-4xl">{a.asset_type==="video"?"🎬":a.asset_type==="audio"?"🎵":"📄"}</span>}
                <span className="absolute top-1 left-1" onClick={e=>{e.stopPropagation();tgA(a.id);}}><input type="checkbox" checked={ms.has(a.id)} readOnly className="w-4 h-4 rounded accent-[#cc785c]"/></span>
              </div>
              <div className="p-3"><p className="text-sm font-medium truncate" style={{fontFamily:"'Inter',sans-serif",color:S.i}}>{hl(a.filename as any)}</p><p className="text-xs mt-0.5" style={{color:S.ms}}>{a.width&&a.height?`${a.width}×${a.height}`:a.duration?`${Math.round(a.duration)}秒`:""} {f(a.size)}{aiT(a.ai_status)&&<span className="ml-2">{aiT(a.ai_status)}</span>}</p>
                {a.tags.length>0&&<div className="flex gap-1 mt-1.5 flex-wrap">{a.tags.slice(0,3).map(t=>(<span key={t.id} className="text-[10px] px-1.5 py-0.5 rounded-full font-medium" style={{fontFamily:"'Inter',sans-serif",border:t.source==="auto"?`1px dashed ${S.ms}`:"none",backgroundColor:t.source==="auto"?"transparent":S.d,color:t.source==="auto"?S.m:S.b}}>{t.name}</span>))}</div>}
              </div>
            </div>))}
          </div>
        ):(
          <div className="flex flex-col gap-0.5">
            {fs.map(a=>(<div key={a.id} onClick={()=>selA(a.id)} className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer" style={{backgroundColor:sel?.id===a.id?S.d:"transparent",border:sel?.id===a.id?`1px solid ${S.r}`:`1px solid transparent`}}>
              <span className="text-lg">{a.asset_type==="video"?"🎬":a.asset_type==="audio"?"🎵":a.asset_type==="image"?"🖼️":"📄"}</span>
              <span className="text-sm flex-1 truncate" style={{color:S.i}}>{hl(a.filename)}</span>
              <span className="w-10 text-center">{aiT(a.ai_status)}</span>
              <span className="text-xs" style={{color:S.ms}}>{a.width&&a.height?`${a.width}×${a.height}`:a.duration?`${Math.round(a.duration)}秒`:""} {f(a.size)}</span>
              <span className="text-xs" style={{color:S.ms}}>{a.modified_at?.slice(0,10)||""}</span>
              <input type="checkbox" checked={ms.has(a.id)} onClick={e=>e.stopPropagation()} onChange={()=>tgA(a.id)} className="w-4 h-4 rounded accent-[#cc785c]"/>
            </div>))}
          </div>
        )}
        {fs.length===0&&<div className="text-center mt-20"><p className="text-4xl mb-4">📁</p><p style={{fontFamily:"'Inter',sans-serif",color:S.b}}>暂无素材</p><p className="text-sm mt-2" style={{color:S.m}}>运行 quickmedia scan 来扫描素材</p></div>}
      </main>
      {sel&&<aside className="w-80 border-l overflow-y-auto p-4 flex flex-col gap-3" style={{borderColor:S.h,backgroundColor:S.c}}>
        <div className="flex justify-between items-center"><h2 className="text-sm font-medium truncate flex-1" style={{fontFamily:"'Inter',sans-serif",color:S.i}}>{sel.filename}</h2><button onClick={()=>{if(confirm(`确认删除 ${sel.filename}？`))delA(sel.id)}} className="text-xs px-1.5 py-0.5 rounded" style={{color:S.r}} title="删除">🗑</button><button onClick={()=>sl(null)} className="text-lg leading-none px-1" style={{color:S.ms}}>✕</button></div>
        {sel.thumbnail_status==="done"?<img src={`/api/thumbnails/${sel.id}?t=${sel.modified_at||''}`} className="w-full rounded-lg" style={{border:`1px solid ${S.h}`}}/>:<div className="w-full aspect-square rounded-lg flex items-center justify-center" style={{backgroundColor:S.s}}><span className="text-5xl">{sel.asset_type==="video"?"🎬":sel.asset_type==="audio"?"🎵":"📄"}</span></div>}
        <div><div className="text-[11px] mb-0.5" style={{color:S.ms}}>路径 <span onClick={()=>fetch("/api/finder/open",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:sel.path})})} className="cursor-pointer ml-1" title="在 Finder 中打开">📂</span></div><p className="text-xs break-all" style={{color:S.b}}>{sel.path}</p></div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div><span style={{color:S.ms}}>类型</span><p style={{color:S.b}}>{sel.asset_type}</p></div>
          <div><span style={{color:S.ms}}>大小</span><p style={{color:S.b}}>{f(sel.size)}</p></div>
          {sel.width&&sel.height&&<div><span style={{color:S.ms}}>尺寸</span><p style={{color:S.b}}>{sel.width}×{sel.height}</p></div>}
          {sel.duration&&<div><span style={{color:S.ms}}>时长</span><p style={{color:S.b}}>{Math.round(sel.duration)}秒</p></div>}
          {sel.modified_at&&<div><span style={{color:S.ms}}>修改时间</span><p style={{color:S.b}}>{sel.modified_at.slice(0,10)}</p></div>}
        </div>
        {sel.ai_status&&sel.ai_status!=="-"&&<div className="text-xs flex items-center gap-2"><span style={{color:S.ms}}>AI 状态: </span><span style={{color:sel.ai_status==="done"?"#5db872":sel.ai_status==="processing"?"#e8a55a":sel.ai_status==="failed"?"#c64545":S.m}}>{sel.ai_status==="done"?"已完成":sel.ai_status==="processing"?"分析中...":sel.ai_status==="pending"?"等待分析":sel.ai_status}</span>{sel.ai_status==="failed"?<button onClick={()=>fetch(`/api/assets/${sel.id}/retry-ai`,{method:"POST"}).then(()=>selA(sel.id)).then(()=>fa())} className="text-xs px-2 py-0.5 rounded-md" style={{backgroundColor:S.r,color:S.w}}>重试</button>:<button onClick={()=>fetch(`/api/assets/${sel.id}/reanalyze`,{method:"POST"}).then(()=>{selA(sel.id);fa();})} className="text-xs px-2 py-0.5 rounded-md" style={{backgroundColor:S.d,color:S.b}}>重新分析</button>}</div>}
        {sel.ai_description&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>AI 描述</div><p className="text-xs" style={{color:S.b}}>{sel.ai_description}</p></div>}
        {sel.ocr_text&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>OCR 文字</div><p className="text-xs" style={{color:S.b}}>{sel.ocr_text}</p></div>}
        {sel.transcript&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>语音转录</div><p className="text-xs max-h-32 overflow-y-auto whitespace-pre-wrap" style={{color:S.b}}>{sel.transcript}</p></div>}
        {sel.ai_summary&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>AI 摘要</div><p className="text-xs" style={{color:S.b}}>{sel.ai_summary}</p></div>}
        {sel.video_summary&&<div><div className="text-[11px] mb-1" style={{color:S.ms}}>综合总结</div><p className="text-xs" style={{color:S.b}}>{sel.video_summary}</p></div>}
        <div style={{borderTop:`1px solid ${S.h}`}}/>
        <div><div className="text-[11px] mb-1" style={{color:S.ms}}>描述</div>
          {ed?<div><textarea ref={dr} value={dv} onChange={e=>sd(e.target.value)} className="w-full text-sm p-2 rounded-md outline-none resize-none" rows={3} style={{fontFamily:"'Inter',sans-serif",border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><div className="flex gap-2 mt-1"><button onClick={svD} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>保存</button><button onClick={()=>{se(false);sd(sel.description||"");}} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.d,color:S.b}}>取消</button></div></div>:<p onClick={()=>{se(true);setTimeout(()=>dr.current?.focus(),0);}} className="text-sm cursor-pointer p-2 rounded-md min-h-[2rem]" style={{fontFamily:"'Inter',sans-serif",color:sel.description?S.b:S.ms,backgroundColor:S.s}}>{sel.description||"点击添加描述..."}</p>}
        </div>
        <div><div className="text-[11px] mb-1" style={{color:S.ms}}>标签</div>
          <div className="flex gap-1.5 flex-wrap mb-2">{sel.tags.map(t=>(<span key={t.id} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-medium group" style={{fontFamily:"'Inter',sans-serif",border:t.source==="auto"?`1px dashed ${S.r}`:`1px solid ${S.h}`,backgroundColor:t.source==="auto"?S.rb:S.d,color:t.source==="auto"?S.r:S.b,cursor:"pointer"}}>{t.name}{t.source==="auto"?<span onClick={()=>cfT(t.id)} className="text-[10px] opacity-0 group-hover:opacity-100">✓</span>:<span onClick={()=>rmT(t.id)} className="text-[10px] opacity-0 group-hover:opacity-100">✕</span>}</span>))}</div>
          <div className="flex gap-2"><input type="text" placeholder="新标签..." value={nt} onChange={e=>sn(e.target.value)} onKeyDown={e=>e.key==="Enter"&&adT()} className="flex-1 text-xs px-2 py-1 rounded-md outline-none" style={{fontFamily:"'Inter',sans-serif",border:`1px solid ${S.h}`,color:S.i,backgroundColor:S.c}}/><button onClick={adT} className="text-xs px-3 py-1 rounded-md font-medium" style={{backgroundColor:S.r,color:S.w}}>添加</button></div>
        </div>
      </aside>}
    </div>
  );
}
export default App;
