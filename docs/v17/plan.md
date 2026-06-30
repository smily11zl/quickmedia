# V17 开发计划 — 多语言国际化

> 状态：grill-me ✅ → grill-with-docs ✅ → to-prd ✅ → to-issues ✅ → tdd ⬜

## 方案

- 纯 TS i18n 模块：`i18n.t("key")`，零 npm 依赖
- 中英双 locale 文件（zh.ts / en.ts），嵌套 key 结构
- 语言切换：设置面板基础 Tab 下拉框 → `window.location.reload()`
- 每个切片 RED→GREEN→构建→手动测试

## 切片

| # | 内容 | 类型 |
|---|------|------|
| s1 | i18n.ts 模块 + locale 文件 | 前端 |
| s2 | 设置面板语言选择器 | 前端 |
| s3 | App.tsx 搜索区 | 前端 |
| s4 | NodePanel 聚合+操作 | 前端 |
| s5 | SettingsModal Tab+提示词 | 前端 |
| s6 | ModelManager | 前端 |
| s7 | AddAssetModal + GraphView | 前端 |
| s8 | 后端消息 key 化 | 后端 |
| s9 | DEFAULT_PROMPTS 拆分 | 后端 |
| s10 | PromptConfig 语言加载 | 后端 |
| s11 | README + setup.sh + 标题 | 文档 |
