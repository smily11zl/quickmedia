"""Shared asset operations used by API server and MCP server."""

import os, json


def get_asset_detail(db, asset_id: int) -> dict | None:
    """Return full asset detail with tags, or None if not found."""
    rows = db.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
    if not rows:
        return None
    item = dict(rows[0])
    tags = db.execute(
        "SELECT t.name, at.source FROM asset_tags at JOIN tags t ON t.id=at.tag_id WHERE at.asset_id=?",
        (asset_id,),
    )
    item["tags"] = [dict(t) for t in tags] if tags else []
    return item


def list_assets_filtered(db, asset_type: str = "", tag_names: list[str] = None, limit: int = 20) -> list[dict]:
    """Return assets filtered by type and/or tags."""
    tag_names = tag_names or []
    has_type = bool(asset_type)
    has_tags = bool(tag_names)
    if has_type and has_tags:
        ph = ",".join("?" for _ in tag_names)
        rows = db.execute(
            f"SELECT DISTINCT a.id, a.filename, a.asset_type, a.size FROM assets a "
            f"JOIN asset_tags at ON a.id=at.asset_id JOIN tags t ON t.id=at.tag_id "
            f"WHERE a.asset_type=? AND t.name IN ({ph}) LIMIT ?",
            [asset_type] + tag_names + [limit],
        )
    elif has_type:
        rows = db.execute("SELECT id, filename, asset_type, size FROM assets WHERE asset_type=? LIMIT ?", (asset_type, limit))
    elif has_tags:
        ph = ",".join("?" for _ in tag_names)
        rows = db.execute(
            f"SELECT DISTINCT a.id, a.filename, a.asset_type, a.size FROM assets a "
            f"JOIN asset_tags at ON a.id=at.asset_id JOIN tags t ON t.id=at.tag_id "
            f"WHERE t.name IN ({ph}) LIMIT ?",
            tag_names + [limit],
        )
    else:
        rows = db.execute("SELECT id, filename, asset_type, size FROM assets LIMIT ?", (limit,))
    return [dict(r) for r in rows]


def delete_asset_full(db, cfg, asset_id: int) -> dict:
    """Delete an asset and all related data. Returns {ok: True/False, error?: ...}."""
    rows = db.execute("SELECT id FROM assets WHERE id=?", (asset_id,))
    if not rows:
        return {"ok": False, "error": f"asset {asset_id} not found"}
    db.execute("DELETE FROM asset_tags WHERE asset_id=?", (asset_id,))
    db.execute("DELETE FROM asset_search_terms WHERE asset_id=?", (asset_id,))
    db.execute("DELETE FROM ai_queue WHERE asset_id=?", (asset_id,))
    try:
        from quickmedia.embedding import ChromaStore
        data_dir = cfg.config_dir
        chroma_path = os.path.join(data_dir, "chroma_db")
        store = ChromaStore(persist_path=chroma_path)
        store.delete(asset_id)
    except Exception:
        pass
    db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
    return {"ok": True, "message": f"deleted asset {asset_id}"}
