# V12 技术方案 — 素材聚合

## 架构概览

```
┌─ Web UI (React) ─────────────────────────────────────┐
│  Sidebar: [Tab1:搜索筛选] [Tab2:聚合节点]              │
│  Tab2: NodePanel (节点列表+操作按钮+横幅)               │
│        AddAssetModal (搜索+多选弹窗)                   │
│        扫描弹窗 (配置路径/选择文件/选择文件夹)           │
└────────────────────┬──────────────────────────────────┘
                     │ REST API
┌────────────────────▼──────────────────────────────────┐
│  FastAPI Server (server.py)                            │
│  ├─ /api/nodes/* (节点 CRUD)                           │
│  ├─ /api/aggregation/run → spawn daemon 线程          │
│  ├─ /api/scan-file → Scanner.scan_file()              │
│  ├─ /api/scan-folder → Scanner.scan_directory()       │
│  └─ /api/file-picker → osascript choose file          │
└────────────────────┬──────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────┐
│  Daemon Thread (按需创建)                              │
│  ├─ mark_processing → mark_done/failed                │
│  ├─ build_prompt(mode, assets, nodes)                 │
│  ├─ OpenAIAdapter.chat(prompt) / OllamaAdapter.chat() │
│  ├─ save_aggregation_result(db, result)               │
│  └─ 全量模式先 DELETE nodes + node_assets 再 INSERT   │
└───────────────────────────────────────────────────────┘
```

## 与设计稿的差异

| 设计稿 | 实际实现 | 原因 |
|--------|---------|------|
| 独立 Worker 进程轮询队列 | Daemon 线程按需执行 | 一次性任务无需常驻进程 |
| worker.py 含 run_aggregation_worker() | 仅保留共享工具函数 | 执行逻辑移至 api.py |
| 手写 HTTP 调用 AI | 复用 OpenAIAdapter/OllamaAdapter | 去重+DeepSeek thinking 禁用 |

## 数据库

```sql
CREATE TABLE aggregation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,           -- full / full_append / append
    status TEXT DEFAULT 'pending', -- pending / processing / done / failed
    error TEXT,
    created_at TEXT,
    completed_at TEXT
);

CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE node_assets (
    node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, asset_id)
);
```

## Scanner 重构

提取两个公共方法，scan_directory 和 scan_file 共享：

```python
def _insert_asset(self, filepath, filename, ext, asset_type, size, st, hash_val) -> int
def _ingest_file(self, filepath, result=None) -> int
```

`_ingest_file` 三道防线：inode匹配 → 哈希匹配 → 新增入库 + 标签/元数据/缩略图/AI入队。

## 三种聚合模式

| 模式 | 传什么 | 全部分配时 |
|------|--------|---------|
| full | 全量素材 | 不跳过，先清空再重建 |
| full_append | 全量素材 + 已有节点 | 跳过 (unassigned=0) |
| append | 仅未分配素材 + 已有节点 | 跳过 (unassigned=0) |

## 代码组织

- **后端**: `quickmedia/aggregation/api.py` (路由+执行), `prompts.py` (prompt构建), `worker.py` (共享工具)
- **前端**: `NodePanel.tsx`, `AddAssetModal.tsx`
- **测试**: `tests/test_v12.py` (28), `frontend/tests/` (15)
