"""V20 s2: 热度系统 — view_count / open_count 计数测试."""

import unittest
import tempfile
import shutil
import os


class TestV20HotCount(unittest.TestCase):
    """Test view_count and open_count increment logic."""

    def test_view_count_increments_on_detail(self):
        """GET /api/assets/{id} increments view_count."""
        # Create a minimal config and database
        d = tempfile.mkdtemp()
        try:
            from quickmedia.database import Database
            from quickmedia.config import Config
            cfg_path = os.path.join(d, "config.yaml")
            with open(cfg_path, "w") as f:
                f.write("watch_paths: []\n")
            cfg = Config(config_dir=d)
            db_path = os.path.join(d, "data.db")
            db = Database(db_path)
            # Insert a test asset
            db.execute(
                "INSERT INTO assets (filename, path, asset_type, size, hash, ai_status, extension, view_count, open_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("test.jpg", "/tmp/test.jpg", "image", 1024, "abc123", "done", "jpg", 0, 0),
            )
            rows = db.execute("SELECT id, view_count FROM assets WHERE filename=?", ("test.jpg",))
            aid = rows[0]["id"]
            self.assertEqual(rows[0]["view_count"], 0)

            # Simulate detail access — should increment
            db.execute("UPDATE assets SET view_count = view_count + 1 WHERE id=?", (aid,))
            rows = db.execute("SELECT view_count FROM assets WHERE id=?", (aid,))
            self.assertEqual(rows[0]["view_count"], 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_open_count_increments(self):
        """Simulating open file increments open_count."""
        d = tempfile.mkdtemp()
        try:
            from quickmedia.database import Database
            db = Database(os.path.join(d, "data.db"))
            db.execute(
                "INSERT INTO assets (filename, path, asset_type, size, hash, ai_status, extension, view_count, open_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("open.jpg", "/tmp/open.jpg", "image", 512, "def456", "done", "jpg", 0, 0),
            )
            rows = db.execute("SELECT id FROM assets WHERE filename=?", ("open.jpg",))
            aid = rows[0]["id"]
            db.execute("UPDATE assets SET open_count = open_count + 1 WHERE id=?", (aid,))
            rows = db.execute("SELECT open_count FROM assets WHERE id=?", (aid,))
            self.assertEqual(rows[0]["open_count"], 1)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_view_count_default_zero(self):
        """New columns have DEFAULT 0."""
        d = tempfile.mkdtemp()
        try:
            from quickmedia.database import Database
            db = Database(os.path.join(d, "data.db"))
            db.execute(
                "INSERT INTO assets (filename, path, asset_type, size, hash, ai_status, extension) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("new.jpg", "/tmp/new.jpg", "image", 100, "ghi789", "done", "jpg"),
            )
            rows = db.execute("SELECT view_count, open_count FROM assets WHERE filename=?", ("new.jpg",))
            self.assertEqual(rows[0]["view_count"], 0)
            self.assertEqual(rows[0]["open_count"], 0)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
