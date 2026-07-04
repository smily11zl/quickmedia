"""File scanning engine for QuickMedia.

Scans directories, identifies media files, computes hashes,
detects duplicates via inode+device and SHA256, and
generates automatic tags.
"""

import os
import hashlib
import stat
import time
from datetime import datetime
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.metadata import MetadataExtractor
from quickmedia.thumbnailer import Thumbnailer
from quickmedia.ai_worker import AIWorker


class Scanner:
    """Scans filesystem directories and indexes media assets."""

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        self._formats = config.get("formats") or {}
        self._metadata = MetadataExtractor()
        thumb_dir = config.get("system.thumbnails_path")
        if not thumb_dir:
            thumb_dir = os.path.join(config.config_dir, "thumbnails")
        self._thumbnailer = Thumbnailer(db=db, thumb_dir=thumb_dir)
        self._ai = AIWorker(db=db, config=config)

    # ── extension / type helpers ──────────────────────────────────

    def _is_allowed(self, filename: str) -> bool:
        """Check if file extension is in the whitelist."""
        _, ext = os.path.splitext(filename)
        if not ext:
            return False
        ext = ext.lower()
        for category, exts in self._formats.items():
            if ext.lstrip(".").lower() in [e.lower() for e in exts]:
                return True
        return False

    def _get_type(self, extension: str) -> str:
        """Determine asset_type from file extension."""
        ext = extension.lower().lstrip(".")
        for cat, exts in self._formats.items():
            if ext in [e.lower() for e in exts]:
                return cat
        return "other"

    # ── hashing ───────────────────────────────────────────────────

    def reload_watch_paths(self) -> None:
        """Reload watch paths from config without restarting."""
        self._watch_paths = self.config.get("watch_paths") or []
        print(f"[Scanner] 重载监控路径: {len(self._watch_paths)} 条", flush=True)


    def _compute_hash(self, filepath: str) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    # ── inode lookup ──────────────────────────────────────────────

    def _get_inode(self, filepath: str) -> tuple[int, int] | None:
        """Return (inode, device) tuple for a file, or None on error."""
        try:
            st = os.stat(filepath)
            return (st.st_ino, st.st_dev)
        except OSError:
            return None

    def _find_by_inode(self, inode: int, device: int) -> dict | None:
        """Find an active asset by inode+device."""
        rows = self.db.execute(
            "SELECT * FROM assets WHERE inode=? AND device=? AND status='active'",
            (inode, device),
        )
        return dict(rows[0]) if rows else None

    # ── hash lookup ───────────────────────────────────────────────

    def _find_by_hash(self, hash_val: str) -> dict | None:
        """Find an active asset by SHA256 hash."""
        rows = self.db.execute(
            "SELECT * FROM assets WHERE hash=? AND status='active'",
            (hash_val,),
        )
        return dict(rows[0]) if rows else None

    # ── auto tags ─────────────────────────────────────────────────

    def _auto_tags(
        self, filename: str, asset_type: str, filepath: str, duration: float
    ) -> list[str]:
        """Generate automatic tags for a scanned asset."""
        tags = []

        # Video length bucket
        if asset_type == "video" and duration > 0:
            if duration < 300:
                tags.append("短片(<5min)")
            elif duration < 1800:
                tags.append("中片(5-30min)")
            else:
                tags.append("长片(>30min)")

        return tags

    # ── tag persistence ──────────────────────────────────────────

    def _ensure_tags(self, tag_names: list[str]) -> dict[str, int]:
        """Ensure tags exist in DB, return {name: id} mapping."""
        tag_ids = {}
        for name in tag_names:
            rows = self.db.execute("SELECT id FROM tags WHERE name=?", (name,))
            if rows:
                tag_ids[name] = rows[0]["id"]
            else:
                self.db.execute(
                    "INSERT INTO tags (name) VALUES (?)", (name,)
                )
                row = self.db.execute("SELECT last_insert_rowid()")
                tag_ids[name] = row[0][0]
        return tag_ids

    def _link_tags(
        self, asset_id: int, tag_names: list[str], source: str = "auto"
    ) -> None:
        """Link tags to an asset, skipping already-linked ones."""
        tag_ids = self._ensure_tags(tag_names)
        existing = self.db.execute(
            "SELECT tag_id FROM asset_tags WHERE asset_id=?", (asset_id,)
        )
        existing_ids = {r["tag_id"] for r in existing}
        for name, tid in tag_ids.items():
            if tid not in existing_ids:
                self.db.execute(
                    "INSERT INTO asset_tags (asset_id, tag_id, source) VALUES (?,?,?)",
                    (asset_id, tid, source),
                )

    # ── scan directory ────────────────────────────────────────────

    def scan_directory(
        self, directory: str, recursive: bool = True, max_depth: int = 3
    ) -> dict:
        """Scan a directory for media files. Returns counts."""
        result = {"new": 0, "updated": 0, "skipped": 0, "duplicates": 0, "total": 0}

        if not os.path.isdir(directory):
            return result
        print(f"[扫描] 正在扫描: {directory} (递归={recursive}, 深度={max_depth})", flush=True)

        # Collect all files
        print(f"[扫描]   开始遍历: {directory}", flush=True)
        filepaths = []
        for root, dirs, files in os.walk(directory):
            depth = root[len(directory) :].count(os.sep)
            if files:
                print(f"[扫描]     子目录: {root} ({len(files)}个文件)", flush=True)
            if not recursive or depth >= max_depth:
                dirs.clear()
            for fname in files:
                filepaths.append(os.path.join(root, fname))

        # Collect existing inode → asset mapping for this directory scope
        # to detect deletions later
        scanned_paths = set()

        for filepath in filepaths:
            filename = os.path.basename(filepath)

            if not self._is_allowed(filename):
                result["skipped"] += 1
                continue

            try:
                st = os.stat(filepath)
            except OSError:
                continue

            ext = os.path.splitext(filename)[1]
            asset_type = self._get_type(ext)
            size = st.st_size
            scanned_paths.add(filepath)

            # Ingest file (inode dedup, hash dedup, or insert new)
            self._ingest_file(filepath, result)

        # Mark deleted files (files in DB whose path is under this directory
        # but no longer exist on disk)
        self._mark_deleted(directory)

        try:
            self._thumbnailer.process_queue()
        except Exception as e:
            print(f"[Scanner] 缩略图处理异常: {e}", flush=True)
        return result

    def _insert_asset(self, filepath: str, filename: str, ext: str,
                      asset_type: str, size: int, st, hash_val: str) -> int:
        """Insert a new asset into the database. Returns asset_id."""
        modified_ts = datetime.fromtimestamp(st.st_mtime).isoformat()
        created_ts = datetime.fromtimestamp(st.st_ctime).isoformat()
        now = datetime.now().isoformat()

        self.db.execute(
            """INSERT INTO assets
               (hash, inode, device, path, filename, extension, asset_type,
                size, status, thumbnail_status, modified_at, created_at,
                scanned_at, ai_status, ai_status_updated_at)
                VALUES (?,?,?,?,?,?,?,?, 'active','pending',?,?,?, 'pending',?)""",
            (hash_val, st.st_ino, st.st_dev, filepath, filename,
             ext.lower(), asset_type, size, modified_ts, created_ts, now, now),
        )
        row = self.db.execute("SELECT last_insert_rowid()")
        return row[0][0]

    def _ingest_file(self, filepath: str, result: dict = None) -> int:
        """Ingest a single file into the asset database. Returns asset_id or 0.
        
        Args:
            filepath: Absolute path to the file.
            result: Optional dict for stats tracking (new, updated, duplicates, total).
        """
        import os as _os
        filename = _os.path.basename(filepath)
        ext = _os.path.splitext(filename)[1].lower().lstrip(".")
        if not self._is_allowed(filename):
            return 0

        asset_type = self._get_type(ext)
        if not asset_type:
            asset_type = "other"

        stat = _os.stat(filepath)
        size = stat.st_size
        now = datetime.now().isoformat()

        # 1. Inode match — file was renamed/moved
        existing = self._find_by_inode(stat.st_ino, stat.st_dev)
        if existing and existing["path"] != filepath:
            self.db.execute(
                "UPDATE assets SET path=?, scanned_at=? WHERE id=?",
                (filepath, now, existing["id"]),
            )
            if result:
                result["updated"] = result.get("updated", 0) + 1
                result["total"] = result.get("total", 0) + 1
            return existing["id"]
        elif existing and existing["path"] == filepath:
            self.db.execute(
                "UPDATE assets SET scanned_at=?, size=? WHERE id=?",
                (now, size, existing["id"]),
            )
            if result:
                result["total"] = result.get("total", 0) + 1
            return existing["id"]

        # 2. Hash match — duplicate content
        hash_val = self._compute_hash(filepath)
        hash_existing = self._find_by_hash(hash_val)
        if hash_existing:
            if result:
                result["duplicates"] = result.get("duplicates", 0) + 1
                result["total"] = result.get("total", 0) + 1
            return hash_existing["id"]

        # 3. New asset
        asset_id = self._insert_asset(filepath, filename, ext, asset_type, size, stat, hash_val)
        if result:
            result["new"] = result.get("new", 0) + 1
            result["total"] = result.get("total", 0) + 1

        # Post-processing: tags, metadata, thumbnail, AI
        meta = self._metadata.extract(filepath)
        auto_tags = self._auto_tags(filename, asset_type, filepath, meta.get("duration", 0))
        self._link_tags(asset_id, auto_tags, source="auto")
        if meta.get("width") or meta.get("height") or meta.get("duration"):
            updates, params = [], []
            if meta.get("width") is not None:
                updates.append("width=?"); params.append(meta["width"])
            if meta.get("height") is not None:
                updates.append("height=?"); params.append(meta["height"])
            if meta.get("duration") is not None:
                updates.append("duration=?"); params.append(meta["duration"])
            if updates:
                params.append(asset_id)
                self.db.execute(
                    f"UPDATE assets SET {', '.join(updates)} WHERE id=?",
                    tuple(params),
                )
        if asset_type in ("image", "video"):
            self._thumbnailer.enqueue(asset_id)
        if asset_type == "image":
            self._ai.enqueue(asset_id, "vision")
        elif asset_type == "video":
            self._ai.enqueue(asset_id, "vision")
            self._ai.enqueue(asset_id, "transcribe")
        elif asset_type == "audio":
            self._ai.enqueue(asset_id, "transcribe")
        elif asset_type == "document":
            self._ai.enqueue(asset_id, "text")

        return asset_id

    def scan_file(self, filepath: str) -> int:
        """Add a single file to the asset database. Returns asset_id or 0."""
        import os as _os
        if not _os.path.isfile(filepath):
            return 0
        aid = self._ingest_file(filepath)
        if aid:
            self._thumbnailer.process_queue()
        return aid

    def _mark_deleted(self, directory: str) -> None:
        """Mark assets whose paths no longer exist on disk as deleted."""
        rows = self.db.execute(
            """SELECT id, path FROM assets
               WHERE status='active' AND path LIKE ?""",
            (directory + "%",),
        )
        for row in rows:
            if not os.path.isfile(row["path"]):
                self.db.execute(
                    "UPDATE assets SET status='deleted' WHERE id=?",
                    (row["id"],),
                )

    def _read_text(self, filepath: str) -> str:
        """Read text content from a document file."""
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()
        if ext in {".txt", ".md"}:
            with open(filepath, "r", errors="replace") as f:
                return f.read()
        if ext == ".pdf":
            try:
                import fitz  # pymupdf
                doc = fitz.open(filepath)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except ImportError:
                pass
        return ""
