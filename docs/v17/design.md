# V17 技术设计 — 多语言国际化

## i18n 架构

```
frontend/src/
  i18n.ts              ← i18next 初始化 + LanguageDetector
  locales/
    zh.ts              ← 中文翻译
    en.ts              ← 英文翻译
  main.tsx             ← import './i18n'
  App.tsx              ← {t("key")} 替换硬编码中文
  NodePanel.tsx
  SettingsModal.tsx
  ...
```

## locale 文件结构

```typescript
// node 模块示例
"node": {
  "add_assets": "手动添加素材",     // zh
  "add_assets": "Add Assets",        // en
  "remove_assets": "手动移除素材",
  "analyze_append": "分析追加到此节点",
  "assigned_to": "已分配到节点：{{name}}",
  "already_has": "节点{{name}}已收录{{filename}}",
}
```

## 语言检测策略

1. 首次访问 → navigator.language → zh/zh-CN/zh-TW... → "zh"，其他 → "en"
2. 用户手动选择 → 存 localStorage key "language"
3. 后续访问 → 读 localStorage

## 后端消息 key 协议

| 原中文 | key |
|--------|-----|
| 聚合任务需要配置模型 | `error.aggregation_no_model` |
| 已有聚合任务进行中 | `error.aggregation_running` |
| 节点不存在 | `error.node_not_found` |
| 节点名不能为空 | `error.node_name_required` |
| 语义搜索失败 | `error.semantic_failed` + `{provider, error}` 插值 |

前端统一处理：
```tsx
.catch(d => setToast({message: t(`error.${d.detail}`, d.params)}))
```

## Prompt 双语言配置

```python
# prompt_config.py
DEFAULT_PROMPTS_ZH = { "vision": {...}, ... }
DEFAULT_PROMPTS_EN = { "vision": {...}, ... }

def get_default_prompts(lang="zh"):
    return DEFAULT_PROMPTS_ZH if lang == "zh" else DEFAULT_PROMPTS_EN
```

PromptConfig._load() 根据语言选 default，custom 不变。

## 文件变更清单

| 文件 | 变更 |
|------|------|
| `frontend/package.json` | +3 deps |
| `frontend/src/i18n.ts` | 新增 |
| `frontend/src/locales/zh.ts` | 新增 |
| `frontend/src/locales/en.ts` | 新增 |
| `frontend/src/main.tsx` | +import |
| `frontend/src/App.tsx` | 80+ 处 t() |
| `frontend/src/NodePanel.tsx` | 40+ 处 t() |
| `frontend/src/SettingsModal.tsx` | 20+ 处 t() |
| `frontend/src/ModelManager.tsx` | t() labels |
| `frontend/src/AddAssetModal.tsx` | t() title |
| `frontend/src/GraphView.tsx` | t() unassigned |
| `quickmedia/prompt_config.py` | DEFAULT_PROMPTS 拆中英 |
| `quickmedia/aggregation/api.py` | detail key |
| `quickmedia/aggregation/core.py` | error key |
| `quickmedia/mcp_server.py` | error key |
| `quickmedia/api/server.py` | warning 结构化 |
| `README.md` | → 英文 |
| `README.zh.md` | 新增 |
| `scripts/setup.sh` | → 英文 |
| `index.html` | title |
