"""Tests for quickmedia.cli — command-line interface."""

import io
import sys
import os
import tempfile
from pathlib import Path
import pytest
from quickmedia.cli import main
from quickmedia.config import Config
from quickmedia.database import Database


def _tmp_config_dir():
    return tempfile.mkdtemp()


def _run_cli(args: list[str], config_dir: str) -> str:
    """Run the CLI with given args and capture stdout."""
    stdout = io.StringIO()
    old_argv = sys.argv
    old_stdout = sys.stdout
    old_home = os.environ.get("HOME")
    try:
        sys.argv = ["quickmedia"] + args
        sys.stdout = stdout
        os.environ["HOME"] = str(Path.home())
        # Use a custom config via env-like injection — pass through constructor args
        # We'll use a monkey-patched approach via main's internals
        main(config_dir=config_dir)
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        if old_home:
            os.environ["HOME"] = old_home
    return stdout.getvalue()


class TestStatsCommand:
    """quickmedia stats command."""

    def test_stats_empty_database(self):
        """stats shows zero counts for empty database."""
        config_dir = _tmp_config_dir()
        output = _run_cli(["stats"], config_dir)
        assert "素材总数: 0" in output

    def test_stats_with_assets(self):
        """stats reflects assets in the database."""
        config_dir = _tmp_config_dir()
        # Pre-populate database
        db_path = os.path.join(config_dir, "data.db")
        db = Database(db_path)
        db.execute("""
            INSERT INTO assets (hash, path, filename, extension, asset_type, size)
            VALUES ('abc', '/tmp/a.jpg', 'a.jpg', '.jpg', 'image', 100)
        """)
        db.close()
        output = _run_cli(["stats"], config_dir)
        assert "素材总数: 1" in output
        assert "图片: 1" in output

    def test_stats_ignores_deleted(self):
        """stats excludes deleted assets."""
        config_dir = _tmp_config_dir()
        db_path = os.path.join(config_dir, "data.db")
        db = Database(db_path)
        db.execute("""
            INSERT INTO assets (hash, path, filename, extension, asset_type, size, status)
            VALUES ('abc', '/tmp/a.jpg', 'a.jpg', '.jpg', 'image', 100, 'active'),
                   ('def', '/tmp/b.jpg', 'b.jpg', '.jpg', 'image', 200, 'deleted')
        """)
        db.close()
        output = _run_cli(["stats"], config_dir)
        assert "素材总数: 1" in output
        assert "图片: 1" in output


class TestMainEntry:
    """quickmedia with no args shows usage."""

    def test_no_args_shows_usage(self):
        config_dir = _tmp_config_dir()
        output = _run_cli([], config_dir)
        assert "usage" in output.lower() or "quickmedia" in output.lower()
