# QuickMedia v8 — 向量化 + 语义搜索

> 需求访谈记录。grill-me 时间：2026-06-17。

## 设计决策

### 1. 向量存储：ChromaDB

- `pip install chromadb`，内嵌模式，零配置
- 数据目录：`~/.asset-manager/chroma_db/`
- 不引入外部服务依赖

### 2. Embedding 作为第 5 种分析类型

`task_models` 新增 `embedding`，和 vision / text / speech / video_summary 并列：

```yaml
task_models:
  embedding: {provider: ollama, model: qwen3-embedding:8b}
```

### 3. 自动触发 + 不可切换模型

- 素材入库自动入队（和现有分析行为一致）
- 向量化内容：文件名 + 手动描述 + AI 分析结果（description / summary / tags）
- AI 分析完成后再触发 embedding（依赖 AI 结果）
- 任务配置页提示："⚠️ 创建后勿切换模型，否则需重建全部向量"

### 4. 支持模型

| Provider | 模型 | 能力 |
|----------|------|------|
| Ollama | qwen3-embedding:8b | embedding |
| OpenRouter | qwen/qwen3-embedding-8b | embedding |

### 5. 搜索入口：类型切换

现有搜索框右侧加下拉切换，三种模式：

- **综合** — 关键词匹配 + 语义搜索混合排序
- **语义** — 纯 embedding 向量相似度搜索
- **匹配** — 精确关键词匹配（现有行为）

### 6. 相似素材推荐

- 详情页底部加"🔍 找相似内容"按钮
- 点击 → 弹出叠加层（覆盖当前页面）
- 叠加层：加载状态 → 相似素材网格 / "未找到相似素材"空状态
- 可关闭，返回之前浏览状态

### 7. 搜索结果排序

- 语义搜索：ChromaDB 返回的余弦相似度排序
- 综合模式：匹配结果在前 + 语义结果在后，用分割线隔开

## 涉及文件

| 文件 | 变更 |
|------|------|
| `quickmedia/providers.py` | 新增 `capability_embedding` + embedding 适配器 |
| `quickmedia/ai_worker.py` | Embedding 入队和任务处理 |
| `quickmedia/api/server.py` | 语义搜索 + 相似素材端点；embedding 队列管理 |
| `quickmedia/config.py` | DEFAULT_CONFIG task_models 默认 + ChromaDB 路径 |
| `quickmedia/models.yaml` | 新增 embedding 模型 |
| `pyproject.toml` | 新增 chromadb 依赖 |
| `frontend/src/App.tsx` | 搜索类型切换 + 相似素材叠加层 |
