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
