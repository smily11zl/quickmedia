"""Thumbnail generation for QuickMedia.

Creates 256px max thumbnails from images and video first frames.
Uses a SQLite-backed queue for async processing.
"""

import os
from PIL import Image, UnidentifiedImageError
from quickmedia.database import Database


class Thumbnailer:
    """Generate and manage thumbnails for media assets."""

    def __init__(
        self,
        db: Database,
        thumb_dir: str,
        max_size: int = 256,
    ):
        self.db = db
        self.thumb_dir = thumb_dir
        self.max_size = max_size
        os.makedirs(thumb_dir, exist_ok=True)

    # ── public API ────────────────────────────────────────────────

    def enqueue(self, asset_id: int) -> None:
        """Add an asset to the thumbnail queue (idempotent)."""
        existing = self.db.execute(
            "SELECT id, status FROM thumbnail_queue WHERE asset_id=?",
            (asset_id,),
        )
        if not existing:
            self.db.execute(
                "INSERT INTO thumbnail_queue (asset_id) VALUES (?)",
                (asset_id,),
            )

    def generate(self, asset_id: int, filepath: str) -> bool:
        """Generate a thumbnail for an asset. Returns True on success."""
        try:
            self.db.execute(
                "UPDATE assets SET thumbnail_status='processing' WHERE id=?",
                (asset_id,),
            )
            self._make_thumbnail(asset_id, filepath)
            self.db.execute(
                "UPDATE assets SET thumbnail_status='done' WHERE id=?",
                (asset_id,),
            )
            return True
        except Exception:
            self.db.execute(
                "UPDATE assets SET thumbnail_status='failed' WHERE id=?",
                (asset_id,),
            )
            return False

    def process_queue(self) -> int:
        """Process all pending thumbnails. Returns count processed."""
        rows = self.db.execute(
            """SELECT a.id, a.path FROM assets a
               WHERE a.thumbnail_status='pending' AND a.asset_type='image'
               ORDER BY a.id"""
        )
        count = 0
        for row in rows:
            if self.generate(row["id"], row["path"]):
                count += 1
        return count

    def _thumb_path(self, asset_id: int) -> str:
        return os.path.join(self.thumb_dir, f"{asset_id}.jpg")

    # ── internals ─────────────────────────────────────────────────

    def _make_thumbnail(self, asset_id: int, filepath: str) -> None:
        """Create a thumbnail file from an image."""
        with Image.open(filepath) as img:
            img = img.convert("RGB")
            w, h = img.size
            scale = self.max_size / max(w, h)
            if scale < 1.0:
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            out_path = self._thumb_path(asset_id)
            img.save(out_path, "JPEG", quality=85)
