# V15 技术设计

> AI 搜索 + 节点树状列表的技术方案。

## 功能 1: AI 搜索

### 数据流

```
用户输入 q → 前端 /api/search?mode=ai&q=xxx
  → search_ai_assets()
    → DB: SELECT id, filename, asset_type FROM assets WHERE status='active'
    → DB: get_asset_tags() 逐个获取 tags
    → 构建 prompt: get_prompt("search_ai") + {assets} + {query}
    → AIWorker.get_adapter("search_ai").chat(prompt)
    → 解析 JSON {"asset_ids": [...]}
    → DB: SELECT * FROM assets WHERE id IN (...) → 返回 items
    → _count_by_type(items) → counts
  ← HTTP 200 {"items": [...], "counts": {...}}
```

### 组件分工

| 组件 | 职责 | 文件 |
|------|------|------|
| `search_ai_assets()` | 全量素材→prompt→LLM→解析→回查 | `quickmedia/search.py`（新增函数） |
| `PromptConfig.get_prompt("search_ai")` | prompt 模板拼接（已有） | `quickmedia/prompt_config.py` |
| `AIWorker.get_adapter()` | 按 task_type 创建适配器 | `quickmedia/ai_worker.py` |
| `GET /api/search` mode=ai 分支 | HTTP 入口，调 search_ai_assets | `quickmedia/api/server.py` |
| `GET /api/task-models` | 返回 search_ai binding 状态 | `quickmedia/api/server.py` |
| 搜索模式选择器 | 改名+重排+红点+搜索触发 | `frontend/src/App.tsx` |

### Prompt 模板结构

```yaml
search_ai:
  system_format: |
    请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：
    {"asset_ids": [1, 5, 23]}
    如果没有找到相关素材，输出：{"asset_ids": []}
  default: |
    你是素材搜索助手。下面是一批素材列表，每行格式：ID|文件名|类型|标签
    用户的搜索意图是：{query}

    请返回**严格相关**的素材ID列表。
    - 只有素材内容与用户查询明确相关时才返回
    - 不确定的相关性 → 不返回（宁可缺勿滥）
    - 按相关度从高到低排序

    素材列表：
    {assets}
  custom: ""
  presets: []
```

### assets 占位符格式

```
  [1] 披萨.png (image)
    描述: 卡通风格的披萨插画，圆形黄色饼底上有红色香肠和绿色蔬菜配料
    标签: 披萨, 蔬菜, 卡通插画, 食物
  [2] 20260607-031931.mp4 (video)
    描述:
    标签: 无
  [3] 会议精神记录.md (document)
    描述: 讨论了下季度产品规划和团队分工...
    标签: 会议, 项目, 决策
```

### LLM 结果解析函数

```python
def parse_search_ai_result(raw: str) -> list[int]:
    """从LLM响应中提取asset_ids列表。"""
    # 1. 提取markdown代码块或{...}
    # 2. json.loads
    # 3. 返回 asset_ids 列表（验证每个是int）
    # 4. 失败返回 []
```

### DEFAULT_PROMPTS 合并逻辑

- `PromptConfig._load()` 遍历 `DEFAULT_PROMPTS` keys，用 `data.setdefault()`
- 新增 search_ai 后自动合并，`system_format` 强制同步
- 现有 5 种 prompt 类型不受影响

### 前端状态扩展

```typescript
// smode type
type SearchMode = "ai" | "keyword" | "semantic" | "combined";

// AI 可用性检测
const [aiSearchReady, setAiSearchReady] = useState(false);

// 挂载时
fetch("/api/task-models")
  .then(r => r.json())
  .then(d => {
    const sa = d.search_ai;
    setAiSearchReady(!!(sa?.provider && sa?.model));
    if (!sa?.provider || !sa?.model) {
      ssmode("combined"); // fallback
    }
  });
```

---

## 功能 2: 节点树状列表

### 组件树

```
App
├── 左侧 sidebar
│   ├── Tab: 搜索 (现有)
│   └── Tab: 节点
│       └── NodePanel
│           ├── [新建节点按钮]
│           ├── TreeItem (节点1)
│           │   ├── row: ▶ 节点名 (12) [⋮]
│           │   └── (展开时) AssetRow[]
│           │       ├── AssetRow: 🖼 cat.png (draggable)
│           │       └── AssetRow: 📄 doc.txt
│           ├── TreeItem (节点2)
│           │   └── ...
│           └── TreeItem (未分配, 虚拟)
│               └── AssetRow[]
```

### TreeItem 接口

```typescript
interface TreeItemProps {
  id: number | "unassigned";
  name: string;
  assetCount: number;
  assets: AssetBasic[] | null;  // null=未加载/折叠
  expanded: boolean;
  isUnassigned: boolean;
  graphData: GraphData;
  onToggle: (id: number | "unassigned") => void;
  onSelectNode: (id: number | null) => void;
  onSelectAsset: (id: number) => void;
  refreshKey: number;
}
```

### AssetRow 结构

```typescript
// 素材列表项（子节点下 + 未分配节点下复用）
interface AssetRowProps {
  asset: AssetBasic;
  sourceNodeId: number | "unassigned";  // 用于拖放
  onSelect: (id: number) => void;
  draggable: boolean;
}
```

### 展开/折叠状态管理

```typescript
// NodePanel 内部 state
const [expandedNodes, setExpandedNodes] = useState<Set<number | "unassigned">>(new Set());
const [nodeAssets, setNodeAssets] = useState<Map<number, AssetBasic[]>>(new Map());

// 展开
const handleToggle = (id: number | "unassigned") => {
  setExpandedNodes(prev => {
    const next = new Set(prev);
    if (next.has(id)) { next.delete(id); return next; }
    else { next.add(id); return next; }
  });
  
  // 按需加载
  if (id !== "unassigned" && !nodeAssets.has(id)) {
    fetch(`/api/nodes/${id}`).then(r => r.json())
      .then(d => setNodeAssets(prev => new Map(prev.set(id, d.assets))));
  }
};
```

### 拖放实现

```typescript
// dragstart (AssetRow)
const handleDragStart = (e: DragEvent, asset: AssetBasic, sourceNodeId: number | "unassigned") => {
  e.dataTransfer!.setData("text/plain", JSON.stringify({
    asset_id: asset.id,
    source_node_id: sourceNodeId,
    filename: asset.filename,
  }));
  e.dataTransfer!.effectAllowed = "move";
};

// drop on 树节点 (TreeItem row)
const handleDrop = async (e: DragEvent, targetNodeId: number) => {
  e.preventDefault();
  const data = JSON.parse(e.dataTransfer!.getData("text/plain"));
  
  if (targetNodeId === data.source_node_id) return; // 同节点忽略
  
  const res = await fetch(`/api/nodes/${targetNodeId}/assets`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({asset_ids: [data.asset_id]}),
  });
  
  if (res.ok) {
    // 刷新 source 和 target 展开节点
    onRefresh([data.source_node_id, targetNodeId].filter(Boolean));
  }
};

// drop on 未分配节点
const handleDropUnassigned = async (e: DragEvent) => {
  const data = JSON.parse(e.dataTransfer!.getData("text/plain"));
  const sid = data.source_node_id;
  
  if (sid === "unassigned") return; // 未分配→未分配忽略
  
  const res = await fetch(`/api/nodes/${sid}/assets/${data.asset_id}`, {
    method: "DELETE",
  });
  
  if (res.ok) onRefresh([sid, "unassigned"]);
};
```

### 树列表联动刷新

```typescript
// props
interface NodePanelProps {
  refreshKey: number;          // 父组件递增此值触发刷新
  graphData: GraphData;        // 云图数据（提供 unassigned）
  expandedNodes: Set<number>;  // 已展开节点集合
  onExpandedChange: (set: Set<number>) => void;
  ...
}

// useEffect 监听 refreshKey
useEffect(() => {
  // 重新加载所有已展开节点的素材
  expandedNodes.forEach(async id => {
    const data = await fetch(`/api/nodes/${id}`).then(r => r.json());
    setNodeAssets(prev => new Map(prev.set(id, data.assets)));
  });
}, [refreshKey]);
```

### 素材类型图标映射

```typescript
const ASSET_TYPE_ICON: Record<string, string> = {
  image: "图片",
  video: "视频",
  audio: "音频",
  document: "文档",
};
```

### 未分配节点视觉

```css
.unassigned-node {
  border-style: dashed;
  color: #8e8b82;  /* S.ms */
  opacity: 0.7;
}
```

---

## API 合约

### GET /api/search?mode=ai

**响应**:
```json
{
  "items": [{
    "id": 1,
    "filename": "披萨.png",
    "asset_type": "image",
    "size": 11593,
    "width": 200,
    "height": 200,
    "path": "/Users/...",
    "tags": [{"id": 1, "name": "披萨", "source": "auto"}, ...],
    "visual_description": "卡通风格的...",
    "ai_summary": null,
    ...
  }],
  "counts": {"image": 5, "video": 1, "audio": 0, "document": 2}
}
```

### GET /api/task-models

**响应**（含 search_ai）:
```json
{
  "vision": {"provider": "ollama", "model": "qwen3.5:9b"},
  "text": {"provider": "ollama", "model": "qwen3.5:9b"},
  "speech": {"provider": "ollama", "model": "qwen3.5:9b"},
  "video_summary": {"provider": "ollama", "model": "qwen3.5:9b"},
  "search_ai": {"provider": "deepseek", "model": "deepseek-v4-flash"}
}
```

### GET /api/nodes/{id}

**响应**（已有，复用）:
```json
{
  "id": 1,
  "name": "宠物照片",
  "description": "各种猫狗的照片",
  "asset_count": 12,
  "assets": [
    {"id": 1, "filename": "cat.png", "asset_type": "image", "size": 11593, ...},
    ...
  ]
}
```

### POST /api/nodes/{id}/assets
### DELETE /api/nodes/{id}/assets/{asset_id}

已有端点，复用。DELETE 幂等：关联不存在也返回 ok。

---

## 文件变更范围

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `quickmedia/prompt_config.py` | 修改 | DEFAULT_PROMPTS 新增 search_ai |
| `quickmedia/config.py` | 修改 | DEFAULT_CONFIG.task_models 新增 search_ai |
| `quickmedia/search.py` | 修改 | 新增 search_ai_assets() |
| `quickmedia/api/server.py` | 修改 | mode=ai 分支 + task-models search_ai |
| `quickmedia/mcp_server.py` | 修改 | mode 参数扩展 ai |
| `frontend/src/App.tsx` | 修改 | smode 改名/重排/AI调用/红点/搜索联动 |
| `frontend/src/NodePanel.tsx` | 修改 | 平铺→树形 TreeItem + 展开/折叠/拖放 |
| `tests/test_v15.py` | 新增 | V15 后端测试 |
| `tests/test_v15_frontend.py` | 新增 | V15 前端组件测试 |
