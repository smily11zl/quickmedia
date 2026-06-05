"""Tests for quickmedia.watcher — fsevents file monitoring."""

import os
import tempfile
import time
import threading
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.watcher import AssetWatcher


def _tmp_env():
    """Create temp config, db, and a scan directory."""
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    watch_dir = tempfile.mkdtemp()
    return db, cfg, watch_dir


class TestWatcherStartStop:
    """Watcher lifecycle."""

    def test_start_and_stop(self):
        db, cfg, watch_dir = _tmp_env()
        watcher = AssetWatcher(db=db, config=cfg)
        watcher.add_watch(watch_dir)
        watcher.start()
        assert watcher.is_running()
        watcher.stop()
        assert not watcher.is_running()

    def test_context_manager(self):
        db, cfg, watch_dir = _tmp_env()
        with AssetWatcher(db=db, config=cfg) as watcher:
            watcher.add_watch(watch_dir)
            assert watcher.is_running()
        assert not watcher.is_running()


class TestFileCreation:
    """New files detected and scanned."""

    def test_new_image_detected(self):
        db, cfg, watch_dir = _tmp_env()
        with AssetWatcher(db=db, config=cfg) as watcher:
            watcher.add_watch(watch_dir)
            # Create an image file
            from PIL import Image
            path = os.path.join(watch_dir, "new_cat.jpg")
            img = Image.new("RGB", (100, 100), color="orange")
            img.save(path)

            # Allow watcher to process
            time.sleep(0.5)
            watcher._process_events()

        stats = db.get_stats()
        assert stats["image"] >= 1

    def test_non_media_file_ignored(self):
        db, cfg, watch_dir = _tmp_env()
        with AssetWatcher(db=db, config=cfg) as watcher:
            watcher.add_watch(watch_dir)
            # Create a .py file (should be ignored)
            path = os.path.join(watch_dir, "script.py")
            with open(path, "w") as f:
                f.write("print('hello')")

            time.sleep(0.5)
            watcher._process_events()

        stats = db.get_stats()
        assert stats["total"] == 0  # .py is not in whitelist


class TestFileDeletion:
    """File deletion marks asset as deleted."""

    def test_delete_marked(self):
        db, cfg, watch_dir = _tmp_env()
        path = os.path.join(watch_dir, "temp.png")
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="blue")
        img.save(path)
        import hashlib
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        st = os.stat(path)
        db.execute(
            "INSERT INTO assets (hash, inode, device, path, filename, extension,"
            " asset_type, size, status) VALUES (?,?,?,?,?,?,?,?,'active')",
            (h, st.st_ino, st.st_dev, path, "temp.png", ".png", "image", st.st_size),
        )

        stats_before = db.get_stats()
        assert stats_before["image"] == 1

        watcher = AssetWatcher(db=db, config=cfg)
        os.remove(path)
        watcher._handle_delete(path)

        stats_after = db.get_stats()
        assert stats_after["image"] == 0
