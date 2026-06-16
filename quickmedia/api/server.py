"""QuickMedia FastAPI server."""

import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from quickmedia.database import Database
from quickmedia.config import Config


def create_app(db: Database, cfg: Config, thumb_dir: str) -> FastAPI:
    app = FastAPI(title="QuickMedia", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.extra["db_path"] = db.conn.execute(
        "PRAGMA database_list"
    ).fetchall()[0][2]
    app.extra["config_dir"] = cfg.config_dir
    app.extra["thumb_dir"] = thumb_dir

    # ── Frontend static files ────────────────────────────────────

    frontend_dist = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "frontend", "dist"
    )

    if os.path.isdir(frontend_dist):
        app.mount("/assets", StaticFiles(
            directory=os.path.join(frontend_dist, "assets")
        ), name="assets")

    # ── Assets API ───────────────────────────────────────────────

    @app.get("/api/assets")
    def list_assets(
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        type: str | None = Query(None),
        formats: str | None = Query(None),
        date_from: str | None = Query(None),
        date_to: str | None = Query(None),
        mdate_from: str | None = Query(None),
        mdate_to: str | None = Query(None),
        tags: str | None = Query(None),
        ai_status: str | None = Query(None),
    ):
        _db = _get_db(app)
        conditions = ["a.status='active'"]
        params = []

        if type:
            conditions.append("a.asset_type=?")
            params.append(type)

        if formats:
            fmt_list = [f".{f.strip().lower()}" for f in formats.split(",")]
            placeholders = ",".join("?" * len(fmt_list))
            conditions.append(f"a.extension IN ({placeholders})")
            params.extend(fmt_list)

        if date_from:
            conditions.append("a.created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("a.created_at <= ?")
            params.append(date_to)
        if mdate_from:
            conditions.append("a.modified_at >= ?")
            params.append(mdate_from)
        if mdate_to:
            conditions.append("a.modified_at <= ?")
            params.append(mdate_to)
        if ai_status:
            status_list = ai_status.split(",")
            placeholders = ",".join("?" * len(status_list))
            conditions.append(f"COALESCE(aq.status, '-') IN ({placeholders})")
            params.extend(status_list)
        if tags:
            tag_ids = [int(t) for t in tags.split(",")]
            # Union: asset with ANY of the specified tags
            tag_placeholders = ",".join("?" * len(tag_ids))
            conditions.append(
                f"a.id IN (SELECT DISTINCT asset_id FROM asset_tags "
                f"WHERE tag_id IN ({tag_placeholders}))"
            )
            params.extend(tag_ids)

        where_clause = " AND ".join(conditions)

        base_select = """SELECT a.id, a.filename, a.asset_type, a.size,
                   a.width, a.height, a.duration, a.path, a.description,
                   a.ai_description, a.thumbnail_status, a.modified_at,
                   a.extension,
                   CASE WHEN aq.status IS NOT NULL THEN aq.status
                        WHEN a.ai_description IS NOT NULL OR a.ai_summary IS NOT NULL THEN 'done'
                        ELSE 'pending'
                   END as ai_status"""
        base_from = """FROM assets a
                   LEFT JOIN (
                       SELECT asset_id,
                         CASE WHEN SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END) > 0
                              THEN 'processing'
                              ELSE MAX(status)
                         END as status
                       FROM ai_queue
                       WHERE id IN (SELECT MAX(id) FROM ai_queue GROUP BY asset_id, task_type)
                       GROUP BY asset_id
        ) aq ON a.id = aq.asset_id"""

        if ai_status or tags:
            total_row = _db.execute(
                f"SELECT COUNT(*) as c FROM ({base_select} {base_from} WHERE {where_clause})",
                tuple(params),
            )
        else:
            total_row = _db.execute(
                f"SELECT COUNT(*) as c FROM assets a WHERE {where_clause}",
                tuple(params),
            )
        rows = _db.execute(
            f"""{base_select}
               {base_from}
               WHERE {where_clause}
               ORDER BY a.filename LIMIT ? OFFSET ?""",
            tuple(params) + (limit, offset),
        )
        items = [dict(r) for r in rows]
        for item in items:
            tags = _db.get_asset_tags(item["id"])
            item["tags"] = [dict(t) for t in tags]
        return {"total": total_row[0]["c"], "items": items}

    @app.get("/api/assets/{asset_id}")
    def get_asset(asset_id: int):
        _db = _get_db(app)
        rows = _db.execute(
            "SELECT * FROM assets WHERE id=?", (asset_id,)
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        result = dict(rows[0])
        tags = _db.get_asset_tags(asset_id)
        result["tags"] = [dict(t) for t in tags]
        # AI status: prioritize 'processing', else the latest status
        ai_rows = _db.execute(
            """SELECT status FROM ai_queue WHERE asset_id=?
               ORDER BY CASE WHEN status='processing' THEN 0 ELSE 1 END, id DESC
               LIMIT 1""",
            (asset_id,),
        )
        result["ai_status"] = ai_rows[0]["status"] if ai_rows else (
            "done" if (result.get("ai_description") or result.get("ai_summary")) else "pending"
        )
        return result

    @app.put("/api/assets/{asset_id}")
    def update_asset(asset_id: int, body: dict):
        _db = _get_db(app)
        if "description" in body:
            _db.execute(
                "UPDATE assets SET description=? WHERE id=?",
                (body["description"], asset_id),
            )
        if "notes" in body:
            _db.execute(
                "UPDATE assets SET notes=? WHERE id=?",
                (body["notes"], asset_id),
            )
        return {"ok": True}

    @app.delete("/api/assets/{asset_id}")
    def delete_asset(asset_id: int):
        """Delete an asset and all related data from the database."""
        _db = _get_db(app)
        rows = _db.execute("SELECT id FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        # CASCADE handles ai_queue, asset_tags, thumbnail_queue
        _db.conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        _db.conn.commit()
        return {"ok": True, "message": "已删除"}

    # ── Thumbnails ──────────────────────────────────────────────

    @app.get("/api/thumbnails/{asset_id}")
    def get_thumbnail(asset_id: int):
        thumb_path = os.path.join(thumb_dir, f"{asset_id}.jpg")
        if not os.path.isfile(thumb_path):
            raise HTTPException(status_code=404, detail="No thumbnail")
        return FileResponse(thumb_path, media_type="image/jpeg")

    # ── Search ──────────────────────────────────────────────────

    @app.get("/api/search")
    def search(q: str = Query(..., min_length=1)):
        _db = _get_db(app)
        results = _db.search(q)
        items = [dict(r) for r in results]
        for item in items:
            tags = _db.get_asset_tags(item["id"])
            item["tags"] = [dict(t) for t in tags]
        return items

    # ── Tags ────────────────────────────────────────────────────

    @app.get("/api/tags")
    def list_tags():
        _db = _get_db(app)
        return [dict(t) for t in _db.list_tags()]

    @app.post("/api/tags")
    def create_tag(body: dict):
        _db = _get_db(app)
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Tag name required")
        tag_id = _db.create_tag(name)
        return {"id": tag_id, "name": name}

    @app.post("/api/assets/{asset_id}/tags/{tag_id}")
    def add_tag(asset_id: int, tag_id: int):
        _db = _get_db(app)
        _db.tag_asset(asset_id, tag_id)
        return {"ok": True}

    @app.post("/api/assets/{asset_id}/tags/by-name")
    def add_tag_by_name(asset_id: int, body: dict):
        _db = _get_db(app)
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Tag name required")
        tag_id = _db.create_tag(name)
        _db.tag_asset(asset_id, tag_id)
        return {"id": tag_id, "name": name}

    @app.delete("/api/assets/{asset_id}/tags/{tag_id}")
    def remove_tag(asset_id: int, tag_id: int):
        _db = _get_db(app)
        _db.remove_tag(asset_id, tag_id)
        return {"ok": True}

    # ── Stats ───────────────────────────────────────────────────

    @app.get("/api/stats")
    def stats():
        _db = _get_db(app)
        return _db.get_stats()

    # ── AI Analysis ──────────────────────────────────────────────

    @app.post("/api/assets/{asset_id}/retry-ai")
    def retry_ai(asset_id: int):
        """Reset failed AI tasks to pending so the worker picks them up again."""
        _db = _get_db(app)
        cursor = _db.conn.execute(
            "UPDATE ai_queue SET status='pending', attempt=0, error=NULL "
            "WHERE asset_id=? AND status='failed'",
            (asset_id,),
        )
        _db.conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="No failed AI tasks found")
        return {"ok": True, "message": "已重置待重试"}

    @app.post("/api/assets/{asset_id}/reanalyze")
    def reanalyze_asset(asset_id: int):
        """Clear AI results and re-enqueue all analysis tasks for an asset."""
        _db = _get_db(app)
        rows = _db.execute("SELECT id, asset_type FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        asset_type = rows[0]["asset_type"]
        # Clear existing AI results
        _db.conn.execute(
            "UPDATE assets SET ai_description=NULL, ai_summary=NULL, "
            "ocr_text=NULL, transcript=NULL, video_summary=NULL, "
            "analyzed_at=NULL WHERE id=?",
            (asset_id,),
        )
        # Clear old auto-generated tags
        _db.conn.execute(
            "DELETE FROM asset_tags WHERE asset_id=? AND source='auto'",
            (asset_id,),
        )
        # Reset existing queue entries
        _db.conn.execute(
            "DELETE FROM ai_queue WHERE asset_id=?", (asset_id,)
        )
        _db.conn.commit()
        # Re-enqueue based on asset type
        if asset_type == "image":
            _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'vision')", (asset_id,))
        elif asset_type == "video":
            _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'vision')", (asset_id,))
            _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'transcribe')", (asset_id,))
        elif asset_type == "audio":
            _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'transcribe')", (asset_id,))
        elif asset_type == "document":
            _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'text')", (asset_id,))
        return {"ok": True, "message": "已重新入队分析任务"}

    @app.post("/api/assets/batch-reanalyze")
    def batch_reanalyze(body: dict):
        """Re-analyze multiple assets at once."""
        asset_ids = body.get("asset_ids", [])
        for aid in asset_ids:
            _db = _get_db(app)
            rows = _db.execute("SELECT id, asset_type FROM assets WHERE id=?", (aid,))
            if not rows:
                continue
            asset_type = rows[0]["asset_type"]
            _db.conn.execute(
                "UPDATE assets SET ai_description=NULL, ai_summary=NULL, "
                "ocr_text=NULL, transcript=NULL, video_summary=NULL, "
                "analyzed_at=NULL WHERE id=?",
                (aid,),
            )
            _db.conn.execute("DELETE FROM ai_queue WHERE asset_id=?", (aid,))
            _db.conn.commit()
            if asset_type == "image":
                _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'vision')", (aid,))
            elif asset_type == "video":
                _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'vision')", (aid,))
                _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'transcribe')", (aid,))
            elif asset_type == "audio":
                _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'transcribe')", (aid,))
            elif asset_type == "document":
                _db.execute("INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'text')", (aid,))
        return {"ok": True, "message": f"已重新入队 {len(asset_ids)} 个素材"}

    @app.post("/api/assets/{asset_id}/analyze")
    def analyze_asset(asset_id: int):
        from quickmedia.ai import VisionAnalyzer
        _db = _get_db(app)
        rows = _db.execute("SELECT path FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        path = rows[0]["path"]
        analyzer = VisionAnalyzer(timeout=300)
        result = analyzer.analyze(path)
        if result.get("description"):
            _db.execute(
                "UPDATE assets SET ai_description=? WHERE id=?",
                (result["description"], asset_id),
            )
        if result.get("ocr_text"):
            _db.execute(
                "UPDATE assets SET ocr_text=? WHERE id=?",
                (result["ocr_text"], asset_id),
            )
        if result.get("tags"):
            for tag_name in result["tags"]:
                tag_id = _db.create_tag(tag_name)
                _db.tag_asset(asset_id, tag_id)
        return result

    # ── Config ───────────────────────────────────────────────────

    @app.get("/api/config")
    def get_config():
        cfg = Config()
        return {
            "ollama_url": cfg.get("ai.ollama_url"),
            "model": cfg.get("ai.model"),
            "video_frames": cfg.get("ai.video_frames"),
            "timeout": cfg.get("ai.timeout"),
        }

    @app.put("/api/config")
    def update_config(body: dict):
        cfg = Config()
        if "ollama_url" in body:
            cfg.set("ai.ollama_url", body["ollama_url"])
        if "model" in body:
            cfg.set("ai.model", body["model"])
        if "video_frames" in body:
            cfg.set("ai.video_frames", int(body["video_frames"]))
        if "timeout" in body:
            cfg.set("ai.timeout", int(body["timeout"]))
        return {"ok": True}

    @app.post("/api/config/test-ollama")
    def test_ollama():
        try:
            import urllib.request, json
            cfg = Config()
            url = f"{cfg.get('ai.ollama_url')}/api/tags"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                return {"connected": True, "models": models}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    # ── Prompts ──────────────────────────────────────────────────

    @app.get("/api/prompts")
    def get_prompts():
        from quickmedia.prompt_config import PromptConfig
        pc = PromptConfig(config_dir=app.extra["config_dir"])
        return pc.get_config()

    @app.put("/api/prompts")
    def update_prompts(body: dict):
        from quickmedia.prompt_config import PromptConfig
        pc = PromptConfig(config_dir=app.extra["config_dir"])
        analysis_type = body.get("type", "")
        custom = body.get("custom", "")
        if analysis_type not in ("vision", "text", "speech", "video_summary"):
            raise HTTPException(status_code=400, detail="Invalid analysis type")
        pc.update_custom(analysis_type, custom)
        return {"ok": True}

    # ── Finder ───────────────────────────────────────────────────

    @app.post("/api/finder/open")
    def open_finder(body: dict):
        path = body.get("path", "")
        if path and os.path.exists(path):
            import subprocess
            subprocess.run(["open", "-R", path])
            return {"ok": True}
        raise HTTPException(status_code=404, detail="Path not found")

    # ── Scan ──────────────────────────────────────────────────────

    @app.post("/api/scan")
    def scan_watch_paths():
        """Scan all configured watch paths for new/modified files."""
        from quickmedia.scanner import Scanner
        cfg = Config(config_dir=app.extra["config_dir"])
        _db = _get_db(app)
        scanner = Scanner(db=_db, config=cfg)
        watch_paths = cfg.get("watch_paths") or []
        total_new = 0
        for wp in watch_paths:
            path = os.path.expanduser(wp.get("path", ""))
            if os.path.isdir(path):
                result = scanner.scan_directory(
                    path,
                    recursive=wp.get("recursive", True),
                    max_depth=wp.get("max_depth", 3),
                )
                total_new += result["new"]
        _db.close()
        return {"ok": True, "new": total_new, "message": f"新增 {total_new} 个素材"}

    # ── Frontend SPA ─────────────────────────────────────────────

    @app.get("/")
    def index():
        if os.path.isdir(frontend_dist):
            return FileResponse(os.path.join(frontend_dist, "index.html"))
        return {"message": "QuickMedia API"}

    return app


def _get_db(app: FastAPI) -> Database:
    """Get a fresh Database connection for the current request."""
    return Database(app.extra["db_path"])
