"""QuickMedia MCP Server — exposes asset management tools to AI agents."""

import os, json
from typing import Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP


def get_data_dir() -> str:
    return os.environ.get("QUICKMEDIA_HOME", os.path.expanduser("~/.asset-manager"))


def init_db():
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    from quickmedia.database import Database
    from quickmedia.config import Config
    db_path = os.path.join(data_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=data_dir)
    return db, cfg, data_dir


# ── Output Models ──────────────────────────────────────────────


class Tag(BaseModel):
    name: str = Field(description="标签名称")
    source: str = Field(description="来源: auto(AI自动生成) 或 manual(手动添加)")


class AssetBasic(BaseModel):
    """搜索结果/列表项的简要素材信息。"""
    id: int = Field(description="素材ID")
    filename: str = Field(description="文件名")
    asset_type: str = Field(description="类型: image/video/audio/document")
    size: int = Field(description="文件大小(字节)")
    path: Optional[str] = Field(default=None, description="文件路径")
    visual_description: Optional[str] = Field(default=None, description="AI图片/视频视觉描述")
    ai_summary: Optional[str] = Field(default=None, description="AI文本摘要(文档内容/音频转录/视频的语音转录)")
    distance: Optional[float] = Field(default=None, description="语义相似距离(越小越相关,仅搜索/相似返回)")
    rrf_score: Optional[float] = Field(default=None, description="RRF综合得分(越大越相关,仅综合搜索返回)")

    class Config:
        extra = "allow"


class AssetDetail(BaseModel):
    """素材完整详情,包含所有AI分析结果和标签。"""
    id: int = Field(description="素材ID")
    hash: Optional[str] = Field(default=None, description="文件SHA256哈希")
    inode: Optional[int] = Field(default=None, description="inode号")
    device: Optional[int] = Field(default=None, description="设备号")
    path: Optional[str] = Field(default=None, description="文件完整路径")
    filename: str = Field(description="文件名")
    extension: Optional[str] = Field(default=None, description="文件扩展名(不含点)")
    asset_type: str = Field(description="类型: image/video/audio/document")
    size: int = Field(description="文件大小(字节)")
    width: Optional[int] = Field(default=None, description="图片/视频宽度(像素)")
    height: Optional[int] = Field(default=None, description="图片/视频高度(像素)")
    duration: Optional[float] = Field(default=None, description="音视频时长(秒)")
    visual_description: Optional[str] = Field(default=None, description="AI视觉描述(图片帧分析结果)")
    ai_summary: Optional[str] = Field(default=None, description="AI文本摘要(文档内容/音频素材的音频转录/视频素材的语音转录)")
    ocr_text: Optional[str] = Field(default=None, description="图片OCR识别文字")
    transcript: Optional[str] = Field(default=None, description="音频/视频语音转录全文")
    video_summary: Optional[str] = Field(default=None, description="视频综合总结(视觉+语音融合理解)")
    tags: list[Tag] = Field(default_factory=list, description="标签列表")
    modified_at: Optional[str] = Field(default=None, description="文件修改时间(ISO格式)")
    created_at: Optional[str] = Field(default=None, description="文件创建时间(ISO格式)")

    class Config:
        extra = "allow"


class ActionResult(BaseModel):
    ok: bool = Field(description="操作是否成功")
    message: str = Field(default="", description="结果消息")
    error: Optional[str] = Field(default="", description="错误信息(失败时)")
    asset_id: Optional[int] = Field(default=None, description="操作的素材ID")


class ScanResult(BaseModel):
    ok: bool = Field(description="操作是否成功")
    message: str = Field(default="", description="结果消息")
    new: int = Field(default=0, description="新增素材数")
    updated: int = Field(default=0, description="更新素材数")
    total: int = Field(default=0, description="扫描总数")
    asset_id: Optional[int] = Field(default=None, description="单文件添加时的素材ID")


class NodeInfo(BaseModel):
    """聚合节点信息。"""
    id: int = Field(description="节点ID")
    name: str = Field(description="节点名称")
    description: str = Field(default="", description="节点描述")
    asset_count: int = Field(default=0, description="节点内素材数量")


class NodeDetail(BaseModel):
    """聚合节点详情,包含素材列表。"""
    id: int = Field(description="节点ID")
    name: str = Field(description="节点名称")
    description: str = Field(default="", description="节点描述")
    asset_count: int = Field(default=0, description="节点内素材数量")
    assets: list[AssetBasic] = Field(default_factory=list, description="节点内的素材列表")


# ── Helpers ────────────────────────────────────────────────────


def _enrich_detail(db, item: dict) -> dict:
    """Add tags to an asset dict."""
    tags = db.execute(
        "SELECT t.name, at.source FROM asset_tags at JOIN tags t ON t.id=at.tag_id WHERE at.asset_id=?",
        (item["id"],),
    )
    item["tags"] = [dict(t) for t in tags] if tags else []
    return item


def _map_extension(item: dict) -> dict:
    """Rename extension -> ext in DB row for model compatibility."""
    if "extension" in item:
        item["ext"] = item.pop("extension")
    return item


# ── Tools ──────────────────────────────────────────────────────


mcp = FastMCP("quickmedia")


@mcp.tool()
def search_assets(query: str, mode: str = "combined", limit: int = 10) -> list[AssetBasic]:
    """搜索素材。mode: keyword(关键词) | semantic(语义) | combined(综合RRF) | ai(AI搜索)。

    返回 AssetBasic 字段:
    - id: 素材ID
    - filename: 文件名
    - asset_type: 类型 image/video/audio/document
    - size: 文件大小(字节)
    - path: 文件路径
    - visual_description: AI图片/视频视觉描述
    - ai_summary: AI文本摘要
    - distance: 语义相似距离(越小越相关, semantic/combined模式)
    - rrf_score: RRF综合得分(越大越相关, combined模式)
    """
    db, cfg, data_dir = init_db()
    if mode == "ai":
        from quickmedia.search import search_ai_assets
        result = search_ai_assets(query, db, cfg, data_dir)
        return [AssetBasic(**r) for r in result] if result else []
    from quickmedia.search import search_assets as do_search
    result = do_search(query, mode, limit, db, cfg, data_dir)
    return [AssetBasic(**r) for r in result] if result else []


@mcp.tool()
def get_asset(asset_id: int = 0, asset_ids: list[int] = None) -> AssetDetail | list[AssetDetail]:
    """获取素材完整详情。支持单个或批量。

    返回 AssetDetail 字段:
    - id: 素材ID
    - filename: 文件名
    - extension: 文件扩展名(不含点)
    - path: 文件完整路径
    - asset_type: 类型 image/video/audio/document
    - size: 文件大小(字节)
    - width: 图片/视频宽度(像素)
    - height: 图片/视频高度(像素)
    - duration: 音视频时长(秒)
    - visual_description: AI视觉描述(图片帧分析结果)
    - ai_summary: AI文本摘要(文档内容/音频转录/视频语音转录)
    - ocr_text: 图片OCR识别文字
    - transcript: 音频/视频语音转录全文
    - video_summary: 视频综合总结(视觉+语音融合理解)
    - tags: [{name, source}] 标签, source=auto(AI生成)/manual(手动)
    - hash: 文件SHA256哈希
    - modified_at / created_at: 文件时间(ISO格式)
    """
    db, cfg, _ = init_db()
    ids = asset_ids if asset_ids else [asset_id] if asset_id else []
    if not ids:
        return AssetDetail(id=0, filename="error", asset_type="other", size=0)
    result = []
    for aid in ids:
        rows = db.execute("SELECT * FROM assets WHERE id=?", (aid,))
        if rows:
            item = dict(rows[0])
            _enrich_detail(db, item)
            result.append(AssetDetail(**item))
    if not result:
        return AssetDetail(id=0, filename="not_found", asset_type="other", size=0)
    return result[0] if len(result) == 1 and not asset_ids else result


@mcp.tool()
def list_assets(asset_type: str = "", tags: list[str] = None, limit: int = 20) -> list[AssetBasic]:
    """列出素材,可按类型和标签筛选。asset_type: image/video/audio/document。

    返回 AssetBasic 字段:
    - id: 素材ID
    - filename: 文件名
    - asset_type: 类型 image/video/audio/document
    - size: 文件大小(字节)
    - path: 文件路径
    - visual_description: AI图片/视频视觉描述
    - ai_summary: AI文本摘要
    """
    db, cfg, _ = init_db()
    from quickmedia.asset_ops import list_assets_filtered
    result = list_assets_filtered(db, asset_type, tags, limit)
    return [AssetBasic(**r) for r in result]


@mcp.tool()
def find_similar(asset_id: int, limit: int = 10) -> list[AssetBasic]:
    """查找视觉/语义相似素材。

    返回 AssetBasic 字段:
    - id: 素材ID
    - filename: 文件名
    - asset_type: 类型 image/video/audio/document
    - size: 文件大小(字节)
    - path: 文件路径
    - distance: 语义相似距离(越小越相似)
    """
    db, cfg, data_dir = init_db()
    try:
        from quickmedia.embedding import ChromaStore
        chroma_path = os.path.join(data_dir, "chroma_db")
        store = ChromaStore(persist_path=chroma_path)
        vectors = []
        for i in range(20):
            v = store.get_vector(asset_id, "search", term_index=i)
            if v:
                vectors.append(v)
            else:
                break
        if not vectors:
            return []
        all_matches = {}
        for v in vectors:
            similar = store.query(v, n_results=limit)
            for s in similar:
                sid = s.get("asset_id") if isinstance(s, dict) else s[0]
                sd = s.get("distance") if isinstance(s, dict) else s[1]
                if sid != asset_id and (sid not in all_matches or sd < all_matches[sid]):
                    all_matches[sid] = sd
        sorted_ids = sorted(all_matches.items(), key=lambda x: x[1])[:limit]
        result = []
        for sid, dist in sorted_ids:
            r = db.execute("SELECT id, filename, asset_type, size FROM assets WHERE id=?", (sid,))
            if r:
                item = dict(r[0])
                item["distance"] = dist
                result.append(AssetBasic(**item))
        return result
    except Exception:
        return []


@mcp.tool()
def add_asset(path: str) -> ScanResult:
    """添加文件或目录到素材库。路径是文件则添加单个,是目录则扫描整个目录。

    返回 ScanResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    - new: 新增素材数
    - updated: 更新素材数
    - total: 扫描总数
    - asset_id: 单文件添加时的素材ID
    """
    db, cfg, _ = init_db()
    from quickmedia.scanner import Scanner
    scanner = Scanner(db=db, config=cfg)
    if os.path.isdir(path):
        r = scanner.scan_directory(path, recursive=True, max_depth=cfg.get("ai.video_frames") or 3)
        return ScanResult(ok=True, message=f"已扫描目录 {path}", new=r.get("new", 0),
                          updated=r.get("updated", 0), total=r.get("total", 0))
    elif os.path.isfile(path):
        aid = scanner.scan_file(path)
        if aid:
            return ScanResult(ok=True, message=f"已添加 {path}", asset_id=aid)
        return ScanResult(ok=False, error=f"添加失败: {path}")
    else:
        return ScanResult(ok=False, error=f"路径不存在: {path}")


@mcp.tool()
def delete_asset(asset_id: int = 0, asset_ids: list[int] = None) -> ActionResult:
    """删除素材及其所有关联数据(标签/向量/AI结果)。支持批量。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    - error: 错误信息(失败时)
    - asset_id: 操作的素材ID
    """
    db, cfg, _ = init_db()
    from quickmedia.asset_ops import delete_asset_full
    ids = asset_ids if asset_ids else [asset_id] if asset_id else []
    if not ids:
        return ActionResult(ok=False, error="请提供 asset_id 或 asset_ids")
    results = [delete_asset_full(db, cfg, aid) for aid in ids]
    errors = [r for r in results if not r.get("ok")]
    if errors:
        return ActionResult(ok=False, error=f"删除失败 {len(errors)}/{len(ids)}")
    return ActionResult(ok=True, message=f"已删除 {len(ids)} 个素材")


# ── Node Tools ──────────────────────────────────────────────────


@mcp.tool()
def list_nodes() -> list[NodeInfo]:
    """列出所有聚合节点,按素材数量降序。

    返回 NodeInfo 字段:
    - id: 节点ID
    - name: 节点名称
    - description: 节点描述
    - asset_count: 节点内素材数量
    """
    db, _, _ = init_db()
    rows = db.execute(
        "SELECT n.*, COUNT(na.asset_id) as asset_count "
        "FROM nodes n LEFT JOIN node_assets na ON n.id=na.node_id "
        "GROUP BY n.id ORDER BY asset_count DESC"
    )
    return [NodeInfo(**dict(r)) for r in rows] if rows else []


@mcp.tool()
def get_node(node_id: int) -> NodeDetail:
    """获取聚合节点详情,包含节点内的素材列表。

    返回 NodeDetail 字段:
    - id: 节点ID
    - name: 节点名称
    - description: 节点描述
    - asset_count: 节点内素材数量
    - assets: [{id, filename, asset_type, size, path, ...}] 节点内的素材列表
    """
    db, _, _ = init_db()
    rows = db.execute(
        "SELECT n.*, COUNT(na.asset_id) as asset_count "
        "FROM nodes n LEFT JOIN node_assets na ON n.id=na.node_id "
        "WHERE n.id=? GROUP BY n.id",
        (node_id,),
    )
    if not rows:
        return NodeDetail(id=0, name="not_found", description="", asset_count=0)
    node = dict(rows[0])
    assets = db.execute(
        "SELECT a.id, a.filename, a.asset_type, a.size "
        "FROM assets a JOIN node_assets na ON a.id=na.asset_id "
        "WHERE na.node_id=? ORDER BY a.filename",
        (node_id,),
    )
    node["assets"] = [AssetBasic(**dict(a)) for a in assets] if assets else []
    return NodeDetail(**node)


@mcp.tool()
def create_node(name: str, description: str = "") -> ActionResult:
    """手动创建聚合节点。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    - asset_id: 新节点的ID
    """
    db, _, _ = init_db()
    if not name.strip():
        return ActionResult(ok=False, error="节点名不能为空")
    db.execute(
        "INSERT INTO nodes (name, description) VALUES (?,?)",
        (name.strip(), description),
    )
    nid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
    return ActionResult(ok=True, message=f"已创建节点 {name}", asset_id=nid)


@mcp.tool()
def update_node(node_id: int, name: str, description: str = "") -> ActionResult:
    """更新聚合节点名称和描述。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
    if not existing:
        return ActionResult(ok=False, error="节点不存在")
    db.execute(
        "UPDATE nodes SET name=?, description=? WHERE id=?",
        (name.strip(), description, node_id),
    )
    return ActionResult(ok=True, message=f"已更新节点 {name}")


@mcp.tool()
def delete_node(node_id: int) -> ActionResult:
    """删除聚合节点(素材不会被删除)。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
    if not existing:
        return ActionResult(ok=False, error="节点不存在")
    db.execute("DELETE FROM node_assets WHERE node_id=?", (node_id,))
    db.execute("DELETE FROM nodes WHERE id=?", (node_id,))
    return ActionResult(ok=True, message="已删除节点")


@mcp.tool()
def add_assets_to_node(node_id: int, asset_ids: list[int]) -> ActionResult:
    """手动将素材分配到节点。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息(含成功数量)
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
    if not existing:
        return ActionResult(ok=False, error="节点不存在")
    added = 0
    for aid in asset_ids:
        try:
            db.execute(
                "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                (node_id, int(aid)),
            )
            added += 1
        except Exception:
            pass
    return ActionResult(ok=True, message=f"已添加 {added} 个素材到节点")


@mcp.tool()
def remove_assets_from_node(node_id: int, asset_ids: list[int]) -> ActionResult:
    """从节点中移除素材(素材本身不会被删除)。支持批量。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息(含移除数量)
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
    if not existing:
        return ActionResult(ok=False, error="节点不存在")
    removed = 0
    for aid in asset_ids:
        db.execute(
            "DELETE FROM node_assets WHERE node_id=? AND asset_id=?",
            (node_id, int(aid)),
        )
        removed += db.conn.total_changes
    return ActionResult(ok=True, message=f"已从节点移除 {removed} 个素材")


@mcp.tool()
def run_aggregation(mode: str) -> ActionResult:
    """触发聚合分析(阻塞等待完成)。mode: full(全量分析,从头重建) | full_append(全量追加,保留节点) | append(追加分析,仅新素材)。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息(含生成的节点数)
    """
    from datetime import datetime
    db, _, _ = init_db()
    if mode not in ("full", "full_append", "append"):
        return ActionResult(ok=False, error=f"无效模式: {mode}")
    running = db.execute(
        "SELECT 1 FROM aggregation_queue WHERE status IN ('pending','processing')"
    )
    if running:
        return ActionResult(ok=False, error="已有聚合任务进行中")

    from quickmedia.aggregation.worker import mark_processing, mark_done, mark_failed

    db.execute(
        "INSERT INTO aggregation_queue (mode, status, created_at) VALUES (?,?,?)",
        (mode, "pending", datetime.now().isoformat()),
    )
    task_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

    try:
        mark_processing(db, task_id)
        from quickmedia.aggregation.core import run_aggregation as _run
        node_count, assigned = _run(mode, db, get_data_dir())
        mark_done(db, task_id)
        msg = "聚合完成"
        if node_count > 0: msg += f"，新建 {node_count} 个节点"
        if assigned > 0: msg += f"，追加 {assigned} 个关联"
        return ActionResult(ok=True, message=msg)
    except Exception as e:
        mark_failed(db, task_id, str(e))
        return ActionResult(ok=False, error=str(e))


@mcp.tool()
def trigger_scan() -> ActionResult:
    """触发扫描所有已配置的监控路径。扫描完成后返回结果。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    import os as _os3
    db, cfg, _ = init_db()
    from quickmedia.scanner import Scanner
    scanner = Scanner(db=db, config=cfg)
    watch_paths = cfg.get("watch_paths") or []
    if not watch_paths:
        return ActionResult(ok=False, error="未配置监控路径")
    total_new = 0
    for wp in watch_paths:
        path = _os3.path.expanduser(wp.get("path", "").replace(":", "/"))
        if _os3.path.isdir(path):
            result = scanner.scan_directory(
                path,
                recursive=wp.get("recursive", True),
                max_depth=wp.get("max_depth", 3),
            )
            total_new += result["new"]
    return ActionResult(ok=True, message=f"扫描 {len(watch_paths)} 条路径，新增 {total_new} 个素材")


@mcp.tool()
def get_aggregation_status() -> ActionResult:
    """查询聚合任务当前状态。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 状态描述(idle/running/done/failed + 详情)
    """
    db, _, _ = init_db()
    task = db.execute("SELECT * FROM aggregation_queue ORDER BY id DESC LIMIT 1")
    if not task:
        return ActionResult(ok=True, message="无聚合任务记录")
    t = dict(task[0])
    status = t.get("status", "unknown")
    mode = t.get("mode", "")
    if status == "done":
        return ActionResult(ok=True, message=f"上次 {mode} 聚合已完成")
    elif status in ("pending", "processing"):
        return ActionResult(ok=True, message=f"{mode} 聚合进行中")
    elif status == "failed":
        return ActionResult(ok=False, error=f"{mode} 聚合失败: {t.get('error', '未知错误')}")
    return ActionResult(ok=True, message=f"状态: {status}")


@mcp.tool()
def reanalyze_asset(asset_id: int) -> ActionResult:
    """触发单个素材的AI重新分析(视觉/文档/语音)。分析异步执行,立即返回。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    db, cfg, _ = init_db()
    existing = db.execute("SELECT 1 FROM assets WHERE id=?", (asset_id,))
    if not existing:
        return ActionResult(ok=False, error="素材不存在")
    # Clear old auto tags
    db.execute("DELETE FROM asset_tags WHERE asset_id=? AND source='auto'", (asset_id,))
    # Re-enqueue AI tasks
    from quickmedia.ai_worker import AIWorker
    worker = AIWorker(db=db, config=cfg)
    asset = dict(db.execute("SELECT * FROM assets WHERE id=?", (asset_id,))[0])
    atype = asset.get("asset_type", "")
    if atype == "image":
        worker.enqueue(asset_id, "vision")
    elif atype == "video":
        worker.enqueue(asset_id, "video_vision")
        worker.enqueue(asset_id, "transcribe")
    elif atype == "audio":
        worker.enqueue(asset_id, "transcribe")
    elif atype == "document":
        worker.enqueue(asset_id, "text")
    return ActionResult(ok=True, message=f"已提交 {atype} 重新分析任务")


@mcp.tool()
def add_asset_tag(asset_id: int, tag_name: str) -> ActionResult:
    """给素材添加手动标签。标签不存在则自动创建。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM assets WHERE id=?", (asset_id,))
    if not existing:
        return ActionResult(ok=False, error="素材不存在")
    # Find or create tag
    tag = db.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
    if not tag:
        db.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
        tag_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
    else:
        tag_id = tag[0]["id"]
    db.execute(
        "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id, source) VALUES (?,?,'manual')",
        (asset_id, tag_id),
    )
    return ActionResult(ok=True, message=f"已添加标签 {tag_name}")


@mcp.tool()
def remove_asset_tag(asset_id: int, tag_name: str) -> ActionResult:
    """从素材移除手动标签。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息
    """
    db, _, _ = init_db()
    existing = db.execute("SELECT 1 FROM assets WHERE id=?", (asset_id,))
    if not existing:
        return ActionResult(ok=False, error="素材不存在")
    tag = db.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
    if not tag:
        return ActionResult(ok=False, error="标签不存在")
    db.execute(
        "DELETE FROM asset_tags WHERE asset_id=? AND tag_id=? AND source='manual'",
        (asset_id, tag[0]["id"]),
    )
    return ActionResult(ok=True, message=f"已移除标签 {tag_name}")


@mcp.tool()
def get_stats() -> ActionResult:
    """获取素材库统计信息: 总数、各类型数量、AI分析完成率等。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 统计信息文本
    """
    db, _, _ = init_db()
    total = db.execute("SELECT COUNT(*) as cnt FROM assets WHERE status='active'")[0]["cnt"]
    by_type = db.execute(
        "SELECT asset_type, COUNT(*) as cnt FROM assets WHERE status='active' GROUP BY asset_type"
    )
    type_stats = ", ".join(f"{r['asset_type']}: {r['cnt']}" for r in by_type)
    ai_done = db.execute(
        "SELECT COUNT(*) as cnt FROM assets WHERE status='active' AND (visual_description IS NOT NULL OR ai_summary IS NOT NULL)"
    )[0]["cnt"]
    msg = f"素材总数: {total} | {type_stats} | AI已分析: {ai_done}"
    return ActionResult(ok=True, message=msg)


@mcp.tool()
def analyze_append_node(node_id: int) -> ActionResult:
    """对单个节点执行分析追加: AI 分析全库未连接素材,自动匹配添加。阻塞等待完成(最多30秒)。

    返回 ActionResult 字段:
    - ok: 操作是否成功
    - message: 结果消息(含添加素材数)
    - error: 错误信息(失败时)
    """
    import json, re, os
    db, cfg, data_dir = init_db()
    existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
    if not existing:
        return ActionResult(ok=False, error="节点不存在")

    node_row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,))[0]
    node_info = dict(node_row)

    # Get existing assets
    node_assets = db.execute(
        "SELECT filename, ai_summary, visual_description FROM assets a "
        "JOIN node_assets na ON a.id=na.asset_id WHERE na.node_id=?",
        (node_id,),
    )
    existing_assets = [dict(r) for r in node_assets]

    # Get candidates
    candidates = db.execute(
        "SELECT id, filename, asset_type, ai_summary, visual_description FROM assets "
        "WHERE status='active' AND id NOT IN "
        "(SELECT asset_id FROM node_assets WHERE node_id=?)",
        (node_id,),
    )
    candidate_list = [dict(r) for r in candidates]
    if not candidate_list:
        return ActionResult(ok=True, message="无可分析的素材")

    # Build prompt and call AI
    from quickmedia.aggregation.prompts import build_append_prompt
    from quickmedia.openai_adapter import OpenAIAdapter
    from quickmedia.providers import ProviderRegistry
    models_path = os.path.join(data_dir, "models.yaml")
    registry = ProviderRegistry(cfg, models_path)
    binding = registry.get_task_binding("text")
    if not binding:
        return ActionResult(ok=False, error="未配置 text 模型")
    provider = registry.get_provider(binding["provider"]) or {}
    url = provider.get("url", "")
    api_key = ""
    env_path = os.path.join(data_dir, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if k == f"{binding['provider'].upper()}_API_KEY":
                        api_key = v.strip()
    adapter = OpenAIAdapter(
        base_url=url, api_key=api_key,
        model=binding["model"], timeout=30,
        provider_name=binding["provider"],
    )
    prompt = build_append_prompt(node_info, existing_assets, candidate_list)
    response = adapter.chat(prompt)

    # Parse JSON response
    try:
        match = re.search(r'\{[^{}]*"asset_ids"[^{}]*\}', response, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            asset_ids = parsed.get("asset_ids", [])
        else:
            asset_ids = []
    except Exception:
        asset_ids = []

    added = 0
    for aid in asset_ids:
        try:
            db.execute(
                "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                (node_id, int(aid)),
            )
            added += 1
        except Exception:
            pass

    return ActionResult(ok=True, message=f"已添加 {added} 个素材到节点")


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
