"""Tests for V6 config migration and models.yaml."""

import os
import tempfile
import yaml
from quickmedia.config import Config, DEFAULT_CONFIG


def test_config_migration_from_old_ai_fields():
    """Old ai.ollama_url + ai.model → providers + task_models auto-migration."""
    d = tempfile.mkdtemp()

    # Simulate old config (pre-V6)
    old_config = {"ai": {"ollama_url": "http://localhost:11434", "model": "qwen3.5:9b"}}
    config_path = os.path.join(d, "config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(old_config, f)

    cfg = Config(config_dir=d)

    # New fields should exist
    assert cfg.get("providers") is not None
    assert cfg.get("providers.ollama") is not None
    assert cfg.get("providers.ollama.url") == "http://localhost:11434"
    assert cfg.get("task_models") is not None
    assert cfg.get("task_models.vision") == {"provider": "ollama", "model": "qwen3.5:9b"}
    assert cfg.get("task_models.text") == {"provider": "ollama", "model": "qwen3.5:9b"}
    assert cfg.get("task_models.speech") == {"provider": "ollama", "model": "qwen3.5:9b"}
    assert cfg.get("task_models.video_summary") == {"provider": "ollama", "model": "qwen3.5:9b"}


def test_models_yaml_copy_on_first_startup():
    """models.yaml copied from package to user dir on first startup."""
    d = tempfile.mkdtemp()
    cfg = Config(config_dir=d)
    models_path = os.path.join(d, "models.yaml")
    assert os.path.isfile(models_path), "models.yaml should be created on first startup"

    with open(models_path) as f:
        data = yaml.safe_load(f)
    assert "ollama" in data
    assert "openrouter" in data


def test_models_yaml_merge_on_upgrade():
    """New models from package merge into existing user models.yaml."""
    d = tempfile.mkdtemp()
    # First run creates user copy
    cfg1 = Config(config_dir=d)
    models_path = os.path.join(d, "models.yaml")

    # Simulate user adding a custom model (new nested structure)
    with open(models_path) as f:
        data = yaml.safe_load(f)
    data["ollama"]["models"].append({"name": "custom-model:latest", "capabilities": ["vision"]})
    with open(models_path, "w") as f:
        yaml.dump(data, f)

    # "Upgrade" — re-init should merge, keeping user's custom model
    cfg2 = Config(config_dir=d)
    with open(models_path) as f:
        merged = yaml.safe_load(f)
    names = [m["name"] for m in merged["ollama"]["models"]]
    assert "custom-model:latest" in names, "User-added model should be preserved"
    assert "qwen3.5:9b" in names, "Default model should still be present"


def test_default_config_has_providers_and_task_models():
    """DEFAULT_CONFIG includes the new V6 fields."""
    cfg = Config()
    assert "providers" in cfg._data
    assert "task_models" in cfg._data
    assert cfg.get("providers.ollama.url") == "http://localhost:11434"
    assert cfg.get("task_models.vision.model") == "qwen3.5:9b"
