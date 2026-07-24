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
        "timeout": 300,
        "video_frames": 3,
    },
    "providers": {
        "ollama": {
            "url": "http://localhost:11434",
        },
    },
    "task_models": {
        "vision": {"provider": "ollama", "model": "qwen3.5:9b"},
        "text": {"provider": "ollama", "model": "qwen3.5:9b"},
        "speech_summary": {"provider": "ollama", "model": "qwen3.5:9b"},
        "transcribe": {"provider": "whisper", "model": "small"},
        "video_summary": {"provider": "ollama", "model": "qwen3.5:9b"},
        "embedding": {"provider": "ollama", "model": "qwen3-embedding:8b"},
        "search_ai": {"provider": "", "model": ""},
        "aggregation": {"provider": "", "model": ""},
    },
    "watch_paths": [],
    "formats": {
        "image": ["jpg", "jpeg", "png", "gif", "webp", "heic", "svg", "avif", "bmp", "tiff", "tif", "ico"],
        "video": ["mp4", "mov", "avi"],
        "audio": ["mp3", "wav", "m4a"],
        "document": ["pdf", "txt", "md", "csv", "json", "xlsx", "docx"],
    },
    "semantic": {
        "top_k": 2,
    },
    "system": {
        "max_file_size": 524288000,  # 500MB
        "thumbnail_size": 256,
        "db_path": None,  # resolved at runtime
        "thumbnails_path": None,  # resolved at runtime
        "chroma_db_path": None,  # resolved at runtime
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
        self._migrate_if_needed()
        self._migrate_watch_paths()
        self._fill_missing_task_models()
        self._resolve_paths()
        self._ensure_models_yaml()

    def _migrate_watch_paths(self) -> None:
        """V10: migrate watch_paths to dict format with name/enabled."""
        wp = self._data.get("watch_paths")
        if not wp:
            return
        changed = False
        new_wp = []
        for i, item in enumerate(wp):
            if isinstance(item, str):
                new_wp.append({
                    "name": f"文件夹 {i+1}",
                    "path": item,
                    "recursive": True,
                    "max_depth": 3,
                    "enabled": True,
                })
                changed = True
            elif isinstance(item, dict):
                if "name" not in item:
                    item["name"] = f"文件夹 {i+1}"
                    changed = True
                if "enabled" not in item:
                    item["enabled"] = True
                    changed = True
                new_wp.append(item)
            else:
                new_wp.append(item)
        if changed:
            self._data["watch_paths"] = new_wp
            self._save()

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

    def _migrate_if_needed(self) -> None:
        """Migrate old ai.* config to providers + task_models if needed."""
        if self._data.get("providers") or not self._data.get("ai", {}).get("ollama_url"):
            return
        ollama_url = self._data["ai"]["ollama_url"]
        model = self._data["ai"].get("model", "qwen3.5:9b")
        self._data.setdefault("providers", {})
        self._data["providers"]["ollama"] = {"url": ollama_url}
        self._data["task_models"] = {
            task: {"provider": "ollama", "model": model}
            for task in ("vision", "text", "speech_summary", "video_summary")
        }

    def _fill_missing_task_models(self) -> None:
        """Fill in any missing task types from DEFAULT_CONFIG. Migrate old keys. Saves if changed."""
        # V19: rename speech → speech_summary (check raw file, not merged defaults)
        current = self._data.setdefault("task_models", {})
        if "speech" in current:
            # Only rename if the file itself has "speech" and wasn't already upgraded
            raw = {}
            if os.path.isfile(self._filepath):
                try:
                    import yaml
                    with open(self._filepath) as f:
                        raw = yaml.safe_load(f) or {}
                except Exception:
                    pass
            file_tm = raw.get("task_models", {})
            if "speech" in file_tm and "speech_summary" not in file_tm:
                current["speech_summary"] = dict(current["speech"])
                del current["speech"]
                self._save()
        defaults = DEFAULT_CONFIG.get("task_models") or {}
        changed = False
        for task, binding in defaults.items():
            if task not in current:
                current[task] = dict(binding)
                changed = True
        if changed:
            self._save()

    def _ensure_models_yaml(self) -> None:
        """Copy models.yaml from package to user dir on first startup; merge on upgrade."""
        import shutil
        package_models = os.path.join(os.path.dirname(__file__), "models.yaml")
        user_models = os.path.join(self.config_dir, "models.yaml")
        if not os.path.isfile(package_models):
            return
        if not os.path.isfile(user_models):
            os.makedirs(self.config_dir, exist_ok=True)
            shutil.copy2(package_models, user_models)
            return
        with open(package_models, "r") as f:
            pkg = yaml.safe_load(f)
        with open(user_models, "r") as f:
            usr = yaml.safe_load(f)
        changed = False
        for provider_name, pkg_data in (pkg or {}).items():
            pkg_models = pkg_data.get("models", []) if isinstance(pkg_data, dict) else []
            if provider_name not in usr:
                usr[provider_name] = pkg_data
                changed = True
            elif isinstance(usr[provider_name], dict) and "models" in usr[provider_name]:
                usr_names = {m["name"] for m in usr[provider_name].get("models", [])}
                for m in pkg_models:
                    if m["name"] not in usr_names:
                        usr[provider_name]["models"].append(m)
                        changed = True
            else:
                # Old flat format — replace with new structure
                usr[provider_name] = pkg_data
                changed = True
        if changed:
            with open(user_models, "w") as f:
                yaml.dump(usr, f, allow_unicode=True, sort_keys=False)
