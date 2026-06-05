"""Configuration management for QuickMedia.

Reads and writes ~/.asset-manager/config.yaml.
Supports dot-notation key access (e.g., "ai.model").
"""

import os
import yaml
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = {
    "ai": {
        "ollama_url": "http://localhost:11434",
        "model": "qwen3.5:9b",
        "timeout": 60,
    },
    "watch_paths": [],
    "formats": {
        "image": ["jpg", "jpeg", "png", "gif", "webp", "heic", "svg"],
        "video": ["mp4", "mov", "avi"],
        "audio": ["mp3", "wav", "m4a"],
        "document": ["pdf", "txt", "md"],
    },
    "system": {
        "max_file_size": 524288000,  # 500MB
        "thumbnail_size": 256,
        "db_path": None,  # resolved at runtime
        "thumbnails_path": None,  # resolved at runtime
    },
    "web": {
        "default_port": 8088,
        "auto_open_browser": True,
    },
}


class Config:
    """QuickMedia configuration loaded from YAML, backed by defaults."""

    def __init__(
        self,
        config_dir: str | None = None,
        config_filename: str = "config.yaml",
    ):
        if config_dir is None:
            config_dir = str(Path.home() / ".asset-manager")
        self.config_dir = config_dir
        self.config_filename = config_filename
        self._filepath = os.path.join(config_dir, config_filename)
        self._data: dict = self._deep_copy(DEFAULT_CONFIG)
        self._load()
        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """Fill in computed paths that depend on config_dir."""
        system = self._data.setdefault("system", {})
        if system.get("db_path") is None:
            system["db_path"] = os.path.join(self.config_dir, "data.db")
        if system.get("thumbnails_path") is None:
            system["thumbnails_path"] = os.path.join(self.config_dir, "thumbnails")

    def _load(self) -> None:
        """Load config from YAML file, deep-merging into defaults."""
        if not os.path.isfile(self._filepath):
            return
        with open(self._filepath, "r") as f:
            file_data = yaml.safe_load(f)
        if file_data and isinstance(file_data, dict):
            self._deep_merge(self._data, file_data)

    def _save(self) -> None:
        """Save current config to YAML file."""
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self._filepath, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def get(self, key: str) -> Any:
        """Get a config value by dot-notation key, e.g. 'ai.model'."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if node is None:
                return None
            if isinstance(node, list):
                try:
                    idx = int(part)
                    node = node[idx]
                except (ValueError, IndexError):
                    return None
            elif isinstance(node, dict):
                node = node.get(part)
            else:
                return None
        return node

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dot-notation key, persists to file."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if isinstance(node, list):
                idx = int(part)
                while idx >= len(node):
                    node.append({})
                node = node[idx]
            elif isinstance(node, dict):
                if part not in node:
                    node[part] = {}
                node = node[part]
        last = parts[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value
        self._save()

    @staticmethod
    def _deep_copy(data: dict) -> dict:
        """Deep copy a nested dict/list structure."""
        if isinstance(data, dict):
            return {k: Config._deep_copy(v) for k, v in data.items()}
        if isinstance(data, list):
            return [Config._deep_copy(v) for v in data]
        return data

    @staticmethod
    def _deep_merge(base: dict, overlay: dict) -> None:
        """Merge overlay into base in-place, recursively."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value
