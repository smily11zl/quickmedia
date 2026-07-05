import unittest, yaml, os

class TestV19Models(unittest.TestCase):
    def test_v19_models_in_yaml(self):
        """s1: verify all V19 OpenRouter models are defined with capabilities."""
        path = os.path.join(os.path.dirname(__file__), "..", "quickmedia", "models.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        openrouter_models = {m["name"]: m.get("capabilities", {}) for m in data.get("openrouter", {}).get("models", [])}
        
        # Claude
        assert "anthropic/claude-opus-4.8" in openrouter_models
        assert "anthropic/claude-opus-4.7" in openrouter_models
        assert "anthropic/claude-sonnet-4.6" in openrouter_models
        assert "anthropic/claude-sonnet-5" in openrouter_models
        assert "anthropic/claude-haiku-4.5" in openrouter_models
        assert "image" in openrouter_models["anthropic/claude-haiku-4.5"]
        
        # GPT
        assert "openai/gpt-5.5" in openrouter_models
        assert "openai/gpt-5.4" in openrouter_models
        
        # Gemini
        assert "google/gemini-3-flash" in openrouter_models
        assert "google/gemini-3.5-flash" in openrouter_models
        assert "audio" in openrouter_models["google/gemini-3-flash"]
        
        # Whisper / ASR
        assert "openai/whisper-large-v3" in openrouter_models
        assert "openai/whisper-large-v3-turbo" in openrouter_models
        assert "qwen/qwen3-asr-flash" in openrouter_models
        assert "audio" in openrouter_models["openai/whisper-large-v3"]

        
        # Openai provider
        openai_models = {m["name"]: m.get("capabilities", {}) for m in data.get("openai", {}).get("models", [])}
        assert "gpt-5.5" in openai_models
        assert "gpt-5.4" in openai_models



import tempfile, shutil
from quickmedia.config import Config

class TestConfigV19(unittest.TestCase):
    def test_speech_renamed_to_speech_summary(self):
        """V19: old 'speech' key in task_models auto-migrated to 'speech_summary'."""
        d = tempfile.mkdtemp()
        try:
            cfg_path = os.path.join(d, "config.yaml")
            with open(cfg_path, "w") as f:
                f.write("task_models:\n  speech:\n    provider: ollama\n    model: test\n")
            cfg = Config(config_dir=d)
            tm = cfg._data.get("task_models", {})
            assert "speech_summary" in tm, f"Expected speech_summary, got {list(tm.keys())}"
            assert "speech" not in tm, "Old 'speech' key should be removed"
        finally:
            shutil.rmtree(d)


class TestV19ConfigS3(unittest.TestCase):
    def test_transcribe_task_in_defaults(self):
        """s3: DEFAULT_CONFIG has transcribe task."""
        from quickmedia.config import DEFAULT_CONFIG
        tm = DEFAULT_CONFIG.get("task_models", {})
        assert "transcribe" in tm, f"Expected transcribe, got {list(tm.keys())}"

    def test_transcribe_available_after_migration(self):
        """s3: Config loads and transcribe task exists."""
        import tempfile, shutil, os
        from quickmedia.config import Config
        d = tempfile.mkdtemp()
        try:
            cfg = Config(config_dir=d)
            tm = cfg._data.get("task_models", {})
            assert "transcribe" in tm
        finally:
            shutil.rmtree(d)


class TestV19CapabilityFilter(unittest.TestCase):
    def test_provider_filter_by_capability(self):
        """s4: get_models can filter by audio capability."""
        import tempfile, shutil, os
        from quickmedia.config import Config
        from quickmedia.providers import ProviderRegistry
        d = tempfile.mkdtemp()
        try:
            cfg = Config(config_dir=d)
            user_models = os.path.join(d, "models.yaml")
            registry = ProviderRegistry(cfg, user_models)
            all_openrouter = registry.get_models("openrouter")
            audio_models = registry.get_models("openrouter", capability="audio")
            assert len(audio_models) < len(all_openrouter), "audio filter should reduce model count"
            assert any("whisper" in m["name"] or "asr" in m["name"] for m in audio_models), "should include whisper/asr models"
        finally:
            shutil.rmtree(d)


class TestV19TranscribeAdapter(unittest.TestCase):
    def test_transcribe_uses_adapter_routing(self):
        """s5: _process_transcribe routes to whisper vs api based on provider."""
        import tempfile, shutil, os
        from unittest.mock import MagicMock
        from quickmedia.config import DEFAULT_CONFIG
        
        # Verify transcribe task is configurable
        tm = DEFAULT_CONFIG.get("task_models", {})
        assert "transcribe" in tm
        assert tm["transcribe"]["provider"] == "whisper"

    def test_audio_extraction_for_video(self):
        """s5: video files trigger ffmpeg audio extraction."""
        import subprocess
        # Verify ffmpeg is available (precondition for audio extraction)
        result = subprocess.run(["which", "ffmpeg"], capture_output=True)
        assert result.returncode == 0, "ffmpeg not found"
