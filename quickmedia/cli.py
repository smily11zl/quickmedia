"""Command-line interface for QuickMedia."""

import sys
import os
from quickmedia.config import Config
from quickmedia.database import Database
from quickmedia.scanner import Scanner


def main(config_dir: str | None = None):
    """Entry point for 'quickmedia' CLI."""
    cfg = Config(config_dir=config_dir) if config_dir else Config()
    db_path = cfg.get("system.db_path")

    if len(sys.argv) < 2:
        _print_usage()
        return

    command = sys.argv[1]

    if command == "stats":
        _cmd_stats(db_path)
    elif command == "scan":
        _cmd_scan(cfg, db_path)
    elif command == "list":
        _cmd_list(db_path)
    elif command == "search":
        _cmd_search(db_path)
    elif command == "tag":
        _cmd_tag(db_path)
    elif command == "edit":
        _cmd_edit(db_path)
    elif command == "serve":
        _cmd_serve(cfg, db_path)
    elif command == "mcp":
        _cmd_mcp(cfg)
    elif command in ("-h", "--help"):
        _print_usage()
    else:
        print(f"未知命令: {command}")
        _print_usage()




def _cmd_mcp(cfg):
    """Start the MCP server for AI agent integration."""
    from quickmedia.mcp_server import main as mcp_main
    mcp_main()


def _print_usage():
    print("""QuickMedia — 本地素材管理工具

用法:
  quickmedia stats      查看素材库统计
  quickmedia scan       扫描素材
  quickmedia list       列出素材
  quickmedia search     搜索素材
  quickmedia tag        管理标签
  quickmedia edit       编辑素材信息
  quickmedia serve      启动 Web UI
  quickmedia paths      管理监控路径
  quickmedia config     查看/修改配置
""")


def _cmd_stats(db_path: str):
    """Display asset statistics."""
    db = Database(db_path)
    try:
        stats = db.get_stats()
    finally:
        db.close()

    print(f"素材总数: {stats['total']}")
    print(f"图片: {stats['image']}  "
          f"视频: {stats['video']}  "
          f"音频: {stats['audio']}  "
          f"文档: {stats['document']}  "
          f"其他: {stats['other']}")


def _cmd_scan(cfg: Config, db_path: str):
    """Scan a directory for media assets."""
    path = sys.argv[2] if len(sys.argv) > 2 else None

    if not path:
        print("用法: quickmedia scan <路径>")
        return

    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        print(f"路径不存在: {path}")
        return

    db = Database(db_path)
    try:
        scanner = Scanner(db=db, config=cfg)
        result = scanner.scan_directory(path)
        # Process thumbnails after scan
        if result["new"] > 0:
            processed = scanner._thumbnailer.process_queue()
            if processed:
                print(f"已生成 {processed} 个缩略图")
            # Process AI queue
            ai_processed = scanner._ai.process_queue()
            if ai_processed:
                print(f"已处理 {ai_processed} 个 AI 分析任务")
    finally:
        db.close()

    print(f"扫描完成。新增 {result['new']}，"
          f"更新 {result['updated']}，"
          f"跳过 {result['skipped']}")
    if result["duplicates"]:
        print(f"发现 {result['duplicates']} 个重复文件（已合并）")


def _cmd_list(db_path: str):
    """List scanned assets."""
    type_filter = None
    args = sys.argv[2:]

    if len(args) >= 2 and args[0] == "--type":
        type_filter = args[1]

    db = Database(db_path)
    try:
        if type_filter:
            rows = db.execute(
                "SELECT id, filename, asset_type, size, width, height, "
                "duration, path FROM assets "
                "WHERE status='active' AND asset_type=? "
                "ORDER BY filename",
                (type_filter,),
            )
        else:
            rows = db.execute(
                "SELECT id, filename, asset_type, size, width, height, "
                "duration, path FROM assets "
                "WHERE status='active' "
                "ORDER BY filename"
            )

        if not rows:
            print("(无素材)")
            return

        header = f"{'ID':<5} {'文件名':<22} {'类型':<8} {'大小':<8} {'尺寸/时长':<15} 路径"
        print(header)
        print("-" * len(header))
        for r in rows:
            size_str = _format_size(r["size"])
            dim_str = ""
            if r["width"] and r["height"]:
                dim_str = f"{r['width']}x{r['height']}"
            elif r["duration"]:
                dim_str = f"{r['duration']:.0f}秒"
            print(f"{r['id']:<5} {r['filename']:<22} {r['asset_type']:<8} "
                  f"{size_str:<8} {dim_str:<15} {r['path']}")
        print(f"\n共 {len(rows)} 条")
    finally:
        db.close()


def _format_size(size: int) -> str:
    """Format file size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size}{unit}"
        size //= 1024
    return f"{size}TB"


def _cmd_search(db_path: str):
    """Search assets by keyword."""
    if len(sys.argv) < 3:
        print("用法: quickmedia search <关键词>")
        return
    query = " ".join(sys.argv[2:])
    db = Database(db_path)
    results = db.search(query)

    if not results:
        print(f"未找到匹配 \"{query}\" 的素材")
        db.close()
        return

    print(f"搜索 \"{query}\" — {len(results)} 条结果:")
    print(f"{'ID':<5} {'文件名':<22} {'类型':<8} {'描述/标签'}")
    print("-" * 70)
    for r in results:
        tags = db.get_asset_tags(r["id"])
        tag_str = ", ".join(t["name"] for t in tags) if tags else ""
        desc = r["description"] or r["visual_description"] or tag_str or ""
        if len(desc) > 30:
            desc = desc[:30] + "..."
        print(f"{r['id']:<5} {r['filename']:<22} {r['asset_type']:<8} {desc}")
    db.close()


def _cmd_tag(db_path: str):
    """Add or list tags for an asset."""
    args = sys.argv[2:]
    if not args:
        print("用法: quickmedia tag <asset-id> <标签名>")
        return

    db = Database(db_path)
    try:
        asset_id = int(args[0])
        if len(args) >= 2:
            # Add tag
            tag_name = " ".join(args[1:])
            tag_id = db.create_tag(tag_name)
            db.tag_asset(asset_id, tag_id)
            rows = db.execute(
                "SELECT filename FROM assets WHERE id=?", (asset_id,)
            )
            fname = rows[0]["filename"] if rows else "?"
            print(f"已添加标签: {tag_name} → {fname}")
        else:
            # List tags
            tags = db.get_asset_tags(asset_id)
            if tags:
                for t in tags:
                    print(f"  [{t['name']}]")
            else:
                print("(无标签)")
    except ValueError:
        print(f"无效的素材 ID: {args[0]}")
    finally:
        db.close()


def _cmd_edit(db_path: str):
    """Edit asset description or notes."""
    if len(sys.argv) < 3:
        print("用法: quickmedia edit <asset-id> [--desc <描述>] [--note <备注>]")
        return

    db = Database(db_path)
    try:
        asset_id = int(sys.argv[2])
        args = sys.argv[3:]

        if len(args) >= 2 and args[0] == "--desc":
            desc = " ".join(args[1:])
            db.execute(
                "UPDATE assets SET description=? WHERE id=?",
                (desc, asset_id),
            )
            print(f"已更新描述")

        elif len(args) >= 2 and args[0] == "--note":
            note = " ".join(args[1:])
            db.execute(
                "UPDATE assets SET notes=? WHERE id=?",
                (note, asset_id),
            )
            print(f"已更新备注")

        else:
            rows = db.execute(
                "SELECT filename, description, notes FROM assets WHERE id=?",
                (asset_id,),
            )
            if rows:
                r = rows[0]
                print(f"{r['filename']}:")
                print(f"  描述: {r['description'] or '(空)'}")
                print(f"  备注: {r['notes'] or '(空)'}")
            else:
                print(f"素材不存在: {asset_id}")
    except ValueError:
        print(f"无效的素材 ID: {sys.argv[2]}")
    finally:
        db.close()


def _cmd_serve(cfg: Config, db_path: str):
    """Start the Web UI server."""
    import uvicorn
    from quickmedia.api.server import create_app
    from quickmedia.scanner import Scanner

    port = int(sys.argv[2]) if len(sys.argv) > 2 else cfg.get("web.default_port") or 8088
    db = Database(db_path)
    thumb_dir = cfg.get("system.thumbnails_path") or os.path.join(
        cfg.config_dir, "thumbnails"
    )

    # v4: clean up old auto-generated time/format/type tags
    from quickmedia.database import _cleanup_v4_tags
    removed = _cleanup_v4_tags(db)
    if removed > 0:
        print(f"已清理 {removed} 个旧版自动标签")

    # Run initial scan on configured watch paths
    watch_paths = cfg.get("watch_paths") or []
    if watch_paths:
        scanner = Scanner(db=db, config=cfg)
        for wp in watch_paths:
            path = os.path.expanduser(wp.get("path", ""))
            if os.path.isdir(path):
                print(f"扫描 {path}...")
                result = scanner.scan_directory(
                    path,
                    recursive=wp.get("recursive", True),
                    max_depth=wp.get("max_depth", 3),
                )
                print(f"  新增 {result['new']}，已存在 {result['total'] - result['new']}")
        processed = scanner._thumbnailer.process_queue()
        if processed:
            print(f"已生成 {processed} 个缩略图")

    app = create_app(db, cfg, thumb_dir)
    db.close()

    # Start file watcher
    from quickmedia.watcher import AssetWatcher
    from quickmedia.ai_worker import AIWorker
    watcher = AssetWatcher(db=Database(db_path), config=cfg)
    for wp in (cfg.get("watch_paths") or []):
        path = os.path.expanduser(wp.get("path", ""))
        if os.path.isdir(path):
            watcher.add_watch(path, recursive=wp.get("recursive", True))
    watcher.start()

    # Start AI worker in background
    import threading
    print("[AIWorker] 检测 Ollama 连接...", flush=True)
    ollama_ok = False
    try:
        url = (cfg.get("providers.ollama.url") or cfg.get("ai.ollama_url") or "http://localhost:11434").rstrip("/")
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url=url + "/v1", api_key="ollama", model="test", timeout=5)
        ollama_ok = adapter.test()
        if ollama_ok:
            model = cfg.get("task_models.vision.model") or cfg.get("ai.model") or "qwen3.5:9b"
            print(f"[AIWorker] Ollama 已连接，模型 {model} 就绪", flush=True)
        else:
            print(f"[AIWorker] Ollama 连接失败", flush=True)
    except Exception as e:
        print(f"[AIWorker] Ollama 不可用 ({e})，跳过 AI 分析", flush=True)
    print("[AIWorker] 后台线程已启动", flush=True)
    def _ai_loop():
        import time
        ai_db = Database(db_path)
        ai_worker = AIWorker(db=ai_db, config=cfg)
        print("[AIWorker] 线程循环已启动", flush=True)
        while True:
            try:
                ai_worker.process_queue()
            except Exception as e:
                print(f"[AIWorker] loop error: {e}", flush=True)
            time.sleep(5)
    # Reset any stuck "processing" tasks from previous interrupted runs
    ai_db = Database(db_path)
    ai_db.execute(
        "UPDATE ai_queue SET status='pending', attempt=0 WHERE status='processing'"
    )
    ai_db.close()
    ai_thread = threading.Thread(target=_ai_loop, daemon=True)
    ai_thread.start()

    print(f"\nQuickMedia Web UI: http://localhost:{port}")
    # Auto-open browser
    import webbrowser
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)
    finally:
        watcher.stop()
