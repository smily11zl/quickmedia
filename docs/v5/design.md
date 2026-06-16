# QuickMedia v5 技术方案

> 基于 v4 技术架构的增量设计。

## 变更范围

| 模块 | 变更类型 | 说明 |
|------|---------|------|
| prompt_config.py | 新增 | PromptConfig 类，管理 prompts.yaml 读写和自动同步 |
| ai.py | 修改 | VisionAnalyzer/TextAnalyzer JSON 解析 + Ollama `think` 参数 |
| ai_worker.py | 修改 | AIWorker 创建 PromptConfig 实例传入分析器 |
| server.py | 扩展 | GET/PUT /api/prompts，重新分析清旧标签，AI 状态增强 |
| App.tsx | 扩展 | 设置面板 AI 分析 Tab + 按钮交互优化 |

## PromptConfig 类

```python
class PromptConfig:
    def __init__(self, config_dir: str):
        self._path = os.path.join(config_dir, "prompts.yaml")
        self._ensure_defaults()

    def _ensure_defaults(self):
        """首次创建，后续启动同步 default/system_format/presets，保留 custom"""
        if not exists: 创建
        else: 更新系统字段，保留用户 custom

    def get_prompt(self, analysis_type: str) -> str:
        """custom 非空用 custom，否则用 default，均追加 system_format"""
        ...

    def get_config(self) -> dict:
        """返回完整配置，供 API 读取"""
        ...

    def update_custom(self, analysis_type: str, custom: str):
        """写入 custom 字段，API PUT 时调用"""
        ...

## AI 调用链

```
VisionAnalyzer.analyze(path)
  → _call_ollama(prompt, img_b64)
      → Ollama /api/chat (think: true/false 按需)
      → [Ollama prompt] 日志输出请求
      → [Ollama] 日志输出响应
  → _parse_response(content)
      → _extract_json() 处理 markdown/前后文字
      → json.loads() 解析
      → 失败返回空 dict
```

## Server 变更

- `CASE WHEN` 替代 `COALESCE`：检查 ai_queue | ai_description | ai_summary
- 重新分析端点：DELETE asset_tags WHERE source='auto' 清除旧标签
- `think` 参数：顶层字段（非 options 内）
```

## API 端点

### GET /api/prompts

```json
{
  "vision": {
    "system_format": "...",
    "default": "...",
    "custom": "用户当前内容或空字符串",
    "presets": [{"name": "摄影", "content": "..."}, ...]
  },
  "text": { ... },
  "speech": { ... },
  "video_summary": { ... }
}
```

### PUT /api/prompts

```json
{
  "type": "vision",
  "custom": "用户编辑的新 prompt 内容"
}
```

## 前端变更

### 设置面板结构

```
┌─ 设置 ───────────────────────┐
│ Ollama URL          [______] │
│ 模型                [______] │
│ 视频采样帧数        [__]     │
│ 请求超时(秒)        [___]    │
│ [检测连接] [保存]            │
├─ AI 分析 ────────────────────┤
│ [图片] [文档] [语音] [视频]   │ ← Tab 切换
│                              │
│ 预设模板:                    │
│ [通用] [摄影] [设计] [宠物] [人物] │
│                              │
│ 自定义 Prompt:               │
│ ┌──────────────────────┐     │
│ │ (textarea)           │     │
│ └──────────────────────┘     │
│ [保存 Prompt]                │
└──────────────────────────────┘
```
