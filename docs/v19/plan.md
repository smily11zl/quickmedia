# V19 — 模型扩展 + 语音识别重构

> 状态：grill-me ✅ → grill-with-docs ✅ → to-prd ✅ → to-issues ✅ → tdd ✅ → **已完成**

## 功能

### 1. 新增 OpenRouter 模型
- Claude Opus 4.8/4.7、Sonnet 4.6/5、Haiku 4.5
- GPT-5.5 / GPT-5.4
- Gemini 3 flash / 3.5 flash
- Whisper Large V3 / V3 Turbo
- Qwen3 ASR Flash

### 2. 语音识别可配置
- 新增 transcribe 任务，支持远端 API（OpenRouter）和本地 Whisper 引擎
- speech → speech_summary 重命名（文本总结任务）
- Whisper provider：本地 faster-whisper 引擎，开关+测试按钮

### 3. 模型按能力过滤
- ModelManager 任务 Tab 仅显示支持该任务能力的模型
- capabilities→task 映射

## 决策记录

| # | 决策 | 结论 |
|---|------|------|
| Q1 | 新增模型 capabilities | 按同系列规则分类 |
| Q2 | Haiku 4.5 能力 | image+text+document |
| Q3 | 语音模型 provider | A：放现有 provider |
| Q4 | 模型过滤范围 | models.yaml 已有 |
| Q5 | 任务重命名+新增 | speech→speech_summary + transcribe |
| Q6 | 过滤逻辑 | provider 全显，模型按能力过滤 |
| Q7 | Whisper provider | B：本地 faster-whisper，开关+测试 |
| Q8 | 音频提取 | 视频转录前 ffmpeg 提取 MP3 |
