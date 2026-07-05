import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import ConfirmModal from "./ConfirmModal";

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


const BUILTIN_PROVIDERS: ProviderInfo[] = [
  {name: "ollama", url: "http://localhost:11434/v1"},
  {name: "openrouter", url: "https://openrouter.ai/api/v1"},
  {name: "deepseek", url: "https://api.deepseek.com/v1"},
  {name: "openai", url: "https://api.openai.com/v1"},
  {name: "minimax", url: "https://api.minimaxi.com/v1"},
];

function saveProviders(providers: Record<string, ProviderData>, taskModels: Record<string, TaskBinding>): Promise<boolean> {
  return fetch("/api/providers", {method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify({providers, task_models: taskModels})})
    .then(r => r.json())
    .then(r => r.ok === true);
}

export default function ModelManager({ onClose, standalone = true, onModelsSaved, initialTab }: { onClose: () => void; standalone?: boolean; onModelsSaved?: () => void; initialTab?: string }) {
  const [tab, setTab] = useState<"providers" | "tasks">((initialTab as any) || "providers");
  const [selProvider, setSelProvider] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [models, setModels] = useState<Record<string, {name:string;capabilities:Record<string,string[]>}[]>>({});
  const [testStatus, setTestStatus] = useState<Record<string, string>>({});
  const [whisperStatus, setWhisperStatus] = useState<string>("");
  const { t } = useTranslation();

  const TASK_LABELS: Record<string, string> = {
    vision: t("model.task_vision"),
    text: t("model.task_text"),
    speech_summary: t("model.task_speech"),
    transcribe: t("model.task_transcribe"),
    video_summary: t("model.task_video_summary"),
    embedding: t("model.task_embedding"),
    search_ai: t("model.task_search_ai"),
    aggregation: t("model.task_aggregation"),
  };

  const TASK_HINTS: Record<string, string> = {
    vision: t("model.hint_vision"),
    text: t("model.hint_text"),
    speech_summary: t("model.hint_speech"),
    transcribe: t("model.hint_transcribe"),
    video_summary: t("model.hint_video_summary"),
    embedding: t("model.hint_embedding"),
    search_ai: t("model.hint_search_ai"),
    aggregation: t("model.hint_aggregation"),
  };
  const [msg, setMsg] = useState("");
  const [editUrl, setEditUrl] = useState<string | null>(null);
  const [editUrlVal, setEditUrlVal] = useState("");
  const [openModelPicker, setOpenModelPicker] = useState<string | null>(null);
  const [editProviders, setEditProviders] = useState<Record<string, ProviderData>>({});
  const [editTaskModels, setEditTaskModels] = useState<Record<string, TaskBinding>>({});
  const [initTaskModels, setInitTaskModels] = useState<Record<string, TaskBinding>>({});
  const [confirmDeleteProvider, setConfirmDeleteProvider] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/providers").then(r => r.json()).then(d => {
      setEditProviders({...(d.providers || {})});
      setEditTaskModels({...(d.task_models || {})});
      setInitTaskModels({...(d.task_models || {})});
      const m: Record<string, {name:string;capabilities:Record<string,string[]>}[]> = {};
      Object.keys(d.providers || {}).forEach((p: string) => {
        fetch(`/api/providers/${p}/models`).then(r => r.json()).then(r2 => {
          m[p] = r2.models || [];
          setModels({...m});
        }).catch(() => {});
      });
      fetch("/api/providers/whisper/models").then(r => r.json()).then(r2 => {
        m["whisper"] = r2.models || [];
        setModels({...m});
      }).catch(() => {});
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
      setMsg(ok ? t("model.added") : t("model.add_failed"));
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
    fetch(`/api/providers/${selProvider}/models`).then(r => r.json()).then(r2 => {
      setModels(prev => ({...prev, [selProvider]: r2.models || []}));
    }).catch(() => {});
    setSelProvider("");
    setApiKey("");
  };

  const removeProvider = (name: string) => {
    setConfirmDeleteProvider(name);
  };

  const doRemoveProvider = () => {
    if (!confirmDeleteProvider) return;
    const updated = {...editProviders};
    delete updated[confirmDeleteProvider];
    setEditProviders(updated);
    const tm = {...editTaskModels};
    for (const t of Object.keys(tm)) {
      if (tm[t].provider === confirmDeleteProvider) tm[t] = {provider: "", model: ""};
    }
    setEditTaskModels(tm);
    saveProviders(updated, tm).then(ok => {
      setMsg(ok ? t("model.deleted") : t("model.delete_failed"));
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
    setConfirmDeleteProvider(null);
  };

  const saveUrl = (name: string) => {
    if (!editUrlVal.trim()) return;
    const updated = {...editProviders, [name]: {...editProviders[name], url: editUrlVal.trim()}};
    setEditProviders(updated);
    setEditUrl(null);
    saveProviders(updated, editTaskModels).then(ok => {
      setMsg(ok ? t("model.saved") : t("model.save_failed"));if(ok&&onModelsSaved)onModelsSaved();
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
  };

  const updateTask = (taskType: string, provider: string, model: string) => {
    setEditTaskModels({...editTaskModels, [taskType]: {provider, model}});
  };

  const saveTasks = () => {
    saveProviders(editProviders, editTaskModels).then(ok => {
      setMsg(ok ? t("model.saved") : t("model.save_failed"));if(ok&&onModelsSaved)onModelsSaved();
      if (ok) setInitTaskModels({...editTaskModels});
      setTimeout(() => setMsg(""), ok ? 2000 : 3000);
    });
  };

  const testProvider = (name: string, url: string) => {
    setTestStatus({...testStatus, [name]: t("model.testing")});
    fetch("/api/providers/test", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({provider: name, url})})
      .then(r => r.json())
      .then(r => setTestStatus({...testStatus, [name]: r.ok ? t("model.connected") : (r.error || t("model.connection_failed"))}))
      .catch(() => setTestStatus({...testStatus, [name]: t("model.connection_failed")}));
  };


  const testWhisper = () => {
    setWhisperStatus(t("model.testing"));
    fetch("/api/providers/whisper/test")
      .then(r => r.json())
      .then(r => setWhisperStatus(r.ok ? t("model.connected") : (r.error || t("model.connection_failed"))))
      .catch(() => setWhisperStatus(t("model.connection_failed")));
  };

  const providerModels = (provider: string, capability?: string): {name:string;capabilities:Record<string,string[]>}[] => {
    const all = models[provider] || [];
    if (!capability) return all;
    return all.filter(m => {
      const caps = m.capabilities || {};
      return capability in caps;
    });
  };

  const TASK_CAPABILITY: Record<string, string> = {
    vision: "image",
    text: "text",
    speech_summary: "text",
    transcribe: "audio",
    video_summary: "text",
    embedding: "embedding",
    search_ai: "text",
    aggregation: "text",
  };

  const capLabel = (caps: Record<string,string[]>) => {
    const labels: Record<string,string> = {image:t("model.cap_image"), text:t("model.cap_text"), audio:t("model.cap_audio"), document:t("model.cap_document"), video:t("model.cap_video"), embedding:t("model.cap_embedding")};
    if (!caps || typeof caps !== 'object') return t("model.cap_general");
    const parts: string[] = [];
    for (const [k, fmts] of Object.entries(caps)) {
      const label = labels[k] || k;
      if (fmts && fmts.length > 0) parts.push(label + "(" + fmts.join(",") + ")");
      else parts.push(label);
    }
    return parts.join(" / ") || t("model.cap_general");
  };

  const tasksDirty = JSON.stringify(editTaskModels) !== JSON.stringify(initTaskModels);

  return (
    <div className={`w-full p-4 flex flex-col gap-4 ${standalone ? 'overflow-y-auto' : ''}`} style={{borderColor: S.h, backgroundColor: S.c}}>
      {standalone && (
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium" style={{color: S.i}}>{t("model.title")}</h2>
          <button onClick={onClose} className="text-xs px-2 py-1 rounded" style={{color: S.ms, backgroundColor: S.s}}>✕ {t("model.close")}</button>
        </div>
      )}

      <div className="flex gap-1 p-0.5 rounded-md" style={{backgroundColor: S.s}}>
        <button onClick={() => setTab("providers")} className="flex-1 text-xs py-1 rounded" style={{backgroundColor: tab === "providers" ? S.c : "transparent", color: tab === "providers" ? S.i : S.ms}}>{t("model.tab_providers_label")}</button>
        <button onClick={() => setTab("tasks")} className="flex-1 text-xs py-1 rounded" style={{backgroundColor: tab === "tasks" ? S.c : "transparent", color: tab === "tasks" ? S.i : S.ms}}>{t("model.tab_tasks")}</button>
      </div>

      {tab === "providers" && (
        <div className="flex flex-col gap-3">
          {availableProviders.length > 0 && (
            <div className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
              <h3 className="text-[11px] font-medium mb-2" style={{color: S.ms}}>{t("model.add_provider")}</h3>
              <div className="flex gap-1.5">
                <select value={selProvider} onChange={e => setSelProvider(e.target.value)} className="text-[10px] px-2 py-1.5 rounded flex-1 outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}}>
                  <option value="">{t("model.select_provider")}</option>
                  {availableProviders.map(p => <option key={p.name} value={p.name}>{p.name} — {p.url}</option>)}
                </select>
                <input placeholder="API Key" value={apiKey} onChange={e => setApiKey(e.target.value)} className="text-[10px] px-2 py-1 rounded flex-1 outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}} />
                <button onClick={() => addProvider()} className="text-[10px] px-3 py-1 rounded" style={{backgroundColor: S.d, color: S.b}}>{t("model.add")}</button>
              </div>
            </div>
          )}

          {Object.keys(editProviders).length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {/* Whisper local provider */}
              <div className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium" style={{color: S.i}}>Whisper</span>
                  <div className="flex gap-1">
                    <button onClick={() => testWhisper()} className="text-[10px] px-2 py-0.5 rounded" style={{backgroundColor: S.d, color: S.b}}>{t("model.whisper_test")}</button>
                  </div>
                </div>
                {whisperStatus && <p className="text-[10px] mt-0.5" style={{color: whisperStatus === t("model.connected") ? "#5db872" : whisperStatus === t("model.testing") ? S.m : "#c64545"}}>{whisperStatus}</p>}
              </div>
              {Object.entries(editProviders).map(([name, p]) => (
                <div key={name} className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium" style={{color: S.i}}>{name}</span>
                    <div className="flex gap-1">
                      <button onClick={() => testProvider(name, p.url)} className="text-[10px] px-2 py-0.5 rounded" style={{backgroundColor: S.d, color: S.b}}>{t("model.test")}</button>
                      {name !== "ollama" && (
                        <button onClick={() => removeProvider(name)} className="text-[10px] px-2 py-0.5 rounded" style={{backgroundColor: S.rb, color: S.r}}>{t("model.remove")}</button>
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
                  {testStatus[name] && <p className="text-[10px] mt-0.5" style={{color: testStatus[name] === t("model.connected") ? "#5db872" : testStatus[name] === t("model.testing") ? S.m : "#c64545"}}>{testStatus[name]}</p>}
                </div>
              ))}
            </div>
          )}
          {msg && <span className="text-[10px]" style={{color: msg.includes("失败") ? "#c64545" : S.m}}>{msg}</span>}
        </div>
      )}

      {tab === "tasks" && (
        <div className="flex flex-col gap-3">
          {Object.keys(editProviders).length === 0 && (
            <p className="text-[10px]" style={{color: S.ms}}>{t("model.no_providers")}</p>
          )}
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(TASK_LABELS).map(([taskType, label]) => {
              const binding = editTaskModels[taskType] || {provider: "", model: ""};
              const models_ = providerModels(binding.provider, TASK_CAPABILITY[taskType]);
              return (
                <div key={taskType} className="p-2 rounded-md border" style={{borderColor: S.h, backgroundColor: S.s}}>
                  <span className="text-[11px] font-medium" style={{color: S.i}}>{label}</span>
                <div className="text-[9px] mt-0.5" style={{color: S.ms}}>{TASK_HINTS[taskType]}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <select value={binding.provider} onChange={e => updateTask(taskType, e.target.value, "")} className="text-[10px] px-1 py-0.5 rounded flex-1 outline-none" style={{border: `1px solid ${S.h}`, color: S.i, backgroundColor: S.c}}>
                      <option value="">{t("model.select_provider")}</option>
                      {[...Object.keys(editProviders), "whisper"].map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <div className="relative flex-1">
                      <button onClick={() => setOpenModelPicker(openModelPicker === taskType ? null : taskType)} className="w-full text-left text-[10px] px-2 py-1 rounded flex items-center justify-between outline-none" style={{border: `1px solid ${S.h}`, color: binding.model ? S.i : S.ms, backgroundColor: S.c}}>
                        <span>{binding.provider ? (binding.model || t("model.select_model")) : t("model.select_model")}</span>
                        <span className="text-[8px]" style={{color: S.ms}}>▼</span>
                      </button>
                      {openModelPicker === taskType && (<>
                        <div className="fixed inset-0 z-[5]" onClick={() => setOpenModelPicker(null)}/>
                        <div className="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded border shadow-sm z-10" style={{borderColor: S.h, backgroundColor: S.c}}>
                          {models_.map(m => (
                            <button key={m.name} onClick={() => { updateTask(taskType, binding.provider, m.name); setOpenModelPicker(null); }}
                              className="w-full text-left px-2 py-1.5 hover:brightness-95" style={{backgroundColor: binding.model === m.name ? S.s : S.c}}>
                              <div className="text-[10px]" style={{color: S.i}}>{m.name}</div><div className="text-[8px]" style={{color:S.ms}}>{capLabel(m.capabilities)}</div>
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
            <button onClick={saveTasks} className="text-xs px-3 py-1.5 rounded-md" style={{backgroundColor: tasksDirty ? S.r : S.d, color: tasksDirty ? S.w : S.ms, cursor: tasksDirty ? "pointer" : "default"}}>{t("model.save_config")}</button>
            {msg && <span className="text-[10px]" style={{color: msg.includes("失败") ? "#c64545" : S.m}}>{msg}</span>}
          </div>
        </div>
      )}
      {confirmDeleteProvider && (
        <ConfirmModal
          title={t("model.delete_provider")}
          message={t("model.delete_provider_msg", {name: confirmDeleteProvider})}
          confirmText={t("model.remove")}
          confirmColor="error"
          onConfirm={doRemoveProvider}
          onCancel={() => setConfirmDeleteProvider(null)}
        />
      )}
    </div>
  );
}
