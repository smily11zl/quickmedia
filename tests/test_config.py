"""Tests for quickmedia.config — configuration management."""

import tempfile
import os
from pathlib import Path
import quickmedia.config as config


def _tmp_config(**kwargs):
    """Create a Config with a temp directory, isolated from real config."""
    return config.Config(config_dir=tempfile.mkdtemp(), **kwargs)


class TestConfigDefaults:
    """Default values when no config file exists."""

    def test_default_config_dir(self):
        cfg = _tmp_config()
        assert cfg.config_dir != str(Path.home() / ".asset-manager")

    def test_default_ollama_url(self):
        cfg = _tmp_config()
        assert cfg.get("ai.ollama_url") == "http://localhost:11434"

    def test_default_model(self):
        cfg = _tmp_config()
        assert cfg.get("ai.model") == "qwen3.5:9b"

    def test_default_db_path(self):
        cfg = _tmp_config()
        assert cfg.get("system.db_path").endswith("data.db")

    def test_default_thumbnail_size(self):
        cfg = _tmp_config()
        assert cfg.get("system.thumbnail_size") == 256

    def test_default_watch_paths(self):
        cfg = _tmp_config()
        assert cfg.get("watch_paths") == []

    def test_default_formats(self):
        cfg = _tmp_config()
        formats = cfg.get("formats")
        assert "jpg" in formats["image"]
        assert "mp4" in formats["video"]
        assert "pdf" in formats["document"]

    def test_get_nonexistent_key(self):
        cfg = _tmp_config()
        assert cfg.get("nonexistent.key") is None


class TestConfigFile:
    """Configuration loaded from a YAML file."""

    def test_load_from_file(self):
        yaml_content = """\
ai:
  model: qwen3.5:4b
system:
  thumbnail_size: 128
watch_paths:
  - path: ~/Desktop/test_media
    recursive: true
    max_depth: 2
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            with open(config_path, "w") as f:
                f.write(yaml_content)
            cfg = config.Config(config_dir=tmpdir, config_filename="config.yaml")
            assert cfg.get("ai.model") == "qwen3.5:4b"
            assert cfg.get("system.thumbnail_size") == 128

    def test_file_overrides_defaults(self):
        yaml_content = "ai:\n  model: custom-model"
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.yaml")
            with open(config_path, "w") as f:
                f.write(yaml_content)
            cfg = config.Config(config_dir=tmpdir, config_filename="config.yaml")
            assert cfg.get("ai.model") == "custom-model"
            assert cfg.get("ai.ollama_url") == "http://localhost:11434"


class TestConfigSet:
    """Setting configuration values."""

    def test_set_and_get(self):
        cfg = _tmp_config()
        cfg.set("ai.model", "qwen3.5:27b")
        assert cfg.get("ai.model") == "qwen3.5:27b"

    def test_set_persists_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = config.Config(config_dir=tmpdir, config_filename="config.yaml")
            cfg.set("watch_paths.0.path", "~/Downloads")
            cfg2 = config.Config(config_dir=tmpdir, config_filename="config.yaml")
            paths = cfg2.get("watch_paths")
            assert len(paths) == 1
            assert paths[0]["path"] == "~/Downloads"
