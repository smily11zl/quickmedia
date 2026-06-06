"""Real-time file system watcher using watchdog (fsevents on macOS).

Monitors configured directories for file changes and updates the asset
database accordingly — new files are scanned, deletions are marked,
modifications are versioned.
"""

import os
import time
import threading
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.scanner import Scanner


class _AssetEventHandler(FileSystemEventHandler):
    """Handles file system events and dispatches to the scanner."""

    def __init__(self, watcher: "AssetWatcher"):
        self._watcher = watcher
        self._events: list[tuple[str, str]] = []  # (type, path)

    def on_created(self, event):
        if not event.is_directory:
            self._events.append(("created", event.src_path))

    def on_deleted(self, event):
        if not event.is_directory:
            self._events.append(("deleted", event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self._events.append(("modified", event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            self._events.append(("moved_from", event.src_path))
            self._events.append(("moved_to", event.dest_path))


class AssetWatcher:
    """Watches directories for media file changes.

    Usage:
        with AssetWatcher(db, config) as watcher:
            watcher.add_watch("/path/to/watch")
            # watcher runs in background thread
    """

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        self._observer = Observer()
        self._handler = _AssetEventHandler(self)
        self._running = False
        self._formats = config.get("formats") or {}

    def add_watch(self, directory: str, recursive: bool = True) -> None:
        """Add a directory to watch."""
        if os.path.isdir(directory):
            self._observer.schedule(self._handler, directory, recursive=recursive)

    def start(self) -> None:
        """Start the watcher in a background thread."""
        self._observer.start()
        self._running = True

    def stop(self) -> None:
        """Stop the watcher."""
        self._observer.stop()
        self._observer.join(timeout=2)
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _process_events(self) -> None:
        """Process accumulated events (for testing). Also handles 
        the _mark_deleted check for directories being watched."""
        events = self._handler._events.copy()
        self._handler._events.clear()

        for evt_type, path in sorted(set(events), key=lambda x: x[0]):
            if evt_type == "deleted":
                self._handle_delete(path)
            elif evt_type == "created":
                self._handle_create(path)
            elif evt_type == "modified":
                self._handle_modify(path)

    def _handle_create(self, path: str) -> None:
        """A new file appeared — scan it."""
        filename = os.path.basename(path)
        if not self._is_allowed(filename):
            return
        try:
            st = os.stat(path)
        except OSError:
            return
        # Use scanner to handle the single file
        self._scan_file(path, filename, st)

    def _handle_modify(self, path: str) -> None:
        """A file was modified — rehash if needed."""
        filename = os.path.basename(path)
        if not self._is_allowed(filename):
            return
        try:
            st = os.stat(path)
        except OSError:
            return
        self._scan_file(path, filename, st)

    def _handle_delete(self, path: str) -> None:
        """A file was deleted — mark the asset as deleted."""
        self.db.execute(
            "UPDATE assets SET status='deleted' WHERE path=? AND status='active'",
            (path,),
        )

    def _scan_file(self, path: str, filename: str, st: os.stat_result) -> None:
        """Scan a single file, inserting or updating the asset."""
        from quickmedia.scanner import Scanner
        scanner = Scanner(db=self.db, config=self.config)

        ext = os.path.splitext(filename)[1]
        asset_type = scanner._get_type(ext)
        size = st.st_size

        # Check inode match first
        existing = scanner._find_by_inode(st.st_ino, st.st_dev)
        if existing:
            if existing["path"] != path:
                self.db.execute(
                    "UPDATE assets SET path=?, scanned_at=? WHERE id=?",
                    (path, datetime.now().isoformat(), existing["id"]),
                )
            else:
                self.db.execute(
                    "UPDATE assets SET size=?, scanned_at=? WHERE id=?",
                    (size, datetime.now().isoformat(), existing["id"]),
                )
            return

        # Check hash
        hash_val = scanner._compute_hash(path)
        hash_existing = scanner._find_by_hash(hash_val)
        if hash_existing:
            return  # duplicate

        # New asset
        modified_ts = datetime.fromtimestamp(st.st_mtime).isoformat()
        created_ts = datetime.fromtimestamp(st.st_ctime).isoformat()
        now = datetime.now().isoformat()

        cursor = self.db.conn.execute(
            """INSERT INTO assets
               (hash, inode, device, path, filename, extension, asset_type,
                size, status, thumbnail_status, modified_at, created_at, scanned_at)
               VALUES (?,?,?,?,?,?,?,?, 'active','pending',?,?,?)""",
            (hash_val, st.st_ino, st.st_dev, path, filename, ext.lower(),
             asset_type, size, modified_ts, created_ts, now),
        )
        self.db.conn.commit()
        asset_id = cursor.lastrowid

        # Auto tags
        auto_tags = scanner._auto_tags(filename, asset_type, path, 0)
        scanner._link_tags(asset_id, auto_tags, source="auto")

        # Metadata
        meta = scanner._metadata.extract(path)
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

        # Thumbnail
        if asset_type in ("image", "video"):
            scanner._thumbnailer.enqueue(asset_id)
            scanner._thumbnailer.process_queue()

    def _is_allowed(self, filename: str) -> bool:
        _, ext = os.path.splitext(filename)
        if not ext:
            return False
        ext = ext.lower().lstrip(".")
        for exts in self._formats.values():
            if ext in [e.lower() for e in exts]:
                return True
        return False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
