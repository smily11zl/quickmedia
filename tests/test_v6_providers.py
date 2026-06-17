"""Tests for V6 Provider architecture and adapters."""

import os
import tempfile
import yaml
import json
from quickmedia.config import Config


class TestProviderRegistry:
    def test_gets_provider_config(self):
        """ProviderRegistry returns provider URL from config."""
        from quickmedia.providers import ProviderRegistry
        d = tempfile.mkdtemp()
        models_path = os.path.join(d, "models.yaml")
        with open(models_path, "w") as f:
            yaml.dump({"ollama": [{"name": "qwen3.5:9b", "capabilities": ["vision", "text"]}]}, f)

        cfg = Config(config_dir=d)
        registry = ProviderRegistry(cfg, models_path)
        provider = registry.get_provider("ollama")
        assert provider["url"] == "http://localhost:11434"

    def test_gets_models_filtered_by_capability(self):
        """get_models filters by capability, per-provider model lists."""
        from quickmedia.providers import ProviderRegistry
        d = tempfile.mkdtemp()
        cfg = Config(config_dir=d)
        models_path = os.path.join(d, "models.yaml")
        registry = ProviderRegistry(cfg, models_path)
        vision_models = registry.get_models("openai", capability="vision")
        assert len(vision_models) >= 1
        names = [m["name"] for m in vision_models]
        assert "gpt-4o" in names

    def test_gets_task_binding(self):
        """get_task_binding returns provider + model for a task type."""
        from quickmedia.providers import ProviderRegistry
        d = tempfile.mkdtemp()
        models_path = os.path.join(d, "models.yaml")
        with open(models_path, "w") as f:
            yaml.dump({"ollama": {"url": "http://localhost:11434", "models": [{"name": "qwen3.5:9b", "capabilities": ["vision"]}]}}, f)

        cfg = Config(config_dir=d)
        registry = ProviderRegistry(cfg, models_path)
        binding = registry.get_task_binding("vision")
        assert binding["provider"] == "ollama"
        assert binding["model"] == "qwen3.5:9b"


class TestOpenAIAdapter:
    def test_test_connection_failure(self):
        """test() returns False for unreachable URL."""
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url="http://127.0.0.1:19999/v1", api_key="test", model="gpt-4o", timeout=2)
        assert adapter.test() is False

    def test_test_connection_success(self):
        """test() returns True for reachable Ollama (OpenAI compat endpoint)."""
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434/v1/models", timeout=1)
        except Exception:
            import pytest
            pytest.skip("Ollama not running")
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url="http://localhost:11434/v1", api_key="ollama", model="qwen3.5:9b", timeout=5)
        assert adapter.test() is True
