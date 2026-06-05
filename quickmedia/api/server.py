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
    ):
        _db = _get_db(app)
        if type:
            total_row = _db.execute(
                "SELECT COUNT(*) as c FROM assets WHERE status='active' AND asset_type=?",
                (type,),
            )
            rows = _db.execute(
                """SELECT id, filename, asset_type, size, width, height, duration,
                   path, description, ai_description, thumbnail_status, modified_at
                   FROM assets WHERE status='active' AND asset_type=?
                   ORDER BY filename LIMIT ? OFFSET ?""",
                (type, limit, offset),
            )
        else:
            total_row = _db.execute(
                "SELECT COUNT(*) as c FROM assets WHERE status='active'"
            )
            rows = _db.execute(
                """SELECT id, filename, asset_type, size, width, height, duration,
                   path, description, ai_description, thumbnail_status, modified_at
                   FROM assets WHERE status='active'
                   ORDER BY filename LIMIT ? OFFSET ?""",
                (limit, offset),
            )
        items = [dict(r) for r in rows]
        # Add tags to each item
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

    @app.post("/api/assets/{asset_id}/analyze")
    def analyze_asset(asset_id: int):
        from quickmedia.ai import VisionAnalyzer
        _db = _get_db(app)
        rows = _db.execute("SELECT path FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        path = rows[0]["path"]
        analyzer = VisionAnalyzer()
        result = analyzer.analyze(path)
        if result.get("description"):
            _db.execute(
                "UPDATE assets SET ai_description=? WHERE id=?",
                (result["description"], asset_id),
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
        }

    @app.put("/api/config")
    def update_config(body: dict):
        cfg = Config()
        if "ollama_url" in body:
            cfg.set("ai.ollama_url", body["ollama_url"])
        if "model" in body:
            cfg.set("ai.model", body["model"])
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
