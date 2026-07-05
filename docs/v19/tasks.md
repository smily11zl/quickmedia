# V19 任务切片

> 5 切片，全部完成。✅

---

### s1: models.yaml 新增 12 个模型

**类型**: AFK  
**阻塞**: 无

**内容**:
- `quickmedia/models.yaml` OpenRouter section 新增 Claude/GPT/Gemini/Whisper/ASR 共 12 个模型
- 每个模型标注 capabilities（image/video/text/document/audio/embedding）
- 现有 openrouter 同名模型 capabilities 补全缺失字段

**验证**: 启动服务 → ModelManager 下拉可见新模型名

---

### s2: speech → speech_summary 重命名

**类型**: AFK  
**阻塞**: s1

**内容**:
- `config.py`: task_models.speech → speech_summary 自动迁移
- `ai_worker.py`: _get_adapter("speech") → _get_adapter("speech_summary")
- `ModelManager.tsx`: TASK_LABELS/TASK_HINTS speech → speech_summary
- `locale`: 更新中英文标签("语音分析"→"语音总结")
- 旧 scanner enqueue 代码不在此切片（Worker 内部引用）

**验证**: ModelManager 任务 Tab 显示 "语音总结" 无 "speech"

---

### s3: transcribe 任务 + Whisper provider

**类型**: AFK  
**阻塞**: s1

**内容**:
- `config.py`: task_models.transcribe 默认配置
- `ModelManager.tsx`: 新增 transcribe 任务项 + Whisper provider 项（开关+测试按钮）
- `models.yaml`: Whisper provider 新增开/关配置
- `locale`: transcribe/whisper 相关文案
- `ai_worker.py`: _get_adapter("transcribe") 支持 whisper provider

**验证**: ModelManager 显示 transcribe 任务 + Whisper provider 可开关

---

### s4: 模型按能力过滤

**类型**: AFK  
**阻塞**: s1

**内容**:
- `ModelManager.tsx`: 任务 Tab 模型下拉按 capabilities 过滤
- capabilities→task 映射函数（image+video→vision, audio→transcribe, text→text/speech_summary等）
- 测试：切换任务后下拉仅显示支持该能力的模型

**验证**: vision 任务不下显纯 text 模型，transcribe 仅显 audio 模型

---

### s5: AIWorker transcribe 适配器化 + 视频音频提取

**类型**: AFK  
**阻塞**: s3, s4

**内容**:
- `ai_worker.py`: _process_transcribe 从硬编码 TranscriptionAnalyzer 改为 _get_adapter("transcribe")
- 视频文件：ffmpeg 提取 MP3 临时文件 → API 调用 → 清理
- 音频文件：直接传原文件
- 本地 whisper：保持原有 faster-whisper 路径（无临时文件）
- API whisper：通过 OpenAI 兼容适配器调 OpenRouter
- 成功后写 transcript → 继续 speech_summary 分析

**验证**: 扫描视频/音频 → Worker 转录成功 → speech_summary 生成标签
