# V17 PRD

## v17 — 多语言国际化 (i18n) ✅ 已完成

### Problem Statement

QuickMedia 全量 UI 和 prompt 模板均为简体中文，非中文用户上手困难。用户界面、错误提示、聚合/搜索模式名称等均需支持英文切换。

### Solution

接入 react-i18next 实现前端多语言，DEFAULT_PROMPTS 拆分为中英两套，后端消息统一走结构化字段由前端翻译。

### Key Features

- 前端 UI 支持中/英切换，首次根据浏览器语言自动选择
- 10 个 prompt 类型的中英文 default 模板
- 设置面板"基础"Tab 加语言选择下拉框
- README 英文默认 + README.zh.md 中文版，互相链接
- 后端 API 不输出用户可见文字，全部走前端翻译

### User Stories

1. 英文用户打开 QuickMedia，看到英文界面，无需翻译
2. 中文用户切换语言后，所有按钮/提示立即变为中文
3. 切换语言不影响已有的自定义 prompt 配置
4. GitHub 上 README 默认为英文，中文用户可点链接切换

### Implementation Decisions

- react-i18next + i18next-browser-languagedetector
- DEFAULT_PROMPTS_ZH / DEFAULT_PROMPTS_EN 在 prompt_config.py 并存
- PromptConfig 初始化根据语言选 default
- 切换语言时只更新 default 字段，custom 保留不变
- 后端消息用结构化 key（已有 detail/warning），前端按语言翻译

### Out of Scope

- AI 生成内容不翻译
- 繁体中文字体不单独支持
- 不内置自动翻译功能

### Testing Decisions

- 前端：切换语言后 UI 文字正确渲染
- 后端：DEFAULT_PROMPTS_ZH / DEFAULT_PROMPTS_EN 结构一致
- API：PromptConfig 不同语言加载不同 default
