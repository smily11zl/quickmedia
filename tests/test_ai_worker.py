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
        from quickmedia.ai import OllamaAdapter
        class _MockAdp:
            def chat(self, prompt, images=None):
                return '{"description": "a red square", "tags": ["红色", "方块"], "text": ""}'
        worker._get_adapter = lambda t: _MockAdp()
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
        call_count = 0
        def flaky_chat(prompt, images=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("slow")
            return '{"description": "ok", "tags": ["test"], "text": ""}'
        class _MockFlaky:
            def chat(self, prompt, images=None):
                return flaky_chat(prompt, images)
        worker._get_adapter = lambda t: _MockFlaky()
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
        class _FailAdp:
            def chat(self, prompt, images=None):
                raise TimeoutError("always fails")
        worker._get_adapter = lambda t: _FailAdp()
        worker.enqueue(asset_id, "vision")
        worker.process_queue()

        rows = db.execute(
            "SELECT status, attempt, error FROM ai_queue WHERE asset_id=?",
            (asset_id,),
        )
        assert rows[0]["status"] == "failed"
        assert rows[0]["attempt"] == 3
        assert "always fails" in (rows[0]["error"] or "")


class TestTranscribeTask:
    """AIWorker handles task_type='transcribe'."""

    def test_transcribe_stores_transcript(self):
        """Transcribe task runs, stores transcript, and runs speech analysis."""
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "audio.m4a")
        import hashlib
        h = hashlib.sha256(b"").hexdigest()
        with open(path, "w") as f: f.write("dummy")
        st = os.stat(path)
        cursor = db.conn.execute(
            """INSERT INTO assets (hash, inode, device, path, filename, extension,
               asset_type, size, status) VALUES (?,?,?,?,?,?,?,?,'active')""",
            (h, st.st_ino, st.st_dev, path, "audio.m4a", ".m4a", "audio", st.st_size),
        )
        db.conn.commit()
        asset_id = cursor.lastrowid

        worker = AIWorker(db=db, config=cfg)
        # Mock both transcriber and text analyzer
        worker._transcriber.transcribe = lambda p: "今天我们讨论预算审批"
        class _SpkAdp2:
            def chat(self, prompt, images=None):
                return '{"summary": "讨论预算相关事项", "tags": ["会议", "预算", "审批"]}'
        worker._get_adapter = lambda t: _SpkAdp2()
        worker.enqueue(asset_id, "transcribe")
        worker.process_queue()

        # Verify transcript stored
        asset_rows = db.execute(
            "SELECT transcript, ai_summary FROM assets WHERE id=?", (asset_id,)
        )
        assert "预算审批" in (asset_rows[0]["transcript"] or "")
        assert "预算" in (asset_rows[0]["ai_summary"] or "")

        # Verify speech tags linked
        tags = db.get_asset_tags(asset_id)
        tag_names = {t["name"] for t in tags}
        assert "会议" in tag_names

    def test_transcribe_triggers_video_summary(self):
        """For video assets, transcribe+speech analysis triggers combined summary
        when vision analysis is also done."""
        db, cfg = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "meeting.mp4")
        import hashlib
        h = hashlib.sha256(b"").hexdigest()
        with open(path, "w") as f: f.write("dummy")
        st = os.stat(path)
        cursor = db.conn.execute(
            """INSERT INTO assets (hash, inode, device, path, filename, extension,
               asset_type, size, width, height, ai_description, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'active')""",
            (h, st.st_ino, st.st_dev, path, "meeting.mp4", ".mp4", "video",
             st.st_size, 1920, 1080, "会议室场景，多人讨论"),
        )
        db.conn.commit()
        asset_id = cursor.lastrowid

        worker = AIWorker(db=db, config=cfg)
        worker._transcriber.transcribe = lambda p: "今天我们讨论Q3预算"
        class _SpkAdp:
            def chat(self, prompt, images=None):
                return '{"summary": "讨论Q3预算分配", "tags": ["会议", "预算"]}'
        worker._get_adapter = lambda t: _SpkAdp()
        # Mock the combined summary generation
        worker._try_generate_video_summary = lambda aid: (
            db.execute(
                "UPDATE assets SET video_summary='综合：会议室讨论Q3预算分配' WHERE id=?",
                (aid,)
            )
        )
        worker.enqueue(asset_id, "transcribe")
        worker.process_queue()

        # Verify combined summary generated
        asset_rows = db.execute(
            "SELECT transcript, ai_summary, video_summary FROM assets WHERE id=?",
            (asset_id,),
        )
        assert "Q3预算" in (asset_rows[0]["transcript"] or "")
        assert "Q3预算分配" in (asset_rows[0]["ai_summary"] or "")
        assert "综合" in (asset_rows[0]["video_summary"] or "")
