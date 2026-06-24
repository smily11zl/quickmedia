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
            raise HTTPException(status_code=409, detail="已有聚合任务进行中")
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
            from quickmedia.config import Config
            from quickmedia.aggregation.worker import (
                mark_processing, mark_done, mark_failed,
                get_all_assets, get_all_nodes, save_aggregation_result,
            )
            from quickmedia.aggregation.prompts import build_prompt
            from quickmedia.providers import ProviderRegistry

            task_db = Database(db_path)
            try:
                mark_processing(task_db, task_id)
                print(f"[Aggregation] 开始任务 #{task_id}: mode={mode}", flush=True)

                assets = get_all_assets(task_db)
                nodes = get_all_nodes(task_db) if mode != "full" else None
                unassigned = []

                # For append/full_append modes, only count unassigned assets
                if mode in ("append", "full_append"):
                    assigned_ids = set()
                    for n in (nodes or []):
                        for aid in n.get("asset_ids", []):
                            assigned_ids.add(aid)
                    unassigned = [a for a in assets if a["id"] not in assigned_ids]
                    if mode == "append":
                        assets = unassigned

                print(f"[Aggregation] 素材数: {len(assets)}, 已有节点数: {len(nodes) if nodes else 0}", flush=True)

                # Skip AI call if no new/unassigned assets to process
                if mode in ("append", "full_append") and len(unassigned) == 0:
                    print(f"[Aggregation] 任务 #{task_id}: 无新素材，跳过分析", flush=True)
                    mark_done(task_db, task_id)
                    return

                prompt = build_prompt(mode, assets, nodes)
                print(f"[Aggregation] prompt 长度: {len(prompt)} 字符", flush=True)

                config = Config(config_dir=config_dir)
                user_models = os.path.join(config_dir, "models.yaml")
                registry = ProviderRegistry(config, user_models)
                binding = registry.get_task_binding("text")
                provider_name = binding["provider"] if binding else "ollama"
                model = binding["model"] if binding else ""
                url = registry.get_provider_url(provider_name) or ""

                print(f"[Aggregation] 调用 AI: provider={provider_name} model={model}", flush=True)

                # Reuse existing adapters
                if provider_name == "ollama":
                    from quickmedia.ai import OllamaAdapter
                    adapter = OllamaAdapter(base_url=url, model=model, timeout=300)
                else:
                    from quickmedia.openai_adapter import OpenAIAdapter
                    env_path = os.path.join(config_dir, ".env")
                    api_key = ""
                    if os.path.isfile(env_path):
                        with open(env_path) as f:
                            for line in f:
                                if provider_name.upper() + "_API_KEY" in line:
                                    api_key = line.split("=", 1)[1].strip()
                                    break
                    adapter = OpenAIAdapter(base_url=url, api_key=api_key, model=model,
                                            provider_name=provider_name, timeout=300)

                content = adapter.chat(prompt)
                print(f"[Aggregation] AI 响应已接收", flush=True)

                # Parse JSON from response (may be wrapped in markdown code block)
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content
                    if content.endswith("```"):
                        content = content[:-3]
                result = json.loads(content)
                node_count = len(result.get("nodes", []))
                print(f"[Aggregation] 解析结果: {node_count} 个节点", flush=True)

                # Full mode: clear old nodes before saving new ones
                if mode == "full":
                    task_db.execute("DELETE FROM node_assets")
                    task_db.execute("DELETE FROM nodes")

                save_aggregation_result(task_db, result)
                mark_done(task_db, task_id)
                print(f"[Aggregation] 任务 #{task_id} 完成: 已保存 {node_count} 个节点", flush=True)

            except Exception as e:
                print(f"[Aggregation] 任务 #{task_id} 失败: {e}", flush=True)
                err_db = Database(db_path)
                mark_failed(err_db, task_id, str(e))
                err_db.close()
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
    def create_node(body: dict):
        db = _get_db(app)
        name = body.get("name", "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="节点名不能为空")
        db.execute(
            "INSERT INTO nodes (name, description) VALUES (?,?)",
            (name, body.get("description", "")),
        )
        nid = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        return {"id": nid, "name": name, "description": body.get("description", "")}

    @app.put("/api/nodes/{node_id}")
    def update_node(node_id: int, body: dict):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="节点不存在")
        name = body.get("name", "").strip()
        if name:
            db.execute(
                "UPDATE nodes SET name=?, description=? WHERE id=?",
                (name, body.get("description", ""), node_id),
            )
        return {"ok": True}

    @app.delete("/api/nodes/{node_id}")
    def delete_node(node_id: int):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="节点不存在")
        db.execute("DELETE FROM node_assets WHERE node_id=?", (node_id,))
        db.execute("DELETE FROM nodes WHERE id=?", (node_id,))
        return {"ok": True}

    @app.post("/api/nodes/{node_id}/assets")
    def assign_assets(node_id: int, body: dict):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="节点不存在")
        asset_ids = body.get("asset_ids", [])
        for aid in asset_ids:
            try:
                db.execute(
                    "INSERT OR IGNORE INTO node_assets (node_id, asset_id) VALUES (?,?)",
                    (node_id, int(aid)),
                )
            except Exception:
                pass
        return {"ok": True}

    @app.delete("/api/nodes/{node_id}/assets/{asset_id}")
    def unassign_asset(node_id: int, asset_id: int):
        db = _get_db(app)
        db.execute(
            "DELETE FROM node_assets WHERE node_id=? AND asset_id=?",
            (node_id, asset_id),
        )
        return {"ok": True}

    @app.get("/api/nodes/{node_id}/assets")
    def get_node_assets(node_id: int, limit: int = 200, offset: int = 0):
        db = _get_db(app)
        existing = db.execute("SELECT 1 FROM nodes WHERE id=?", (node_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="节点不存在")
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
