"""Tests for quickmedia.scanner — file scanning engine."""

import os
import tempfile
import hashlib
from quickmedia.config import Config
from quickmedia.database import Database
from quickmedia.scanner import Scanner


def _tmp_env():
    """Set up a temp config dir, database, and scanner."""
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    scanner = Scanner(db=db, config=cfg)
    return config_dir, db, cfg, scanner


def _make_file(dirpath: str, name: str, content: bytes = b"hello") -> str:
    """Create a file with given content, return its path."""
    path = os.path.join(dirpath, name)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _hash(content: bytes) -> str:
    """SHA256 hex digest."""
    return hashlib.sha256(content).hexdigest()


class TestExtensionWhitelist:
    """File extension filtering."""

    def test_image_allowed(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._is_allowed("cat.jpg") is True
        assert scanner._is_allowed("cat.png") is True
        assert scanner._is_allowed("cat.WEBP") is True  # case insensitive

    def test_video_allowed(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._is_allowed("video.mp4") is True
        assert scanner._is_allowed("video.mov") is True

    def test_document_allowed(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._is_allowed("notes.md") is True
        assert scanner._is_allowed("doc.pdf") is True
        assert scanner._is_allowed("readme.txt") is True

    def test_unknown_extension_blocked(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._is_allowed("program.exe") is False
        assert scanner._is_allowed("archive.zip") is False
        assert scanner._is_allowed("script.py") is False

    def test_no_extension_blocked(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._is_allowed("README") is False


class TestTypeDetection:
    """Asset type classification from extension."""

    def test_image_type(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._get_type(".jpg") == "image"
        assert scanner._get_type(".png") == "image"

    def test_video_type(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._get_type(".mp4") == "video"

    def test_audio_type(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._get_type(".mp3") == "audio"
        assert scanner._get_type(".wav") == "audio"

    def test_document_type(self):
        _, db, cfg, scanner = _tmp_env()
        assert scanner._get_type(".pdf") == "document"
        assert scanner._get_type(".md") == "document"


class TestAutoTags:
    """Automatic tag generation during scanning (v4: only duration tags)."""

    def test_no_type_tag(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.png", "image", "/tmp/test.png", 0)
        assert "图片" not in tags

    def test_no_format_tag(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.png", "image", "/tmp/test.png", 0)
        assert "PNG" not in tags

    def test_no_time_period_tag(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.jpg", "image", "/tmp/test.jpg", 0)
        has_year = any(t.startswith("202") for t in tags)
        assert not has_year

    def test_video_length_tag_short(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.mp4", "video", "/tmp/test.mp4", 120)
        assert "短片(<5min)" in tags

    def test_video_length_tag_medium(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.mp4", "video", "/tmp/test.mp4", 600)
        assert "中片(5-30min)" in tags

    def test_video_length_tag_long(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.mp4", "video", "/tmp/test.mp4", 2000)
        assert "长片(>30min)" in tags

    def test_non_video_no_length_tag(self):
        _, db, cfg, scanner = _tmp_env()
        tags = scanner._auto_tags("test.jpg", "image", "/tmp/test.jpg", 10)
        assert not any("短片" in t or "中片" in t or "长片" in t for t in tags)


class TestScanNewFiles:
    """Scanning new files into the database."""

    def test_scan_single_image(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        _make_file(src_dir, "cat.png", b"image_data_123")

        result = scanner.scan_directory(src_dir)
        assert result["new"] == 1
        assert result["total"] == 1

        stats = db.get_stats()
        assert stats["image"] == 1
        assert stats["total"] == 1

    def test_scan_multiple_types(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        _make_file(src_dir, "a.jpg", b"img")
        _make_file(src_dir, "b.mp4", b"vid")
        _make_file(src_dir, "c.txt", b"txt")

        result = scanner.scan_directory(src_dir)
        assert result["new"] == 3

        stats = db.get_stats()
        assert stats["image"] == 1
        assert stats["video"] == 1
        assert stats["document"] == 1

    def test_scan_skips_blocked_extensions(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        _make_file(src_dir, "a.jpg", b"img")
        _make_file(src_dir, "b.exe", b"bin")
        _make_file(src_dir, "c.zip", b"zip")

        result = scanner.scan_directory(src_dir)
        assert result["new"] == 1
        assert result["skipped"] == 2


class TestDuplicateDetection:
    """Handling duplicate files (same hash)."""

    def test_same_hash_different_path(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        content = b"identical content for dedup test"
        _make_file(src_dir, "original.jpg", content)
        _make_file(src_dir, "copy.jpg", content)

        result = scanner.scan_directory(src_dir)
        # First file is new, second is a duplicate
        assert result["new"] == 1
        assert result["duplicates"] == 1


class TestFileDeletion:
    """Detecting deleted files."""

    def test_file_gone_marked_deleted(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        path = _make_file(src_dir, "temp.png", b"temp")

        # Scan it in
        scanner.scan_directory(src_dir)
        stats = db.get_stats()
        assert stats["image"] == 1

        # Delete the file
        os.remove(path)

        # Re-scan
        scanner.scan_directory(src_dir)
        stats = db.get_stats()
        assert stats["image"] == 0  # deleted files excluded from stats


class TestScanRecursion:
    """Recursive directory scanning."""

    def test_recursive_scan(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        sub_dir = os.path.join(src_dir, "subfolder")
        os.makedirs(sub_dir)
        _make_file(src_dir, "root.jpg", b"img")
        _make_file(sub_dir, "nested.png", b"img2")

        result = scanner.scan_directory(src_dir, recursive=True)
        assert result["new"] == 2

    def test_non_recursive_scan(self):
        config_dir, db, cfg, scanner = _tmp_env()
        src_dir = tempfile.mkdtemp()
        sub_dir = os.path.join(src_dir, "subfolder")
        os.makedirs(sub_dir)
        _make_file(src_dir, "root.jpg", b"img")
        _make_file(sub_dir, "nested.png", b"img2")

        result = scanner.scan_directory(src_dir, recursive=False)
        assert result["new"] == 1  # only root.jpg


class TestTranscribeEnqueue:
    """Scanner enqueues transcribe tasks for audio and video."""

    def test_audio_enqueues_transcribe(self):
        """Audio files get a transcribe task enqueued."""
        config_dir, db, cfg, scanner = _tmp_env()
        # Mock AIWorker.enqueue to avoid real whisper loading
        enqueued = []
        scanner._ai.enqueue = lambda aid, tt: enqueued.append((aid, tt))

        src_dir = tempfile.mkdtemp()
        _make_file(src_dir, "podcast.wav", b"audio_data")
        scanner.scan_directory(src_dir)

        assert ("transcribe" in [t for _, t in enqueued])

    def test_video_enqueues_both_vision_and_transcribe(self):
        """Video files get both vision and transcribe tasks."""
        config_dir, db, cfg, scanner = _tmp_env()
        enqueued = []
        scanner._ai.enqueue = lambda aid, tt: enqueued.append((aid, tt))

        src_dir = tempfile.mkdtemp()
        _make_file(src_dir, "meeting.mp4", b"video_data")
        scanner.scan_directory(src_dir)

        task_types = [t for _, t in enqueued]
        assert "vision" in task_types
        assert "transcribe" in task_types
