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
    """搜索素材。mode: keyword(关键词) | semantic(语义) | combined(综合RRF)。

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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
