"""Tests for quickmedia.ai_worker — async AI analysis queue."""

import os, tempfile
from PIL import Image
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.ai_worker import AIWorker


def _tmp_env():
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    return db, cfg


def _create_asset(db, path, asset_type="image"):
    img = Image.new("RGB", (100, 100), color="red")
    img.save(path)
    st = os.stat(path)
    import hashlib
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    cursor = db.conn.execute(
        """INSERT INTO assets (hash, inode, device, path, filename, extension,
           asset_type, size, status) VALUES (?,?,?,?,?,?,?,?,'active')""",
        (h, st.st_ino, st.st_dev, path, "test.png", ".png", asset_type, st.st_size),
    )
    db.conn.commit()
    return cursor.lastrowid


class TestAIQueue:
    """ai_queue table operations."""

    def test_enqueue(self):
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_asset(db, path)
        worker = AIWorker(db=db, config=cfg)
        worker.enqueue(asset_id, "vision")

        rows = db.execute(
            "SELECT * FROM ai_queue WHERE asset_id=? AND task_type='vision'",
            (asset_id,),
        )
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"

    def test_enqueue_idempotent(self):
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_asset(db, path)
        worker = AIWorker(db=db, config=cfg)
        worker.enqueue(asset_id, "vision")
        worker.enqueue(asset_id, "vision")
        rows = db.execute(
            "SELECT id FROM ai_queue WHERE asset_id=? AND task_type='vision'",
            (asset_id,),
        )
        assert len(rows) == 1

    def test_status_transitions_success(self):
        """After successful AI analysis, status should be 'done'."""
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_asset(db, path)
        worker = AIWorker(db=db, config=cfg)
        # Mock VisionAnalyzer to avoid real Ollama calls
        worker._vision.analyze = lambda p: {"description": "a red square", "tags": ["红色", "方块"]}
        worker.enqueue(asset_id, "vision")
        worker.process_queue()

        rows = db.execute(
            "SELECT status, attempt FROM ai_queue WHERE asset_id=?",
            (asset_id,),
        )
        assert rows[0]["status"] == "done"
        assert rows[0]["attempt"] == 0

    def test_status_transitions_fail_then_retry(self):
        """After 3 failed attempts, status should be 'failed'."""
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_asset(db, path)
        worker = AIWorker(db=db, config=cfg)
        # Simulate 2 timeouts then success on 3rd try
        call_count = [0]
        def flaky_analyze(p):
            call_count[0] += 1
            if call_count[0] < 3:
                raise TimeoutError("timed out")
            return {"description": "finally worked", "tags": ["ok"]}
        worker._vision.analyze = flaky_analyze
        worker.enqueue(asset_id, "vision")
        worker.process_queue()

        rows = db.execute(
            "SELECT status, attempt FROM ai_queue WHERE asset_id=?",
            (asset_id,),
        )
        assert rows[0]["status"] == "done"
        assert rows[0]["attempt"] == 2

    def test_status_transitions_all_fail(self):
        """After 3 failed attempts with no recovery, status should be 'failed'."""
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_asset(db, path)
        worker = AIWorker(db=db, config=cfg)
        worker._vision.analyze = lambda p: (_ for _ in ()).throw(TimeoutError("always fails"))
        worker.enqueue(asset_id, "vision")
        worker.process_queue()

        rows = db.execute(
            "SELECT status, attempt, error FROM ai_queue WHERE asset_id=?",
            (asset_id,),
        )
        assert rows[0]["status"] == "failed"
        assert rows[0]["attempt"] == 3
        assert "always fails" in (rows[0]["error"] or "")
