"""Tests for V6 API endpoints — provider management."""

import os
import tempfile
from quickmedia.api.server import create_app
from quickmedia.database import Database
from quickmedia.config import Config


def _make_client(config_dir=None):
    """Create a test client with a temporary config dir."""
    if config_dir is None:
        config_dir = tempfile.mkdtemp()
    db_dir = tempfile.mkdtemp()
    db_path = os.path.join(db_dir, "test.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    thumb_dir = os.path.join(config_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    app = create_app(db, cfg, thumb_dir)
    from fastapi.testclient import TestClient
    return TestClient(app), config_dir


class TestProvidersAPI:
    def test_get_providers_returns_full_config(self):
        """GET /api/providers returns providers + task_models."""
        client, _ = _make_client()
        r = client.get("/api/providers")
        assert r.status_code == 200
        data = r.json()
        assert "providers" in data
        assert "task_models" in data
        assert data["providers"]["ollama"]["url"] == "http://localhost:11434"
        assert data["task_models"]["vision"]["provider"] == "ollama"

    def test_put_providers_updates_config(self):
        """PUT /api/providers persists new provider and task model config."""
        client, d = _make_client()
        new_config = {
            "providers": {
                "ollama": {"url": "http://localhost:11434"},
                "openrouter": {"url": "https://openrouter.ai/api/v1"},
            },
            "task_models": {
                "vision": {"provider": "openrouter", "model": "gpt-4o"},
                "text": {"provider": "ollama", "model": "qwen3.5:9b"},
                "speech": {"provider": "ollama", "model": "qwen3.5:9b"},
                "video_summary": {"provider": "ollama", "model": "qwen3.5:9b"},
            },
        }
        r = client.put("/api/providers", json=new_config)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        # Verify persistence
        cfg = Config(config_dir=d)
        assert cfg.get("providers.openrouter.url") == "https://openrouter.ai/api/v1"
        assert cfg.get("task_models.vision.provider") == "openrouter"

    def test_api_key_written_to_env(self):
        """PUT /api/providers saves api_key to .env, not config.yaml."""
        client, d = _make_client()
        new_config = {
            "providers": {
                "ollama": {"url": "http://localhost:11434"},
                "openrouter": {"url": "https://openrouter.ai/api/v1", "api_key": "sk-test-123"},
            },
            "task_models": {},
        }
        r = client.put("/api/providers", json=new_config)
        assert r.status_code == 200

        # api_key NOT in config.yaml
        cfg = Config(config_dir=d)
        assert cfg.get("providers.openrouter.api_key") is None

        # api_key IS in .env
        import os
        env_path = os.path.join(d, ".env")
        assert os.path.isfile(env_path)
        with open(env_path) as f:
            content = f.read()
        assert "OPENROUTER_API_KEY=sk-test-123" in content

    def test_test_connection_failure(self):
        """POST /api/providers/test returns error for unreachable URL."""
        client, _ = _make_client()
        r = client.post("/api/providers/test", json={
            "provider": "custom",
            "url": "http://127.0.0.1:19999/v1",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "error" in data

    def test_test_connection_ollama(self):
        """POST /api/providers/test returns ok for Ollama if running."""
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:11434/v1/models", timeout=1)
        except Exception:
            import pytest
            pytest.skip("Ollama not running")
        client, _ = _make_client()
        r = client.post("/api/providers/test", json={
            "provider": "ollama",
            "url": "http://localhost:11434/v1",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
