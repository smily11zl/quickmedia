import { useState, useEffect } from "react";

const S = {c:"#faf9f5",h:"#e6dfd8",d:"#efe9de",s:"#f5f0e8",i:"#141413",b:"#3d3d3a",m:"#6c6a64",ms:"#8e8b82",r:"#cc785c",rb:"rgba(204,120,92,0.08)",w:"#fff"};

interface ProviderData {
  url: string;
  api_key?: string;
}

interface TaskBinding {
  provider: string;
  model: string;
}

interface ProviderInfo {
  name: string;
  url: string;
}

const TASK_LABELS: Record<string, string> = {
  vision: "图片分析",
  text: "文档分析",
  speech: "语音分析",
  video_summary: "视频总结",
};

const TASK_HINTS: Record<string, string> = {
  vision: "分析图片/视频帧的内容、标签和文字",
  text: "分析文档类素材的摘要和关键词",
  speech: "分析语音转写文本的摘要和主题",
  video_summary: "综合画面描述和语音内容生成总结",
};

const BUILTIN_PROVIDERS: ProviderInfo[] = [
  {name: "ollama", url: "http://localhost:11434/v1"},
  {name: "openrouter", url: "https://openrouter.ai/api/v1"},
  {name: "deepseek", url: "https://api.deepseek.com/v1"},
  {name: "openai", url: "https://api.openai.com/v1"},
];

function saveProviders(providers: Record<string, ProviderData>, taskModels: Record<string, TaskBinding>): Promise<boolean> {
  return fetch("/api/providers", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify({providers, task_models: taskModels})})
    .then(r => r.json())
    .then(r => r.ok === true);
}

export default function ModelManager({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<"providers" | "tasks">("providers");
  const [selProvider, setSelProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<Record<string, {name:string;capabilities:string[]}[]>>({});
  const [testStatus, setTestStatus] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [editUrl, setEditUrl] = useState<string | null>(null);
  const [editUrlVal, setEditUrlVal] = useState("");
  const [openModelPicker, setOpenModelPicker] = useState<string | null>(null);
  const [editProviders, setEditProviders] = useState<Record<string, ProviderData>>({});
  const [editTaskModels, setEditTaskModels] = useState<Record<string, TaskBinding>>({});

  useEffect(() => {
    fetch("/api/providers").then(r => r.json()).then(d => {
      setEditProviders({...(d.providers || {})});
      setEditTaskModels({...(d.task_models || {})});
      const m: Record<string, {name:string;capabilities:string[]}[]> = {};
      Object.keys(d.providers || {}).forEach((p: string) => {
        fetch(`/api/providers/${p}/models`).then(r => r.json()).then(r2 => {
          m[p] = r2.models || [];
          setModels({...m});
        }).catch(() => {});
      });
    });
  }, []);

  const availableProviders = BUILTIN_PROVIDERS.filter(p => !(p.name in editProviders));

  const addProvider = () => {
    if (!selProvider) return;
    const info = BUILTIN_PROVIDERS.find(p => p.name === selProvider);
    if (!info) return;
    const updated = {...editProviders, [selProvider]: {url: info.url, api_key: apiKey}};
    setEditProviders(updated);
    saveProviders(updated, editTaskModels).then(ok => {
      setMsg(ok ? "已添加" : "添加失败");
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
    fetch(`/api/providers/${selProvider}/models`).then(r => r.json()).then(r2 => {
      setModels(prev => ({...prev, [selProvider]: r2.models || []}));
    }).catch(() => {});
    setSelProvider("");
    setApiKey("");
  };

  const removeProvider = (name: string) => {
    const updated = {...editProviders};
    delete updated[name];
    setEditProviders(updated);
    const tm = {...editTaskModels};
    for (const t of Object.keys(tm)) {
      if (tm[t].provider === name) tm[t] = {provider: "", model: ""};
    }
    setEditTaskModels(tm);
    saveProviders(updated, tm).then(ok => {
      setMsg(ok ? "已删除" : "删除失败");
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
  };

  const saveUrl = (name: string) => {
    if (!editUrlVal.trim()) return;
    const updated = {...editProviders, [name]: {...editProviders[name], url: editUrlVal.trim()}};
    setEditProviders(updated);
    setEditUrl(null);
    saveProviders(updated, editTaskModels).then(ok => {
      setMsg(ok ? "已保存" : "保存失败");
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
  };

  const updateTask = (taskType: string, provider: string, model: string) => {
    setEditTaskModels({...editTaskModels, [taskType]: {provider, model}});
  };

  const saveTasks = () => {
    saveProviders(editProviders, editTaskModels).then(ok => {
      setMsg(ok ? "已保存" : "保存失败");
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
  };

  const testProvider = (name: string, url: string) => {
    setTestStatus({...testStatus, [name]: "测试中..."});
    fetch("/api/providers/test", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({provider: name, url})})
      .then(r => r.json())
      .then(r => setTestStatus({...testStatus, [name]: r.ok ? "已连接" : (r.error || "连接失败")}))
      .catch(() => setTestStatus({...testStatus, [name]: "连接失败"}));
  };

  const providerModels = (provider: string): {name:string;capabilities:string[]}[] => models[provider] || [];

  const capLabel = (caps: string[]) => {
    const labels: Record<string,string> = {vision:"图片", text:"文字", speech:"语音"};
    return caps.map(c => labels[c]||c).join("/") || "通用";
  };

  return (
    <div className="w-96 border-l overflow-y-auto p-4 flex flex-col gap-4" style={{borderColor: S.h, backgroundColor: S.c}}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium" style={{color: S.i}}>模型管理</h2>
        <button onClick={onClose} className="text-xs px-2 py-1 rounded" style={{color: S.ms, backgroundColor: S.s}}>✕ 关闭</button>
      </div>

      <div className="flex gap-1 p-0.5 rounded-md" style={{backgroundColor: S.s}}>
        <button onClick={() => setTab("providers")} className="flex-1 text-xs py-1 rounded" style={{backgroundColor: tab === "providers" ? S.c : "transparent", color: tab === "providers" ? S.i : S.ms}}>Provider 管理</button>
        <button onClick={() => setTab("tasks")} className="flex-1 text-xs py-1 rounded" style={{backgroundColor: tab === "tasks" ? S.c : "transparent", color: tab === "tasks" ? S.i : S.ms}}>任务配置</button>
      </div>

      {tab === "providers" && (
        <div className="flex flex-col gap-3">
          {Object.keys(editProviders).length > 0 ? (
            <div className="flex flex-col gap-2">
              {Object.entries(editProviders).map(([name, p]) => (
                <div key={name} className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium" style={{color: S.i}}>{name}</span>
                    <div className="flex gap-1">
                      <button onClick={() => testProvider(name, p.url)} className="text-[10px] px-2 py-0.5 rounded" style={{backgroundColor: S.d, color: S.b}}>测试</button>
                      {name !== "ollama" && (
                        <button onClick={() => removeProvider(name)} className="text-[10px] px-2 py-0.5 rounded" style={{backgroundColor: S.rb, color: S.r}}>删除</button>
                      )}
                    </div>
                  </div>
                  {editUrl === name ? (
                    <div className="flex gap-1 mt-0.5">
                      <input value={editUrlVal} onChange={e => setEditUrlVal(e.target.value)} onKeyDown={e => e.key === "Enter" && saveUrl(name)} className="text-[10px] px-1 py-0.5 rounded outline-none flex-1" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}} />
                      <button onClick={() => saveUrl(name)} className="text-[10px] px-1 py-0.5 rounded" style={{backgroundColor: S.r, color: S.w}}>✓</button>
                      <button onClick={() => setEditUrl(null)} className="text-[10px] px-1 py-0.5 rounded" style={{backgroundColor: S.s, color: S.m}}>✕</button>
                    </div>
                  ) : (
                    <p className="text-[10px] mt-0.5 cursor-pointer hover:underline" style={{color: S.ms}} onClick={() => { setEditUrl(name); setEditUrlVal(p.url); }}>
                      URL: {p.url}
                    </p>
                  )}
                  {p.api_key && <p className="text-[10px]" style={{color: S.ms}}>Key: {p.api_key.slice(0,4)}****{p.api_key.slice(-4)}</p>}
                  {testStatus[name] && <p className="text-[10px] mt-0.5" style={{color: testStatus[name] === "已连接" ? "#5db872" : testStatus[name] === "测试中..." ? S.m : "#c64545"}}>{testStatus[name]}</p>}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[10px]" style={{color: S.ms}}>暂无 provider，请添加</p>
          )}

          {availableProviders.length > 0 && (
            <div className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
              <h3 className="text-[11px] font-medium mb-2" style={{color: S.ms}}>添加 Provider</h3>
              <div className="flex flex-col gap-1.5">
                <select value={selProvider} onChange={e => setSelProvider(e.target.value)} className="text-[10px] px-2 py-1.5 rounded outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}}>
                  <option value="">选择 provider</option>
                  {availableProviders.map(p => <option key={p.name} value={p.name}>{p.name} — {p.url}</option>)}
                </select>
                <input placeholder="API Key" value={apiKey} onChange={e => setApiKey(e.target.value)} className="text-[10px] px-2 py-1 rounded outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}} />
                <button onClick={addProvider} className="text-[10px] px-3 py-1 rounded mt-1" style={{backgroundColor: S.d, color: S.b}}>添加</button>
              </div>
            </div>
          )}
          {msg && <span className="text-[10px]" style={{color: msg.includes("失败") ? "#c64545" : S.m}}>{msg}</span>}
        </div>
      )}

      {tab === "tasks" && (
        <div className="flex flex-col gap-3">
          {Object.keys(editProviders).length === 0 && (
            <p className="text-[10px]" style={{color: S.ms}}>请先在 Provider 管理中添加 provider</p>
          )}
          <div className="flex flex-col gap-2">
            {Object.entries(TASK_LABELS).map(([taskType, label]) => {
              const binding = editTaskModels[taskType] || {provider: "", model: ""};
              const models_ = providerModels(binding.provider);
              return (
                <div key={taskType} className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
                  <span className="text-[11px] font-medium" style={{color: S.i}}>{label}</span>
                <div className="text-[9px] mt-0.5" style={{color: S.ms}}>{TASK_HINTS[taskType]}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <select value={binding.provider} onChange={e => updateTask(taskType, e.target.value, "")} className="text-[10px] px-1 py-0.5 rounded flex-1 outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}}>
                      <option value="">选择 provider</option>
                      {Object.keys(editProviders).map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <div className="relative flex-1">
                      <button onClick={() => setOpenModelPicker(openModelPicker === taskType ? null : taskType)} className="w-full text-left text-[10px] px-2 py-1 rounded flex items-center justify-between outline-none" style={{border: `1px solid ${S.h}`, color: binding.model ? S.i : S.ms, backgroundColor: S.c}}>
                        <span>{binding.model || "选择模型"}</span>
                        <span className="text-[8px]" style={{color: S.ms}}>▼</span>
                      </button>
                      {openModelPicker === taskType && (<>
                        <div className="fixed inset-0 z-[5]" onClick={() => setOpenModelPicker(null)}/>
                        <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded border shadow-sm z-10" style={{borderColor: S.h, backgroundColor: S.c}}>
                          {models_.map(m => (
                            <button key={m.name} onClick={() => { updateTask(taskType, binding.provider, m.name); setOpenModelPicker(null); }}
                              className="w-full text-left px-2 py-1.5 hover:brightness-95" style={{backgroundColor: binding.model === m.name ? S.s : S.c}}>
                              <div className="text-[10px]" style={{color: S.i}}>{m.name}</div>
                              <div className="text-[9px]" style={{color: S.ms}}>{capLabel(m.capabilities)}</div>
                            </button>
                          ))}
                        </div>
                      </>)}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex gap-2 items-center">
            <button onClick={saveTasks} className="text-xs px-3 py-1 rounded-md" style={{backgroundColor: S.r, color: S.w, cursor: "pointer"}}>保存配置</button>
            {msg && <span className="text-[10px]" style={{color: msg.includes("失败") ? "#c64545" : S.m}}>{msg}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
