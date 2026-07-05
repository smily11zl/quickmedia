# V19 设计文档

## 1. 新增模型

### models.yaml 扩展（OpenRouter）

```yaml
openrouter:
  models:
    # Claude 系列
    - name: anthropic/claude-opus-4.8
      capabilities: { image: [...], text: [], document: [...] }
    - name: anthropic/claude-opus-4.7
      capabilities: { image: [...], text: [], document: [...] }
    - name: anthropic/claude-sonnet-4.6
      capabilities: { image: [...], text: [], document: [...] }
    - name: anthropic/claude-sonnet-5
      capabilities: { image: [...], text: [], document: [...] }
    - name: anthropic/claude-haiku-4.5
      capabilities: { image: [...], text: [], document: [...] }
    # GPT 系列
    - name: openai/gpt-5.5
      capabilities: { image: [...], text: [], document: [...] }
    - name: openai/gpt-5.4
      capabilities: { image: [...], text: [], document: [...] }
    # Gemini 系列
    - name: google/gemini-3-flash
      capabilities: { image: [...], video: [...], audio: [...], text: [], document: [...] }
    - name: google/gemini-3.5-flash
      capabilities: { image: [...], video: [...], audio: [...], text: [], document: [...] }
    # 语音识别
    - name: openai/whisper-large-v3
      capabilities: { audio: [MP3, WAV, FLAC, M4A] }
    - name: openai/whisper-large-v3-turbo
      capabilities: { audio: [MP3, WAV, FLAC, M4A] }
    - name: qwen/qwen3-asr-flash
      capabilities: { audio: [MP3, WAV, FLAC, M4A] }
```

## 2. 任务重命名：speech → speech_summary

### config.yaml task_models 变化

```yaml
task_models:
  speech_summary:          # 原 speech，自动迁移
    provider: openrouter
    model: anthropic/claude-haiku-4.5
  transcribe:              # 新增
    provider: whisper
    model: small
```

### ai_worker.py 自适应

```python
# _get_adapter("speech") → _get_adapter("speech_summary")
adapter = self._get_adapter("speech_summary")
```

## 3. 语音识别适配器

### _process_transcribe 重构

```python
def _process_transcribe(self, asset_id: int, path: str) -> None:
    # 检测是否需要提取音频
    asset_type = self.db.execute("SELECT asset_type FROM assets WHERE id=?", (asset_id,))[0]["asset_type"]
    if asset_type == "video":
        import tempfile, subprocess, os
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        subprocess.run(["ffmpeg", "-i", path, "-vn", "-acodec", "libmp3lame", "-y", tmp.name], capture_output=True)
        path = tmp.name

    adapter = self._get_adapter("transcribe")
    if adapter.provider_type == "whisper":
        # 本地 faster-whisper
        transcript = transcribe_local(path)
    else:
        # API 调用
        transcript = transcribe_api(adapter, path)

    # 清理临时文件
    if asset_type == "video":
        os.unlink(tmp.name)
    ...
```

## 4. Whisper Provider

- 无 URL/API Key
- 仅 `enabled: true/false` + `model_size: small` 配置
- 测试按钮：尝试加载 whisper model 并做短样本转录

## 5. 模型能力过滤

### ModelManager 过滤映射

| 任务 | 显示 models 满足 |
|------|-----------------|
| vision | image 或 video |
| text | text 或 document |
| speech_summary | text 或 document |
| transcribe | audio |
| video_summary | text 或 document |
| embedding | embedding |
| search_ai | text 或 document |
| aggregation | text 或 document |

### capabilities 到任务的映射函数

```python
CAPABILITY_TO_TASK = {
    "image": ["vision"],
    "video": ["vision"],
    "text": ["text", "speech_summary", "video_summary", "search_ai", "aggregation"],
    "document": ["text", "speech_summary", "video_summary", "search_ai", "aggregation"],
    "audio": ["transcribe"],
    "embedding": ["embedding"],
}
```

## 6. 向后兼容

- `task_models.speech` 自动重命名为 `speech_summary`（V19 迁移）
- _get_adapter 同时检查 "speech" 和 "speech_summary" 配置
