"""QuickMedia FastAPI server."""

import os
from fastapi import FastAPI, Request, Query, HTTPException, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from quickmedia.database import Database
from quickmedia.config import Config

# WebSocket connection pool
_graph_ws_clients: list = []

async def broadcast_graph_changed():
    """Push graph_changed event to all connected WebSocket clients."""
    import asyncio
    disconnected = []
    for ws in _graph_ws_clients:
        try:
            await ws.send_json({"event": "graph_changed"})
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _graph_ws_clients.remove(ws)


def _parse_osascript_path(output: str):
    """Parse osascript choose folder output. Returns path or None."""
    if not output or not output.strip():
        return None
    out = output.strip()
    if "User cancelled" in out or "execution error" in out.lower():
        return None
    if out.startswith("alias "):
        parts = out[6:].rstrip(":").split(":")
        parts = [x for x in parts if x]
        if len(parts) > 1 and ":" in out[6:]:
            p = "/" + "/".join(parts[1:])
        elif parts:
            p = "/".join(parts) if parts[0].startswith("/") else "/" + "/".join(parts)
        else:
            return None
        return p if p else None
    return out if os.path.isdir(out) else None


def create_app(db: Database, cfg: Config, thumb_dir: str) -> FastAPI:
    app = FastAPI(title="QuickMedia", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Read language cookie for AI prompts
    @app.middleware("http")
    async def detect_language(request: Request, call_next):
        from quickmedia.prompt_config import set_current_language
        lang = request.cookies.get("qm_lang", "zh")
        set_current_language(lang)
        response = await call_next(request)
        return response

    app.extra["db_path"] = db.conn.execute(
        "PRAGMA database_list"
    ).fetchall()[0][2]
    app.extra["config_dir"] = cfg.config_dir
    app.extra["thumb_dir"] = thumb_dir

    # V12: Aggregation routes
    from quickmedia.aggregation.api import register_aggregation_routes
    register_aggregation_routes(app)

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
        # For counts we exclude the type filter so sidebar shows full distribution
        counts_conditions = ["a.status='active'"]
        counts_params = []

        if type:
            conditions.append("a.asset_type=?")
            params.append(type)
            # NOT added to counts_conditions — type filter excluded from counts

        if formats:
            fmt_list = [f".{f.strip().lower()}" for f in formats.split(",")]
            placeholders = ",".join("?" * len(fmt_list))
            conditions.append(f"a.extension IN ({placeholders})")
            params.extend(fmt_list)
            counts_conditions.append(f"a.extension IN ({placeholders})")
            counts_params.extend(fmt_list)

        if date_from:
            conditions.append("a.created_at >= ?")
            params.append(date_from)
            counts_conditions.append("a.created_at >= ?")
            counts_params.append(date_from)
        if date_to:
            conditions.append("a.created_at <= ?")
            params.append(date_to)
            counts_conditions.append("a.created_at <= ?")
            counts_params.append(date_to)
        if mdate_from:
            conditions.append("a.modified_at >= ?")
            params.append(mdate_from)
            counts_conditions.append("a.modified_at >= ?")
            counts_params.append(mdate_from)
        if mdate_to:
            conditions.append("a.modified_at <= ?")
            params.append(mdate_to)
            counts_conditions.append("a.modified_at <= ?")
            counts_params.append(mdate_to)
        if ai_status:
            status_list = ai_status.split(",")
            placeholders = ",".join("?" * len(status_list))
            conditions.append(f"a.ai_status IN ({placeholders})")
            params.extend(status_list)
            counts_conditions.append(f"a.ai_status IN ({placeholders})")
            counts_params.extend(status_list)
        if tags:
            tag_ids = [int(t) for t in tags.split(",")]
            tag_placeholders = ",".join("?" * len(tag_ids))
            tag_cond = (
                f"a.id IN (SELECT DISTINCT asset_id FROM asset_tags "
                f"WHERE tag_id IN ({tag_placeholders}))"
            )
            conditions.append(tag_cond)
            params.extend(tag_ids)
            counts_conditions.append(tag_cond)
            counts_params.extend(tag_ids)

        where_clause = " AND ".join(conditions)
        counts_where = " AND ".join(counts_conditions)

        base_select = """SELECT a.id, a.filename, a.asset_type, a.size,
                   a.width, a.height, a.duration, a.path, a.description,
                   a.visual_description, a.thumbnail_status, a.modified_at,
                   a.extension,
                   a.ai_status"""
        base_from = """FROM assets a"""

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
        # Counts grouped by asset_type (same filter minus type, full set, not limited)
        if ai_status or tags:
            counts_rows = _db.execute(
                f"SELECT asset_type, COUNT(*) as count FROM ({base_select} {base_from} WHERE {counts_where}) GROUP BY asset_type",
                tuple(counts_params),
            )
        else:
            counts_rows = _db.execute(
                f"SELECT a.asset_type, COUNT(*) as count FROM assets a WHERE {counts_where} GROUP BY a.asset_type",
                tuple(counts_params),
            )
        counts = {"image": 0, "video": 0, "audio": 0, "document": 0}
        for row in counts_rows:
            counts[row["asset_type"]] = row["count"]
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
            # Add doc_preview for document types
            if item.get("asset_type") == "document":
                try:
                    p = item.get("path", "")
                    if p and os.path.isfile(p):
                        ext = os.path.splitext(p)[1].lower()
                        if ext in {".txt", ".md", ".docx"}:
                            text = ""
                            if ext == ".docx":
                                try:
                                    import docx
                                    doc = docx.Document(p)
                                    lines = []
                                    for para in doc.paragraphs[:3]:
                                        t = para.text.strip()[:80]
                                        if t:
                                            lines.append(t)
                                    text = "\n".join(lines)
                                except ImportError:
                                    pass
                            else:
                                with open(p, "r", errors="replace") as f:
                                    lines = [f.readline().strip()[:80] for _ in range(3)]
                                    text = "\n".join(l for l in lines if l)
                            if text:
                                item["doc_preview"] = text[:200]
                except Exception:
                    pass
        return {"total": total_row[0]["c"], "items": items, "counts": counts}

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
        result["ai_status"] = result.get("ai_status")
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
        """Delete an asset and all related data."""
        _db = _get_db(app)
        cfg = Config(config_dir=app.extra["config_dir"])
        from quickmedia.asset_ops import delete_asset_full
        result = delete_asset_full(_db, cfg, asset_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("error", "not found"))
        return result

    # ── Thumbnails ──────────────────────────────────────────────

    @app.get("/api/thumbnails/{asset_id}")
    def get_thumbnail(asset_id: int):
        thumb_path = os.path.join(thumb_dir, f"{asset_id}.jpg")
        if not os.path.isfile(thumb_path):
            raise HTTPException(status_code=404, detail="No thumbnail")
        return FileResponse(thumb_path, media_type="image/jpeg")


    @app.get("/api/search")
    def search(q: str = Query("", min_length=0), mode: str = "keyword"):
        print(f"[Search] mode={mode} q={repr(q)}", flush=True)
        _db = _get_db(app)

        def _count_by_type(items):
            cnt = {"image": 0, "video": 0, "audio": 0, "document": 0}
            for it in items:
                t = it.get("asset_type", "")
                if t in cnt:
                    cnt[t] += 1
            return cnt

        # Handle empty query
        if not q.strip():
            return {"items": [], "counts": {"image": 0, "video": 0, "audio": 0, "document": 0}}

        # AI mode: LLM-based search
        if mode == "ai":
            try:
                from quickmedia.search import search_ai_assets
                cfg = Config(config_dir=app.extra["config_dir"])
                items = search_ai_assets(q, _db, cfg, app.extra["config_dir"])
                return {"items": items, "counts": _count_by_type(items)}
            except Exception as e:
                print(f"[AI search] error: {e}", flush=True)
                return {"items": [], "counts": {"image": 0, "video": 0, "audio": 0, "document": 0}}

        # Tokenize query for keyword search
        try:
            import jieba
            tokens = [t for t in jieba.cut_for_search(q) if t.strip()]
        except ImportError:
            tokens = [q]
        if not tokens:
            tokens = [q]

        keyword_results = _db.search_tokens(tokens) if len(tokens) > 1 else _db.search(q)
        items = [dict(r) for r in keyword_results]
        print(f"[Keyword search] tokens={tokens} results={len(items)}", flush=True)
        for item in items[:10]:
            print("  " + str(item.get("filename","?")), flush=True)
        for item in items:
            tags = _db.get_asset_tags(item["id"])
            item["tags"] = [dict(t) for t in tags]
        # For semantic/combined modes, also query embeddings
        warning = None
        if mode in ("semantic", "combined"):
            binding = {}
            try:
                from quickmedia.embedding import ChromaStore
                from quickmedia.ai_worker import EmbeddingAdapter
                cfg = Config(config_dir=app.extra["config_dir"])
                chroma_path = os.path.join(app.extra["config_dir"], "chroma_db")
                if os.path.isdir(chroma_path):
                    store = ChromaStore(persist_path=chroma_path)
                    # Get embedding adapter
                    from quickmedia.search import get_embedding_adapter
                    adapter, binding = get_embedding_adapter(cfg, app.extra["config_dir"])
                    if adapter:
                        query_vector = adapter.embed(q)
                        k = cfg.get("semantic.top_k") or 2
                        similar = store.query_search_terms(query_vector, k=k, n_results=50)
                        pass  # removed [:20] truncation
                        print(f"[Semantic search] query='{q}' provider={binding['provider']} model={binding['model']} results={len(similar)}", flush=True)
                        for s in similar:
                            row = _db.execute("SELECT filename FROM assets WHERE id=?", (s["asset_id"],))
                            name = row[0]["filename"] if row else f"unknown({s['asset_id']})"
                            details = s.get("top_k_details", [])
                            all_terms = {i: t["term"] for i, t in enumerate(_db.execute("SELECT term FROM asset_search_terms WHERE asset_id=?", (s["asset_id"],)))}
                            parts = []
                            for d in details:
                                tname = d.get("term_name") or all_terms.get(d["term_index"]) or f"t{d['term_index']}"
                                parts.append(f"{tname}={d['distance']:.4f}")
                            dstr = " | ".join(parts) if parts else "no terms"
                            print(f"  {s['distance']:.4f}  {name}  ({dstr})", flush=True)

                        # Semantic mode: return pure semantic results, no keyword fusion
                        if mode == "semantic":
                            result = []
                            kw_ids = {item["id"] for item in items} if items else set()
                            best_dist = similar[0]["distance"] if similar else 1.0
                            ref = best_dist if best_dist > 0.001 else 0.001
                            for s in similar:
                                rows = _db.execute("SELECT * FROM assets WHERE id=?", (s["asset_id"],))
                                if rows:
                                    item = dict(rows[0])
                                    tags = _db.get_asset_tags(s["asset_id"])
                                    item["tags"] = [dict(t) for t in tags]
                                    item["_distance"] = s["distance"]
                                    if s["asset_id"] in kw_ids:
                                        if best_dist == 0 and s["distance"] == 0: item["_stars"] = 5
                                        elif best_dist == 0: pass
                                        else:
                                            ratio = s["distance"] / ref
                                            if ratio <= 1.0: item["_stars"] = 5
                                            elif ratio <= 1.5: item["_stars"] = 4
                                            elif ratio <= 2.0: item["_stars"] = 3
                                            elif ratio <= 2.5: item["_stars"] = 2
                                            elif ratio <= 3.0: item["_stars"] = 1
                                    result.append(item)
                            return {"items": result, "counts": _count_by_type(result)}

                        # RRF fusion: merge keyword + vector results by rank
                        # Build rank maps (1-indexed)
                        kw_rank = {item["id"]: i + 1 for i, item in enumerate(items)}
                        vec_rank = {s["asset_id"]: i + 1 for i, s in enumerate(similar)}

                        all_ids = set(kw_rank.keys()) | set(vec_rank.keys())
                        rrf_scores = {}
                        for aid in all_ids:
                            score = 0.0
                            if aid in kw_rank:
                                score += 1.0 / (60 + kw_rank[aid])
                            if aid in vec_rank:
                                score += 1.0 / (60 + vec_rank[aid])
                            rrf_scores[aid] = score

                        # Build merged items sorted by RRF score
                        merged_items = []
                        seen = set()
                        for aid, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
                            rows = _db.execute("SELECT * FROM assets WHERE id=?", (aid,))
                            if rows:
                                item = dict(rows[0])
                                tags = _db.get_asset_tags(aid)
                                item["tags"] = [dict(t) for t in tags]
                                item["_rrf_score"] = score
                                merged_items.append(item)
                                seen.add(aid)

                        # Compute star: items within 3x best distance that are also in keyword results
                        best_dist = similar[0]["distance"] if similar else 1.0
                        star_map = {}
                        if kw_rank:
                            for s in similar:
                                if s["asset_id"] in kw_rank:
                                    ref = best_dist if best_dist > 0.001 else 0.001
                                    ratio = s["distance"] / ref
                                    if ratio <= 1.0: n = 5
                                    elif ratio <= 1.5: n = 4
                                    elif ratio <= 2.0: n = 3
                                    elif ratio <= 2.5: n = 2
                                    elif ratio <= 3.0: n = 1
                                    else: n = 0
                                    if n > 0: star_map[s["asset_id"]] = n

                        if mode == "semantic":
                            items = [it for it in merged_items if it["id"] in vec_rank]
                        else:  # combined
                            items = merged_items
                            for it in items:
                                if it["id"] in star_map:
                                    it["_stars"] = star_map[it["id"]]

                        # Log RRF fusion results
                        print(f"[RRF fusion] tokens={tokens} total={len(items)}", flush=True)
                        for item in items[:10]:
                            source = ""
                            if item["id"] in kw_rank:
                                source += f"KW#{kw_rank[item['id']]}"
                            if item["id"] in vec_rank:
                                source += f" +VEC#{vec_rank[item['id']]}" if source else f"VEC#{vec_rank[item['id']]}"
                            rows = _db.execute("SELECT filename FROM assets WHERE id=?", (item["id"],))
                            name = rows[0]["filename"] if rows else "?"
                            print(f"  {item['_rrf_score']:.4f}  {name}  [{source}]", flush=True)
            except Exception as e:
                # Semantic search failure should not break the request
                print(f"Semantic search error: {e}", flush=True)
                provider = binding.get("provider", "ollama") if binding else "ollama"
                warning = f"语义搜索失败（{provider}: {e}）"

        return {"items": items, "counts": _count_by_type(items), "warning": warning if warning else None}

    # ── Graph API ─────────────────────────────────────────────────

    @app.get("/api/graph")
    def get_graph():
        _db = _get_db(app)
        nodes = [dict(r) for r in _db.execute(
            "SELECT n.id, n.name, n.description, "
            "COUNT(na.asset_id) as asset_count "
            "FROM nodes n LEFT JOIN node_assets na ON n.id=na.node_id "
            "GROUP BY n.id"
        )]
        edges = [dict(r) for r in _db.execute(
            "SELECT na.node_id, na.asset_id, a.filename, a.asset_type, "
            "a.ai_summary, a.thumbnail_status "
            "FROM node_assets na JOIN assets a ON a.id=na.asset_id"
        )]
        unassigned = [dict(r) for r in _db.execute(
            "SELECT a.id, a.filename, a.asset_type, a.thumbnail_status "
            "FROM assets a WHERE a.status='active' "
            "AND a.id NOT IN (SELECT DISTINCT asset_id FROM node_assets)"
        )]
        return {"nodes": nodes, "edges": edges, "unassigned": unassigned}

    @app.websocket("/ws/graph")
    async def ws_graph(websocket: WebSocket):
        await websocket.accept()
        _graph_ws_clients.append(websocket)
        try:
            while True:
                await websocket.receive_text()  # keepalive
        except WebSocketDisconnect:
            pass
        finally:
            if websocket in _graph_ws_clients:
                _graph_ws_clients.remove(websocket)

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

    
    @app.post("/api/folder-picker")
    def folder_picker():
        """Open macOS folder picker and return selected path."""
        import subprocess
        try:
            result = subprocess.run(
                ["osascript", "-e", "choose folder"],
                capture_output=True, text=True, timeout=30,
            )
            path = _parse_osascript_path(result.stdout)
            if path:
                return {"path": path}
            return {"error": "no_folder_selected", "path": None}
        except FileNotFoundError:
            return {"error": "仅支持 macOS", "path": None}
        except Exception as e:
            return {"error": str(e), "path": None}

    @app.post("/api/file-picker")
    def file_picker():
        """Open macOS file picker and return selected path."""
        import subprocess
        try:
            result = subprocess.run(
                ["osascript", "-e", "choose file"],
                capture_output=True, text=True, timeout=30,
            )
            path = _parse_osascript_path(result.stdout)
            if path:
                return {"path": path}
            return {"error": "no_file_selected", "path": None}
        except FileNotFoundError:
            return {"error": "仅支持 macOS", "path": None}
        except Exception as e:
            return {"error": str(e), "path": None}

    @app.post("/api/scan-file")
    def scan_single_file(body: dict):
        """Scan a single file into the asset library."""
        from quickmedia.scanner import Scanner
        path = body.get("path", "")
        if not path or not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"文件不存在: {path}")
        db = _get_db(app)
        cfg = Config(config_dir=app.extra["config_dir"])
        scanner = Scanner(db=db, config=cfg)
        aid = scanner.scan_file(path)
        if aid:
            return {"ok": True, "asset_id": aid, "message": f"已添加 {os.path.basename(path)}"}
        return {"ok": False, "error": "add_failed"}

    @app.post("/api/scan-folder")
    def scan_single_folder(body: dict):
        """Scan a folder into the asset library."""
        from quickmedia.scanner import Scanner
        path = body.get("path", "")
        if not path or not os.path.isdir(path):
            raise HTTPException(status_code=400, detail=f"文件夹不存在: {path}")
        db = _get_db(app)
        cfg = Config(config_dir=app.extra["config_dir"])
        scanner = Scanner(db=db, config=cfg)
        result = scanner.scan_directory(path, recursive=True, max_depth=3)
        return {"ok": True, "message": f"已扫描 {path}", "result": result}

    @app.get("/api/task-models")
    def get_task_models():
        """Return current task model bindings."""
        cfg = Config(config_dir=app.extra["config_dir"])
        return cfg.get("task_models") or {}

    @app.get("/api/config/watch-paths")
    def get_watch_paths():
        """Return configured watch paths."""
        cfg = Config(config_dir=app.extra["config_dir"])
        return {"paths": cfg.get("watch_paths") or []}

    @app.put("/api/config/watch-paths")
    def update_watch_paths(data: dict = Body(...)):
        paths = data.get("paths", data) if isinstance(data, dict) else data
        """Save watch paths and trigger scanner reload."""
        cfg = Config(config_dir=app.extra["config_dir"])
        cfg.set("watch_paths", paths)
        cfg._save()
        # Trigger hot reload of watcher
        try:
            scanner = app.extra.get("scanner")
            if scanner:
                scanner.reload_watch_paths()
        except Exception:
            pass
        return {"ok": True, "message": f"已保存 {len(paths)} 条路径"}

    @app.get("/api/formats")
    def get_formats():
        cfg = Config(config_dir=app.extra["config_dir"])
        fmts = cfg.get("formats") or {}
        all_fmts = []
        for cat, exts in fmts.items():
            all_fmts.extend(exts)
        return sorted(set(all_fmts))
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
            "UPDATE assets SET visual_description=NULL, ai_summary=NULL, "
            "ocr_text=NULL, transcript=NULL, video_summary=NULL, "
            "analyzed_at=NULL WHERE id=?",
            (asset_id,),
        )
        # Clear old ChromaDB embeddings
        chroma_path = os.path.join(app.extra["config_dir"], "chroma_db")
        if os.path.isdir(chroma_path):
            from quickmedia.embedding import ChromaStore
            store = ChromaStore(persist_path=chroma_path)
            store.delete(asset_id)
        # Clear old auto-generated tags
        _db.conn.execute(
            "DELETE FROM asset_tags WHERE asset_id=? AND source='auto'",
            (asset_id,),
        )
        # Clear old search_terms
        _db.conn.execute("DELETE FROM asset_search_terms WHERE asset_id=?", (asset_id,))
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
                "UPDATE assets SET visual_description=NULL, ai_summary=NULL, "
                "ocr_text=NULL, transcript=NULL, video_summary=NULL, "
                "analyzed_at=NULL, ai_status='pending', ai_status_updated_at=datetime('now') WHERE id=?",
                (aid,),
            )
            # Clear old auto tags, search_terms, and embeddings
            _db.conn.execute("DELETE FROM asset_tags WHERE asset_id=? AND source='auto'", (aid,))
            _db.conn.execute("DELETE FROM asset_search_terms WHERE asset_id=?", (aid,))
            try:
                from quickmedia.embedding import ChromaStore
                store = ChromaStore(persist_path=os.path.join(app.extra["config_dir"], "chroma_db"))
                store.delete(aid)
            except Exception:
                pass

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

    @app.post("/api/assets/batch-delete")
    def batch_delete(body: dict):
        _db = _get_db(app)
        ids = body.get("ids", [])
        from quickmedia.asset_ops import delete_asset_full
        cfg = Config(config_dir=app.extra["config_dir"])
        deleted = 0
        for aid in ids:
            result = delete_asset_full(_db, cfg, aid)
            if result.get("ok"):
                deleted += 1
        return {"ok": True, "deleted": deleted}

    @app.delete("/api/ai-queue")
    def clear_queue():
        _db = _get_db(app)
        _db.execute(
            "UPDATE assets SET ai_status='cancelled', ai_status_updated_at=datetime('now') "
            "WHERE id IN (SELECT asset_id FROM ai_queue)"
        )
        _db.execute("DELETE FROM ai_queue")
        return {"ok": True}

    @app.get("/api/assets/{asset_id}/preview")
    def preview_asset(asset_id: int):
        _db = _get_db(app)
        rows = _db.execute("SELECT asset_type, path FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        asset_type = rows[0]["asset_type"]
        path = rows[0]["path"]
        if asset_type not in ("document",):
            return {"text": ""}
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()[:200]
            return {"text": text.strip()}
        except Exception:
            return {"text": ""}

    @app.get("/api/assets/{asset_id}/similar")
    def similar_assets(asset_id: int, limit: int = 10):
        _db = _get_db(app)
        rows = _db.execute("SELECT id, filename FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        cfg = Config(config_dir=app.extra["config_dir"])
        chroma_path = os.path.join(app.extra["config_dir"], "chroma_db")
        if not os.path.isdir(chroma_path):
            return []
        from quickmedia.embedding import ChromaStore
        from collections import defaultdict
        store = ChromaStore(persist_path=chroma_path)
        all_ids = store._collection.get()["ids"]
        src_vectors = [sid for sid in all_ids if sid.startswith(f"search_{asset_id}_")]
        if not src_vectors:
            return []
        per_match = defaultdict(list)
        for sid in src_vectors:
            v = store.get_vector(asset_id, "search", term_index=int(sid.rsplit("_", 1)[1]))
            if v:
                results = store._collection.query(query_embeddings=[v], n_results=limit * 5)
                if results and results["ids"] and results["ids"][0]:
                    for i, rid in enumerate(results["ids"][0]):
                        if rid.startswith("search_"):
                            mid = int(rid.split("_", 1)[1].rsplit("_", 1)[0])
                            dist = results["distances"][0][i] if results.get("distances") else 0
                            per_match[mid].append(dist)
        items = []
        for mid, dists in per_match.items():
            if mid == asset_id:
                continue
            items.append({"asset_id": mid, "distance": min(dists)})
        items.sort(key=lambda x: x["distance"])
        items = items[:limit]
        result = []
        src_name = rows[0]["filename"] if rows else str(asset_id)
        for i in items:
            row = _db.execute("SELECT * FROM assets WHERE id=?", (i["asset_id"],))
            if row:
                item = dict(row[0])
                tags = _db.get_asset_tags(item["id"])
                item["tags"] = [dict(t) for t in tags]
                result.append(item)
        print(f"[Semantic search] similar={src_name} results={len(result)}", flush=True)
        for i in items:
            r = _db.execute("SELECT filename FROM assets WHERE id=?", (i["asset_id"],))
            name = r[0]["filename"] if r else "unknown"
            print(f"  {i['distance']:.4f}  {name}", flush=True)
        return result[:limit]
        if not vector:
            return []
        similar = store.query(vector, n_results=limit + 1)
        # Filter by relative distance to best match
        if similar:
            best = similar[0].get("distance", 0)
            similar = [s for s in similar if s.get("distance", 1.0) < best * 1.2 and s["asset_id"] != asset_id]
        similar = similar[:limit]
        items = []
        # Log similar results
        name_rows = _db.execute("SELECT filename FROM assets WHERE id=?", (asset_id,))
        src_name = name_rows[0]["filename"] if name_rows else str(asset_id)
        print(f"[Semantic search] similar={src_name} results={len(similar)}", flush=True)
        for s in similar:
            r = _db.execute("SELECT * FROM assets WHERE id=?", (s["asset_id"],))
            if r:
                item = dict(r[0])
                tags = _db.get_asset_tags(item["id"])
                item["tags"] = [dict(t) for t in tags]
                item["_distance"] = s["distance"]
                items.append(item)
                print(f"  {s['distance']:.4f}  {item['filename']}", flush=True)
        return items

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
                "UPDATE assets SET visual_description=? WHERE id=?",
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
        # Read ollama info from provider system
        ollama_url = cfg.get("providers.ollama.url") or cfg.get("ai.ollama_url") or "http://localhost:11434"
        ollama_model = cfg.get("task_models.vision.model") or cfg.get("ai.model") or "qwen3.5:9b"
        return {
            "ollama_url": ollama_url,
            "model": ollama_model,
            "video_frames": cfg.get("ai.video_frames"),
            "timeout": cfg.get("ai.timeout"),
            "providers": cfg.get("providers") or {},
            "task_models": cfg.get("task_models") or {},
        }

    @app.put("/api/config")
    def update_config(body: dict):
        cfg = Config()
        if "ollama_url" in body:
            cfg.set("providers.ollama.url", body["ollama_url"])
        if "model" in body:
            for task in ("vision", "text", "speech", "video_summary"):
                cfg.set(f"task_models.{task}.model", body["model"])
        if "video_frames" in body:
            cfg.set("ai.video_frames", int(body["video_frames"]))
        if "timeout" in body:
            cfg.set("ai.timeout", int(body["timeout"]))
        return {"ok": True}

    @app.post("/api/config/test-ollama")
    def test_ollama():
        cfg = Config()
        url = cfg.get("providers.ollama.url") or cfg.get("ai.ollama_url") or "http://localhost:11434"
        url = url.rstrip("/") + "/v1"
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url=url, api_key="ollama", model="test", timeout=5)
        ok = adapter.test()
        return {"connected": ok, "error": "" if ok else "Connection failed"}

    # ── Prompts ──────────────────────────────────────────────────

    @app.get("/api/prompts")
    def get_prompts(request: Request):
        from quickmedia.prompt_config import PromptConfig
        lang = request.cookies.get("qm_lang", "zh")
        pc = PromptConfig(config_dir=app.extra["config_dir"], language=lang)
        return pc.get_all()

    @app.put("/api/prompts")
    def update_prompts(body: dict):
        from quickmedia.prompt_config import PromptConfig
        pc = PromptConfig(config_dir=app.extra["config_dir"])
        analysis_type = body.get("type", "")
        custom = body.get("custom", "")
        if analysis_type not in ("vision", "text", "speech", "video_summary", "search_ai",
                                  "aggregation_full", "aggregation_full_append",
                                  "aggregation_append", "aggregation_analyze_append"):
            raise HTTPException(status_code=400, detail="Invalid analysis type")
        pc.save(analysis_type, custom)
        return {"ok": True}

    # ── Providers ─────────────────────────────────────────────────

    @app.get("/api/providers")
    def get_providers():
        cfg = Config(config_dir=app.extra["config_dir"])
        providers = cfg.get("providers") or {}
        # Merge API keys from .env
        env_path = os.path.join(app.extra["config_dir"], ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        # Match provider name: OPENROUTER_API_KEY -> openrouter
                        if k.endswith("_API_KEY"):
                            pname = k[:-8].lower()
                            if pname in providers:
                                providers[pname] = dict(providers[pname])
                                providers[pname]["api_key"] = v
        return {
            "providers": providers,
            "task_models": cfg.get("task_models") or {},
        }

    @app.get("/api/providers/{provider_name}/models")
    def get_provider_models(provider_name: str):
        from quickmedia.providers import ProviderRegistry
        user_models = os.path.join(app.extra["config_dir"], "models.yaml")
        cfg = Config(config_dir=app.extra["config_dir"])
        registry = ProviderRegistry(cfg, user_models)
        models = registry.get_models(provider_name)
        return {"models": [{"name": m["name"], "capabilities": m.get("capabilities", [])} for m in models]}

    @app.put("/api/providers")
    def update_providers(body: dict):
        cfg = Config(config_dir=app.extra["config_dir"])
        providers = body.get("providers", {})
        task_models = body.get("task_models", {})

        # Save provider URLs to config.yaml, strip api_key
        config_providers = {}
        for name, p in providers.items():
            config_providers[name] = {"url": p.get("url", "")}

        # Save API keys to .env
        env_lines = []
        for name, p in providers.items():
            if p.get("api_key"):
                env_lines.append(f"{name.upper()}_API_KEY={p['api_key']}")

        # Write non-key settings to config.yaml
        cfg.set("providers", config_providers)
        cfg.set("task_models", task_models)

        # Write API keys to .env
        env_path = os.path.join(app.extra["config_dir"], ".env")
        existing = {}
        if os.path.isfile(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        existing[k] = v
        for line in env_lines:
            k, v = line.split("=", 1)
            existing[k] = v
        with open(env_path, "w") as f:
            for k, v in existing.items():
                f.write(f"{k}={v}\n")

        return {"ok": True}

    @app.post("/api/providers/test")
    def test_provider(body: dict):
        provider_name = body.get("provider", "")
        url = body.get("url", "")
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        # Read API key from .env for this provider
        api_key = ""
        env_path = os.path.join(app.extra["config_dir"], ".env")
        if os.path.isfile(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        if k == f"{provider_name.upper()}_API_KEY":
                            api_key = v
                            break
        if provider_name == "ollama":
            api_key = api_key or "ollama"
            url = url.rstrip("/") + "/v1"
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url=url, api_key=api_key, model="test", timeout=10)
        try:
            ok = adapter.test()
            return {"ok": ok, "error": "" if ok else "Connection failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── AI Queue ────────────────────────────────────────────────

    @app.get("/api/queue/status")
    def queue_status():
        _db = _get_db(app)
        pending = _db.execute(
            "SELECT COUNT(*) as n FROM ai_queue WHERE status='pending'"
        )[0]["n"]
        processing = _db.execute(
            "SELECT aq.id, aq.asset_id, a.filename FROM ai_queue aq "
            "JOIN assets a ON aq.asset_id = a.id "
            "WHERE aq.status='processing' LIMIT 1"
        )
        return {
            "pending": pending,
            "processing_name": processing[0]["filename"] if processing else None,
        }

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
        total_new = 0
        watch_paths = cfg.get("watch_paths") or []
        print(f"[扫描] 开始扫描 {len(watch_paths)} 条路径", flush=True)
        for wp in watch_paths:
            path = os.path.expanduser(wp.get("path", "").replace(":", "/"))
            r = wp.get("recursive", True)
            md = wp.get("max_depth", 3)
            print(f"[扫描]   进入目录: {path} (递归=@r, 深度=@d)".replace("@r",str(r)).replace("@d",str(md)), flush=True)
            print(f"[扫描]   os.path.isdir({path}) = {os.path.isdir(path)}", flush=True)
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
    """Get thread-local Database connection."""
    import threading
    tid = threading.current_thread().ident
    if "_db_cache" not in app.extra:
        app.extra["_db_cache"] = {}
    cache = app.extra["_db_cache"]
    if tid not in cache:
        cache[tid] = Database(app.extra["db_path"])
    return cache[tid]
