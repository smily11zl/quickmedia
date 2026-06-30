"""V12 Aggregation API routes."""

from fastapi import HTTPException, FastAPI
from datetime import datetime
import threading, os, json


def _get_db(app: FastAPI):
    """Get a fresh Database connection (thread-safe)."""
    from quickmedia.database import Database
    db_path = app.extra["db_path"]
    return Database(db_path)


def register_aggregation_routes(app):
    """Register all aggregation routes on the FastAPI app."""

    @app.post("/api/aggregation/run")
    def aggregation_run(body: dict):
        mode = body.get("mode", "full")
        if mode not in ("full", "full_append", "append"):
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
        db = _get_db(app)
        running = db.execute(
            "SELECT 1 FROM aggregation_queue WHERE status IN ('pending','processing')"
        )
        if running:
            raise HTTPException(status_code=409, detail="aggregation_running")
        # Clean old task records before starting new one
        db.execute("DELETE FROM aggregation_queue")
        db.execute(
            "INSERT INTO aggregation_queue (mode, status, created_at) VALUES (?,?,?)",
            (mode, "pending", datetime.now().isoformat()),
        )
        task_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        db.close()

        # Spawn background thread to execute the task
        db_path = app.extra["db_path"]
        config_dir = app.extra["config_dir"]

        def run_task():
            from quickmedia.database import Database
            from quickmedia.aggregation.worker import mark_processing, mark_done, mark_failed

            task_db = Database(db_path)
            try:
                mark_processing(task_db, task_id)
                print(f"[Aggregation] 开始任务 #{task_id}: mode={mode}", flush=True)

                from quickmedia.aggregation.core import run_aggregation as _run
                node_count, assigned = _run(mode, task_db, config_dir)

                mark_done(task_db, task_id, node_count, assigned)
                import asyncio
                from quickmedia.api.server import broadcast_graph_changed
                asyncio.run(broadcast_graph_changed())
                print(f"[Aggregation] 任务 #{task_id} 完成: 新节点 {node_count}, 追加 {assigned} 个关联", flush=True)

            except Exception as e:
                print(f"[Aggregation] 任务 #{task_id} 失败: {e}", flush=True)
                mark_failed(task_db, task_id, str(e))
            finally:
                task_db.close()

        threading.Thread(target=run_task, daemon=True).start()
        return {"ok": True, "task_id": task_id, "message": f"已提交 {mode} 聚合任务"}

    @app.get("/api/aggregation/status")
    def aggregation_status():
        db = _get_db(app)
        task = db.execute("SELECT * FROM aggregation_queue ORDER BY id DESC LIMIT 1")
        if not task:
            return {"status": "idle"}
        t = dict(task[0])
        return {"status": t.get("status", "idle"), "task": t}

    @app.post("/api/aggregation/status/reset")
    def aggregation_status_reset():
        """Clear done and failed tasks from queue."""
        db = _get_db(app)
        db.execute("DELETE FROM aggregation_queue WHERE status IN ('done', 'failed')")
        return {"ok": True}

    @app.get("/api/nodes")
    def list_nodes():
        db = _get_db(app)
        nodes = db.execute(
            "SELECT n.*, COUNT(na.asset_id) as asset_count "
            "FROM nodes n LEFT JOIN node_assets na ON n.id=na.node_id "
            "GROUP BY n.id ORDER BY asset_count DESC"
        )
        return [dict(n) for n in nodes]

    @app.post("/api/nodes")
    async def create_node(body: dict):
        db = _get_db(app)
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="node_name_required")
        db.execute(
            "INSERT INTO nodes (name, description) VALUES (?,?)",
            (name, body.get("description", "")),
        )
        nid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        return {"id": nid, "name": name, "description": body.get("description", "")}

    @app.put("/api/nodes/{node_id}")
    async def update_node(node_id: int, body: dict):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="node_not_found")
        name = body.get("name", "").strip()
        if name:
            db.execute(
                "UPDATE nodes SET name=?, description=? WHERE id=?",
                (name, body.get("description", ""), node_id),
            )
        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        return {"ok": True}

    @app.delete("/api/nodes/{node_id}")
    async def delete_node(node_id: int):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="node_not_found")
        db.execute("DELETE FROM node_assets WHERE node_id=?", (node_id,))
        db.execute("DELETE FROM nodes WHERE id=?", (node_id,))
        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        return {"ok": True}

    @app.post("/api/nodes/{node_id}/assets")
    async def assign_assets(node_id: int, body: dict):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="node_not_found")
        asset_ids = body.get("asset_ids", [])
        for aid in asset_ids:
            try:
                db.execute(
                    "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                    (node_id, int(aid)),
                )
            except Exception:
                pass
        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        return {"ok": True}

    @app.delete("/api/nodes/{node_id}/assets/{asset_id}")
    async def unassign_asset(node_id: int, asset_id: int):
        db = _get_db(app)
        db.execute(
            "DELETE FROM node_assets WHERE node_id=? AND asset_id=?",
            (node_id, asset_id),
        )
        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        return {"ok": True}

    @app.get("/api/nodes/{node_id}/assets")
    def get_node_assets(node_id: int, limit: int = 200, offset: int = 0):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="node_not_found")
        rows = db.execute(
            "SELECT a.* FROM assets a "
            "JOIN node_assets na ON a.id=na.asset_id "
            "WHERE na.node_id=? AND a.status='active' "
            "ORDER BY a.filename LIMIT ? OFFSET ?",
            (node_id, limit, offset),
        )
        items = []
        for row in rows:
            item = dict(row)
            tags = db.execute(
                "SELECT t.id, t.name, at.source FROM tags t "
                "JOIN asset_tags at ON t.id=at.tag_id WHERE at.asset_id=?",
                (item["id"],),
            )
            item["tags"] = [dict(t) for t in tags]
            items.append(item)
        # Counts grouped by asset_type for this node
        cnt_rows = db.execute(
            "SELECT a.asset_type, COUNT(*) as count FROM assets a "
            "JOIN node_assets na ON a.id=na.asset_id "
            "WHERE na.node_id=? AND a.status='active' GROUP BY a.asset_type",
            (node_id,),
        )
        counts = {"image": 0, "video": 0, "audio": 0, "document": 0}
        for r in cnt_rows:
            counts[r["asset_type"]] = r["count"]
        return {"items": items, "total": len(items), "counts": counts}

    @app.post("/api/nodes/{node_id}/analyze-append")
    async def analyze_append_node(node_id: int):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="node_not_found")
        node_row = db.execute("SELECT * FROM nodes WHERE id=?", (node_id,))[0]
        node_info = dict(node_row)
        print(f"[AnalyzeAppend] 节点: {node_info['name']} (id={node_id})", flush=True)

        # Get existing assets in this node
        node_assets = db.execute(
            "SELECT a.id, filename, ai_summary, visual_description, video_summary FROM assets a "
            "JOIN node_assets na ON a.id=na.asset_id WHERE na.node_id=?",
            (node_id,),
        )
        existing_assets = [dict(r) for r in node_assets]

        # Get all assets NOT connected to this node
        candidates = db.execute(
            "SELECT id, filename, asset_type, ai_summary, visual_description FROM assets "
            "WHERE status='active' AND id NOT IN "
            "(SELECT asset_id FROM node_assets WHERE node_id=?)",
            (node_id,),
        )
        candidate_list = [dict(r) for r in candidates]
        print(f"[AnalyzeAppend] 已有素材: {len(existing_assets)}, 候选素材: {len(candidate_list)}", flush=True)

        if not candidate_list:
            print(f"[AnalyzeAppend] 无候选素材，跳过 AI 调用", flush=True)
            return {"ok": True, "added": 0}

        # Build prompt and call AI
        from quickmedia.aggregation.prompts import build_append_prompt
        from quickmedia.ai_worker import AIWorker
        from quickmedia.config import Config

        config_dir = app.extra["config_dir"]
        cfg = Config(config_dir=config_dir)
        worker = AIWorker(db=db, config=cfg)
        try:
            adapter = worker._get_adapter("aggregation")
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))

        from quickmedia.prompt_config import get_current_language
        prompt = build_append_prompt(node_info, existing_assets, candidate_list, get_current_language())
        response = adapter.chat(prompt)

        # Parse JSON response
        import json, re
        try:
            match = re.search(r"\{[^{}]*\"asset_ids\"[^{}]*\}", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                asset_ids = parsed.get("asset_ids", [])
            else:
                asset_ids = []
        except Exception:
            asset_ids = []

        # Add matching assets to node
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

        from quickmedia.api.server import broadcast_graph_changed
        await broadcast_graph_changed()
        print(f"[AnalyzeAppend] 完成: 添加 {added} 个素材到节点 {node_info['name']}", flush=True)
        return {"ok": True, "added": added}

