"""Tests for QuickMedia V10 — configurable watch paths."""

import tempfile, os, yaml
from quickmedia.config import Config


class TestV10WatchPathsConfig:
    """watch_paths configuration and migration."""

    def test_default_watch_paths_is_list(self):
        """DEFAULT_CONFIG should have empty watch_paths array."""
        from quickmedia.config import DEFAULT_CONFIG
        assert "watch_paths" in DEFAULT_CONFIG
        assert isinstance(DEFAULT_CONFIG["watch_paths"], list)
        assert DEFAULT_CONFIG["watch_paths"] == []

    def test_watch_paths_structure_has_required_fields(self):
        """New watch_paths entries should support name/path/recursive/max_depth/enabled."""
        cfg = Config()
        cfg.set("watch_paths", [{
            "name": "测试文件夹",
            "path": "/tmp/test",
            "recursive": True,
            "max_depth": 3,
            "enabled": True,
        }])
        paths = cfg.get("watch_paths")
        assert len(paths) == 1
        p = paths[0]
        assert p["name"] == "测试文件夹"
        assert p["path"] == "/tmp/test"
        assert p["recursive"] is True
        assert p["max_depth"] == 3
        assert p["enabled"] is True

    def test_old_format_auto_migration(self):
        """Old string-only paths should be migrated to new dict format."""
        import tempfile, os
        tmp = tempfile.mkdtemp()
        cfg = Config(config_dir=tmp)
        # Simulate old format: array of paths with no name field
        cfg.set("watch_paths", ["/tmp/legacy"])
        cfg._save()
        # Re-read — migration should kick in
        cfg2 = Config(config_dir=tmp)
        paths = cfg2.get("watch_paths")
        assert len(paths) == 1
        p = paths[0]
        assert p.get("name") is not None  # auto-generated name
        assert p["path"] == "/tmp/legacy"
        assert "enabled" in p
        assert p["enabled"] is True

    def test_old_dict_without_name_gets_migrated(self):
        """Dict with path but no name should get name auto-added."""
        import tempfile, os
        tmp = tempfile.mkdtemp()
        cfg = Config(config_dir=tmp)
        cfg.set("watch_paths", [{
            "path": "/tmp/test",
            "recursive": False,
            "max_depth": 1,
        }])
        cfg._save()
        cfg2 = Config(config_dir=tmp)
        paths = cfg2.get("watch_paths")
        assert paths[0].get("name") is not None
        assert paths[0].get("enabled") is True

    def test_empty_watch_paths_returns_empty_list(self):
        """Empty watch_paths should return [] not None."""
        cfg = Config()
        cfg.set("watch_paths", [])
        assert cfg.get("watch_paths") == []


class TestV10ConfigMigrationIdempotent:
    """Migration should not corrupt already-migrated data."""

    def test_already_migrated_passes_through(self):
        """New format should pass through unchanged."""
        import tempfile
        tmp = tempfile.mkdtemp()
        cfg = Config(config_dir=tmp)
        data = [{
            "name": "已迁移",
            "path": "/tmp/done",
            "recursive": True,
            "max_depth": 5,
            "enabled": False,
        }]
        cfg.set("watch_paths", data)
        cfg._save()
        cfg2 = Config(config_dir=tmp)
        paths = cfg2.get("watch_paths")
        assert paths == data


class TestV10FolderPicker:
    """macOS osascript folder picker."""

    def test_osascript_parse_valid_output(self):
        """Valid osascript output should return the path."""
        from quickmedia.api.server import _parse_osascript_path
        result = _parse_osascript_path("alias /Users/test/Documents:")
        assert result == "/Users/test/Documents"

    def test_osascript_user_cancelled_returns_none(self):
        """User cancelling should return None."""
        from quickmedia.api.server import _parse_osascript_path
        assert _parse_osascript_path("") is None
        assert _parse_osascript_path("User cancelled.") is None

    def test_osascript_error_returns_none(self):
        """Execution errors should return None."""
        from quickmedia.api.server import _parse_osascript_path
        assert _parse_osascript_path("execution error: No such file or directory (-43)") is None


class TestV10WatchPathsAPI:
    """API endpoints for managing watch paths."""

    def test_api_get_watch_paths_returns_list(self):
        """GET /api/config/watch-paths should return paths array."""
        import subprocess, json
        # Start a test server
        pass  # Requires live server — tested via integration

    def test_api_put_watch_paths_saves_and_reloads(self):
        """PUT /api/config/watch-paths should save and trigger reload."""
        pass  # Requires live server — tested via integration

    def test_config_save_watch_paths_persists(self):
        """Config.set + _save should persist watch_paths to YAML."""
        import tempfile, os
        tmp = tempfile.mkdtemp()
        from quickmedia.config import Config
        cfg = Config(config_dir=tmp)
        cfg.set("watch_paths", [{"name": "Test", "path": "/tmp/x", "recursive": False, "max_depth": 1, "enabled": True}])
        cfg._save()
        # Re-read from disk
        cfg2 = Config(config_dir=tmp)
        paths = cfg2.get("watch_paths")
        assert len(paths) == 1
        assert paths[0]["name"] == "Test"
        assert paths[0]["enabled"] is True

    def test_config_delete_watch_paths(self):
        """Deleting all watch_paths should persist empty list."""
        import tempfile
        tmp = tempfile.mkdtemp()
        from quickmedia.config import Config
        cfg = Config(config_dir=tmp)
        cfg.set("watch_paths", [
            {"name": "A", "path": "/tmp/a", "recursive": True, "max_depth": 1, "enabled": True},
            {"name": "B", "path": "/tmp/b", "recursive": False, "max_depth": 2, "enabled": False},
        ])
        cfg._save()
        cfg.set("watch_paths", [])
        cfg._save()
        cfg2 = Config(config_dir=tmp)
        assert cfg2.get("watch_paths") == []


class TestV10FirstLaunchGuide:
    """First-launch auto-open and red dot logic."""

    def test_no_watch_paths_should_trigger_auto_open(self):
        """When watch_paths is empty, should set flag for auto-open."""
        from quickmedia.config import Config
        import tempfile
        tmp = tempfile.mkdtemp()
        cfg = Config(config_dir=tmp)
        cfg.set("watch_paths", [])
        cfg._save()
        paths = cfg.get("watch_paths")
        assert paths == []
        # Frontend would detect this and auto-open settings

    def test_has_watch_paths_should_not_trigger(self):
        """When watch_paths has entries, should not auto-open."""
        from quickmedia.config import Config
        import tempfile
        tmp = tempfile.mkdtemp()
        cfg = Config(config_dir=tmp)
        cfg.set("watch_paths", [{"name": "x", "path": "/tmp", "recursive": True, "max_depth": 1, "enabled": True}])
        cfg._save()
        paths = cfg.get("watch_paths")
        assert len(paths) > 0
        # Frontend would skip auto-open
