"""V12 Aggregation — shared utility functions."""

from datetime import datetime


def mark_processing(db, task_id: int) -> None:
    """Mark a task as processing."""
    db.execute(
        "UPDATE aggregation_queue SET status='processing' WHERE id=?",
        (task_id,),
    )


def mark_done(db, task_id: int, nodes_created: int = 0, assigned: int = 0) -> None:
    """Mark a task as completed with result counts."""
    db.execute(
        "UPDATE aggregation_queue SET status='done', completed_at=?, nodes_created=?, assigned=? WHERE id=?",
        (datetime.now().isoformat(), nodes_created, assigned, task_id),
    )


def mark_failed(db, task_id: int, error: str) -> None:
    """Mark a task as failed with error message."""
    db.execute(
        "UPDATE aggregation_queue SET status='failed', error=?, completed_at=? WHERE id=?",
        (error, datetime.now().isoformat(), task_id),
    )


def get_all_assets(db) -> list[dict]:
    """Get all active assets with descriptions and tags for aggregation."""
    from quickmedia.asset_ops import get_asset_detail
    rows = db.execute("SELECT id FROM assets WHERE status='active'")
    assets = []
    for row in rows:
        detail = get_asset_detail(db, row["id"])
        if detail:
            assets.append(detail)
    return assets


def get_all_nodes(db) -> list[dict]:
    """Get all nodes with their asset associations."""
    nodes = db.execute(
        "SELECT n.*, COUNT(na.asset_id) as asset_count "
        "FROM nodes n LEFT JOIN node_assets na ON n.id=na.node_id "
        "GROUP BY n.id ORDER BY asset_count DESC"
    )
    result = []
    for node in nodes:
        n = dict(node)
        asset_rows = db.execute(
            "SELECT asset_id FROM node_assets WHERE node_id=?", (n["id"],)
        )
        n["asset_ids"] = [r["asset_id"] for r in asset_rows]
        result.append(n)
    return result


def save_aggregation_result(db, result: dict) -> None:
    """Save aggregation results (nodes + assignments) to database."""
    nodes = result.get("nodes", [])
    for node_data in nodes:
        name = node_data.get("name", "").strip()
        if not name:
            continue
        description = node_data.get("description", "").strip()
        asset_ids = node_data.get("asset_ids", [])

        db.execute(
            "INSERT INTO nodes (name, description, created_at) VALUES (?,?,?)",
            (name, description, datetime.now().isoformat()),
        )
        node_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]

        for aid in asset_ids:
            try:
                db.execute(
                    "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                    (node_id, int(aid)),
                )
            except Exception:
                pass

    # Handle explicit assignments (append mode)
    assignments = result.get("assignments", {})
    for node_id_str, asset_id_list in assignments.items():
        try:
            node_id = int(node_id_str)
        except (ValueError, TypeError):
            continue
        for aid in (asset_id_list or []):
            try:
                db.execute(
                    "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                    (node_id, int(aid)),
                )
            except Exception:
                pass
