# V17 任务完成报告

> 状态：全部完成 ✅

## 切片概览

| # | 内容 | 文件 | 测试点 | 状态 |
|---|------|------|--------|------|
| s1 | i18n 模块 + locale | i18n.ts, zh.ts, en.ts | 中英同构校验, 嵌套 key 查找 | ✅ |
| s2 | 语言选择器 | SettingsModal.tsx | 下拉框, cookie 持久化, reload | ✅ |
| s3 | App.tsx | App.tsx | 搜索/筛选/详情/按钮/aiT | ✅ |
| s4 | NodePanel | NodePanel.tsx, ConfirmModal.tsx | 聚合按钮/右键菜单/节点树/弹窗 | ✅ |
| s5 | SettingsModal | SettingsModal.tsx | 四 Tab/prompt 类型/变量/文件夹 | ✅ |
| s6 | ModelManager | ModelManager.tsx | TASK_LABELS/HINTS/Toast/capability | ✅ |
| s7a | AddAssetModal | AddAssetModal.tsx | 弹窗标题/搜索/全选/确认 | ✅ |
| s7b | GraphView | GraphView.tsx | TYPE_LABELS/图例/未分配 | ✅ |
| s7c | SimilarPanel | SimilarPanel.tsx | 标题/关闭/搜索中/未找到 | ✅ |
| s8 | 后端消息 key 化 | api/server.py, aggregation/*, ai_worker.py, mcp_server.py | error key → 前端 t("error.xxx") | ✅ |
| s9 | DEFAULT_PROMPTS 拆分 | prompt_config.py | ZH/EN 双版 10 种 prompt | ✅ |
| s10 | PromptConfig 语言加载 | prompt_config.py, ai.py, ai_worker.py | cookie 读写, middleware, threading | ✅ |
| s11 | 文档 + CLI | README.md, README.zh.md, setup.sh, cli.py, index.html | 双语文档, 英文默认, 页面标题 | ✅ |

## 技术决策

- **i18n 框架**: react-i18next + i18next（标准方案，I18nextProvider 包裹 App）
- **语言检测**: cookie `qm_lang` → localStorage → navigator
- **语言切换**: `document.cookie` + `i18n.changeLanguage()` + `window.location.reload()`
- **Locale 结构**: 嵌套 key，`t("module.sub_key")`，21 个模块 132+ keys
- **Prompt 多语言**: DEFAULT_PROMPTS_ZH/EN 双版，`get_prompt()` 动态覆盖
- **后端消息**: error key → 前端 `error.` namespace 映射，middleware 读 cookie
- **命名冲突**: SettingsModal `.map(t => ...)` 循环变量覆盖 → 改用 `{ t: translate }`
- **模块常量**: TASK_LABELS/TASK_HINTS 从模块级移入组件内使用 `t()`
- **CLI 帮助**: 默认英文，`--lang zh` 看中文

## 关键修复记录

- `title="在 Finder 中打开"` → `title={t(...)}`（属性需 `{}` 包裹）
- YAML 缓存 `presets` 每次从语言默认同步
- `groupMap[g.k]` → 对象映射（prompt type key 代替中文字符串）
- `pt?.startsWith` 防空（undefined 导致崩溃）
- 三元内 `t()` 无需 `{}`（`{loading ? t(...) : text}`）
- `aiT` 模块级函数 → `import i18n` 直接调用 `i18n.t()`
- PromptConfig `get_prompt()` 默认用 `self.language`
- `_console_log` 删除时连 `if` 块一起删（空块语法错）

### Hotfix
- s3 遗留：空状态 `t("detail.empty_hint")` 缺 JSX `{}`，显示为 raw key → 已修复
