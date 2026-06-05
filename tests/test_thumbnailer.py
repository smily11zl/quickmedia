"""Tests for quickmedia.thumbnailer — thumbnail generation."""

import os
import tempfile
from PIL import Image
from quickmedia.thumbnailer import Thumbnailer
from quickmedia.database import Database
from quickmedia.config import Config


def _tmp_env():
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    thumb_dir = os.path.join(config_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumbnailer = Thumbnailer(db=db, thumb_dir=thumb_dir, max_size=256)
    return db, cfg, thumbnailer, config_dir


def _create_image_asset(db, path):
    """Create a test image and insert an asset record."""
    img = Image.new("RGB", (800, 600), color="salmon")
    img.save(path)
    cursor = db.conn.execute(
        """INSERT INTO assets (hash, path, filename, extension, asset_type, size, status)
           VALUES ('testhash', ?, 'test.png', '.png', 'image', 1000, 'active')""",
        (path,),
    )
    db.conn.commit()
    return cursor.lastrowid


class TestThumbnailGeneration:
    """Thumbnail creation from image files."""

    def test_generates_thumbnail(self):
        db, cfg, thumb, config_dir = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_image_asset(db, path)

        thumb.generate(asset_id, path)

        thumb_path = thumb._thumb_path(asset_id)
        assert os.path.isfile(thumb_path)

        with Image.open(thumb_path) as im:
            assert im.width <= 256
            assert im.height <= 256

    def test_updates_thumbnail_status_to_done(self):
        db, cfg, thumb, config_dir = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "img.png")
        asset_id = _create_image_asset(db, path)

        thumb.generate(asset_id, path)

        rows = db.execute(
            "SELECT thumbnail_status FROM assets WHERE id=?",
            (asset_id,),
        )
        assert rows[0]["thumbnail_status"] == "done"

    def test_failed_on_bad_file(self):
        db, cfg, thumb, config_dir = _tmp_env()
        d = tempfile.mkdtemp()
        path = os.path.join(d, "bad.png")
        asset_id = _create_image_asset(db, path)
        # Overwrite with bad bytes AFTER creating valid image
        with open(path, "wb") as f:
            f.write(b"this is not an image file")

        thumb.generate(asset_id, path)

        rows = db.execute(
            "SELECT thumbnail_status FROM assets WHERE id=?",
            (asset_id,),
        )
        assert rows[0]["thumbnail_status"] == "failed"


class TestThumbnailQueue:
    """Thumbnail queue table operations."""

    def test_queue_insert(self):
        db, cfg, thumb, config_dir = _tmp_env()
        db.execute(
            "INSERT INTO assets (hash, path, filename, extension, asset_type, size)"
            " VALUES ('qhash','/tmp/q.jpg','q.jpg','.jpg','image',100)"
        )
        asset_id = db.execute("SELECT last_insert_rowid()")[0]["last_insert_rowid()"]
        thumb.enqueue(asset_id)
        rows = db.execute(
            "SELECT * FROM thumbnail_queue WHERE asset_id=?",
            (asset_id,),
        )
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
