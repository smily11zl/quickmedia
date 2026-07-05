---

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

---

## v18 — AI 状态重构 ✅ 已完成

### Problem Statement

素材的 AI 分析状态（done/processing/pending/failed/cancelled）依赖 `ai_queue` 子查询实时计算，性能差且无法独立管理状态。队列清除、批量删除、Worker 取消等场景缺乏可靠的状态同步。

### Solution

将 `ai_status` 和 `ai_status_updated_at` 作为 `assets` 表字段，消除冗余查询。引入 `PRAGMA user_version` 版本号跳过重复迁移。Worker 双重检查（前/后）防止 AI 分析覆盖取消状态。

### Key Changes

- **DB**: `assets.ai_status` TEXT + `assets.ai_status_updated_at` TEXT, `PRAGMA user_version=18`
- **Worker**: 处理前检查 assets.ai_status, cancelled/不存在则跳过；成功后写 done + 删 ai_queue + enqueue embedding；失败写 failed
- **API**: `_get_db` 线程本地缓存, user_version 跳过迁移；`batch-delete` 复用 `delete_asset_full`；`clear_queue` DELETE FROM ai_queue
- **Frontend**: `aiT()` 5 色状态标签（done/processing/pending/failed/cancelled）；批量选择 + 删除 + 确认弹窗 i18n
- **MCP**: `AssetBasic` 全 19 字段 + `AssetDetail` 含 ai_status，docstring 与模型对齐
- **Scanner**: INSERT 时直接写 ai_status='pending', _auto_tags 在 metadata 提取后用真实 duration
---

## v19 — 模型扩展 + 语音识别重构

### Problem Statement

当前支持的模型有限（OpenRouter 上仅 GPT-4o/mini、Sonnet 4、Haiku 4、Gemini 2.5 等），语音识别硬编码为本地 faster-whisper（不可配置）。用户希望：
1. 使用更强大的模型（Claude Opus/Sonnet 4.6/Sonnet 5、GPT 5.5/5.4、Gemini 3 系列）
2. 语音转文字可选用远端 API（Whisper Large V3/Turbo、Qwen3 ASR）或本地引擎
3. 不同任务的模型选择仅显示支持该任务能力的模型

### Solution

在 models.yaml 增加 OpenRouter 模型（Claude Opus 4.8/4.7、Sonnet 4.6/5、Haiku 4.5、GPT 5.5/5.4、Gemini 3 flash/3.5 flash、Whisper Large V3/V3 Turbo、Qwen3 ASR Flash）。每个模型标注 capabilities（image/video/text/document/audio/embedding）。

ModelManager 按任务过滤模型——vision 任务仅显 image/video 模型，transcribe 仅显 audio 模型。speech 任务重命名为 speech_summary（语音总结）。

新增 Whisper provider 类型（本地 faster-whisper 引擎），仅需开关+测试按钮。AIWorker 的 transcribe 任务通过适配器调用配置的 provider+model 进行语音转文字。

### User Stories

1. 作为用户，我想要在设置面板中看到最新 Claude/GPT/Gemini 模型，以便选用最先进的分析能力
2. 作为用户，我想要 vision 任务只显示支持图片的模型，避免选到纯文本模型导致失败
3. 作为用户，我想要语音转文字支持 OpenRouter 的 Whisper/Qwen ASR API，以便处理超长音频
4. 作为用户，我想要保持本地 Whisper 可用，以便离线时仍能转录
5. 作为用户，我想要语音总结和语音转文字分开配置，以便对两阶段分别优化模型选择

### Implementation Decisions

- **models.yaml 扩展**：OpenRouter 下新增 12 个模型，各带 capabilities 标注
- **任务重命名**：config.task_models.speech → speech_summary（向后兼容自动迁移）
- **新增 transcribe 任务**：config.task_models.transcribe，绑定 provider+model
- **Whisper provider**：新增 provider 类型，无 URL/Key，仅 switch + test 按钮
- **模型过滤**：ModelManager 下拉按 capabilities 过滤（vision→image+video，text→text+document，transcribe→audio，embedding→embedding）
- **AIWorker 适配**：_process_transcribe 通过 adapter 调 transcribe，不再硬编码
- **向后兼容**：speech→speech_summary 自动迁移，旧配置不失

### Testing Decisions

- 最高 seam：API 层测试 task_models 配置读写
- Worker 层：mock adapter 的 transcribe/speech_summary 方法，测试流程完整性
- 前端：测试 ModelManager 过滤逻辑（不同任务选模型下拉内容）
- 不测：真实 Whisper/API 调用、网络连通性

### Out of Scope

- 本地 whisper 模型下载管理
- 远端 ASR API 的性能对比
- 流式语音识别
- 自定义模型输入（仅 models.yaml 已有模型可选）

---

## v19 — 模型扩展 + 语音识别重构 ✅ 已完成

### Problem Statement

OpenRouter 支持的模型有限（仅 GPT-4o/mini、Sonnet 4 等），语音识别硬编码为本地 faster-whisper 不可配置，任务模型选单不按能力过滤。

### Solution

1. **新增 14 个模型**（OpenRouter 12 + OpenAI 2）：Claude Opus 4.7/4.8、Sonnet 4.6/5、Haiku 4.5、GPT-5.5/5.4、Gemini 3 Flash/3.5 Flash、Whisper V3/Turbo、Qwen ASR Flash
2. **模型按能力过滤**：任务 Tab 仅显示支持该能力的模型（transcribe→audio, vision→image, 其余→text）
3. **语音识别可配置**：新增 transcribe 任务 + Whisper provider，支持本地 faster-whisper 和 OpenRouter API
4. **speech → speech_summary 重命名**：原"语音分析"改名为"语音总结"，语义更准确
5. **AIWorker 适配器化**：转录根据 provider 路由到本地或 API，视频自动 ffmpeg 提取音频
6. **Prompt 格式统一**：中英文 JSON key 全对齐

### Key Decisions

- Haiku 4.5 → image+text+document（查 OpenRouter 确认）
- Whisper provider → 本地 faster-whisper 引擎，开关+测试按钮，不选模型
- OpenRouter 转录 API → JSON+base64（非 multipart）
- 视频转录 → ffmpeg 提取 MP3 临时文件（API 用），本地 whisper 直传原文件


---

## v20 — 排序修复 + 热度 + 详情页高清缩略图 ✅ 已完成
