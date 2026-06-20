# QuickMedia v8 任务拆分

## Slice 8.1 — Embedding 基础设施

**目标：** ChromaDB 存储 + 入库链路打通。

**后端：**
- [ ] `pyproject.toml`: chromadb 依赖
- [ ] `quickmedia/embedding.py`: EmbeddingAdapter（Ollama + OpenAI Compat）+ ChromaDB 初始化/增删查
- [ ] `quickmedia/ai.py`: EmbeddingAnalyzer 类
- [ ] `quickmedia/ai_worker.py`: _process_embedding() 方法；vision/text 完成后自动入队 embedding
- [ ] `quickmedia/database.py`: ai_queue 支持 task_type='embedding'
- [ ] `quickmedia/config.py`: ChromaDB 路径 + 默认 embedding provider

**测试：**
- [ ] ChromaDB CRUD
- [ ] EmbeddingAdapter 调用
- [ ] AIWorker embedding 任务流转

**验证：** 扫描素材 → AI 分析完成 → embedding 自动入库 → ChromaDB 中有向量。

---

## Slice 8.2 — 语义搜索后端

**目标：** 搜索接口支持语义搜索 + 相似推荐。

**后端：**
- [ ] `GET /api/search?q=...&mode=semantic`: 语义搜索端点
- [ ] `GET /api/search?q=...&mode=combined`: 综合搜索端点
- [ ] `GET /api/assets/{id}/similar`: 相似素材端点
- [ ] 搜索接口向后兼容（不传 mode 默认 keyword）

**验证：** curl 搜索返回语义相关结果，相似接口返回 Top N 素材。

---

## Slice 8.3 — 前端搜索 UI

**目标：** 搜索类型切换 + 相似素材叠加层。

**前端：**
- [ ] `App.tsx`: 搜索框右侧加类型切换下拉（综合/语义/匹配）
- [ ] `App.tsx`: 详情页"🔍 找相似内容"按钮
- [ ] `SimilarPanel.tsx`: 叠加层组件（加载中 / 结果网格 / 空状态 / 关闭）
- [ ] 搜索模式切换后自动重新搜索

**验证：** 三种模式可切换搜索，相似素材叠加层正常展示和关闭。

---

## 完成统计

| 切片 | 状态 | 类型 |
|------|------|------|
| 8.1 Embedding 基础设施 | ✅ | AFK |
| 8.2 语义搜索后端 | ✅ |
| 8.3 前端搜索 UI | ✅ |
