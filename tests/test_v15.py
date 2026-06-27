"""Tests for QuickMedia V15 — AI Search + Node Tree List."""
import os, tempfile, pytest
from fastapi.testclient import TestClient
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.api.server import create_app


@pytest.fixture
def client():
    config_dir = tempfile.mkdtemp()
    db_path = os.path.join(config_dir, "data.db")
    db = Database(db_path)
    cfg = Config(config_dir=config_dir)
    thumb_dir = os.path.join(config_dir, "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    app = create_app(db, cfg, thumb_dir)
    with TestClient(app) as c:
        yield c


# ── s1: search_ai prompt + task_models 基础设施 ──

class TestDefaultPromptsSearchAi:
    """RED: DEFAULT_PROMPTS must include search_ai entry."""

    def test_search_ai_in_default_prompts(self):
        """DEFAULT_PROMPTS contains search_ai with required structure."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS

        assert "search_ai" in DEFAULT_PROMPTS, "DEFAULT_PROMPTS missing search_ai"
        sa = DEFAULT_PROMPTS["search_ai"]
        assert "system_format" in sa
        assert "default" in sa
        assert "custom" in sa
        assert "presets" in sa

    def test_search_ai_system_format_requires_json(self):
        """search_ai system_format requires JSON output with asset_ids."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS

        fmt = str(DEFAULT_PROMPTS["search_ai"]["system_format"])
        assert "asset_ids" in fmt
        assert "JSON" in fmt

    def test_search_ai_default_prompt_has_placeholders(self):
        """search_ai default prompt contains {assets} and {query} placeholders."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS

        default = str(DEFAULT_PROMPTS["search_ai"]["default"])
        assert "{assets}" in default or "assets" in default.lower()
        assert "{query}" in default or "query" in default.lower()

    def test_search_ai_default_prompt_includes_description(self):
        """search_ai default prompt describes format with 描述 and 标签 fields."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS

        default = str(DEFAULT_PROMPTS["search_ai"]["default"])
        assert "描述" in default, "default prompt should mention 描述 field"


class TestDefaultConfigTaskModelsSearchAi:
    """RED: DEFAULT_CONFIG.task_models must include search_ai."""

    def test_search_ai_in_default_task_models(self):
        """DEFAULT_CONFIG.task_models contains search_ai."""
        from quickmedia.config import DEFAULT_CONFIG

        tm = DEFAULT_CONFIG.get("task_models") or {}
        assert "search_ai" in tm, "DEFAULT_CONFIG.task_models missing search_ai"


class TestPromptConfigSearchAi:
    """RED: PromptConfig loads and returns search_ai prompt."""

    def test_get_prompt_search_ai(self):
        """PromptConfig.get_prompt('search_ai') returns combined prompt."""
        from quickmedia.prompt_config import PromptConfig

        d = tempfile.mkdtemp()
        pc = PromptConfig(d)
        prompt = pc.get_prompt("search_ai")
        assert len(prompt) > 0
        assert "JSON" in prompt or "json" in prompt.lower()
        assert "asset_ids" in prompt

    def test_search_ai_custom_override(self):
        """Custom search_ai prompt takes priority over default."""
        from quickmedia.prompt_config import PromptConfig

        d = tempfile.mkdtemp()
        pc = PromptConfig(d)
        custom_text = "自定义搜索逻辑：按文件日期优先"
        pc.save("search_ai", custom_text)
        prompt = pc.get_prompt("search_ai")
        assert custom_text in prompt
        assert "asset_ids" in prompt  # system_format still appended


class TestFillMissingTaskModelsSearchAi:
    """RED: _fill_missing_task_models auto-fills search_ai."""

    def test_fill_missing_adds_search_ai(self):
        """_fill_missing_task_models copies search_ai from DEFAULT_CONFIG."""
        from quickmedia.config import Config, DEFAULT_CONFIG

        d = tempfile.mkdtemp()
        cfg = Config(config_dir=d)

        tm = cfg.get("task_models") or {}
        assert "search_ai" in tm, "_fill_missing_task_models did not add search_ai"

        default_val = DEFAULT_CONFIG["task_models"]["search_ai"]
        actual_val = tm["search_ai"]
        assert actual_val == default_val, f"Expected {default_val}, got {actual_val}"


class TestApiPromptsSearchAi:
    """RED: GET /api/prompts returns search_ai section."""

    def test_get_prompts_includes_search_ai(self, client):
        """GET /api/prompts response contains search_ai."""
        r = client.get("/api/prompts")
        assert r.status_code == 200
        data = r.json()
        assert "search_ai" in data, "API /api/prompts missing search_ai"
        sa = data["search_ai"]
        assert "system_format" in sa
        assert "default" in sa
        assert "custom" in sa
        assert "presets" in sa


# ── s3: /api/search?mode=ai 端点实现 ──

class TestSearchAiAssets:
    """RED: search_ai_assets function builds prompt and parses results."""

    def test_search_ai_assets_function_exists(self):
        """search_ai_assets is importable from search module."""
        from quickmedia.search import search_ai_assets
        assert callable(search_ai_assets)

    def test_format_asset_with_video_summary(self):
        """Asset text uses video_summary first for videos."""
        from quickmedia.search import _format_asset_text

        asset = {
            "id": 1, "filename": "test.mp4", "asset_type": "video",
            "video_summary": "综合视频总结", "visual_description": "视觉描述", "ai_summary": None,
            "tags": [{"name": "标签1"}, {"name": "标签2"}],
        }
        text = _format_asset_text(asset)
        assert "[1]" in text
        assert "test.mp4" in text
        assert "video" in text
        assert "综合视频总结" in text
        assert "标签1" in text

    def test_format_asset_falls_back_to_visual_description(self):
        """Without video_summary, use visual_description."""
        from quickmedia.search import _format_asset_text

        asset = {
            "id": 2, "filename": "img.png", "asset_type": "image",
            "video_summary": None, "visual_description": "图片描述", "ai_summary": None,
            "tags": [],
        }
        text = _format_asset_text(asset)
        assert "图片描述" in text

    def test_format_asset_falls_back_to_ai_summary(self):
        """Without video_summary or visual_description, use ai_summary."""
        from quickmedia.search import _format_asset_text

        asset = {
            "id": 3, "filename": "doc.txt", "asset_type": "document",
            "video_summary": None, "visual_description": None, "ai_summary": "文档摘要",
            "tags": [],
        }
        text = _format_asset_text(asset)
        assert "文档摘要" in text

    def test_format_asset_no_description_shows_wu(self):
        """Asset with no description shows 无 for tags."""
        from quickmedia.search import _format_asset_text

        asset = {
            "id": 4, "filename": "unknown.bin", "asset_type": "other",
            "video_summary": None, "visual_description": None, "ai_summary": None,
            "tags": [],
        }
        text = _format_asset_text(asset)
        assert "无" in text  # tags displayed as 无 when empty

    def test_parse_search_ai_result(self):
        """parse_search_ai_result extracts asset_ids from JSON."""
        from quickmedia.search import parse_search_ai_result

        assert parse_search_ai_result('{"asset_ids": [1, 5, 23]}') == [1, 5, 23]
        assert parse_search_ai_result('{"asset_ids": []}') == []
        assert parse_search_ai_result("invalid json") == []
        assert parse_search_ai_result("") == []


class TestSearchAiApi:
    """RED: GET /api/search?mode=ai returns proper response."""

    def test_search_ai_empty_query_returns_empty(self, client):
        """Empty query returns empty items."""
        r = client.get("/api/search", params={"q": "", "mode": "ai"})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["items"] == []

    def test_search_ai_returns_structure(self, client):
        """mode=ai with query returns items + counts structure."""
        r = client.get("/api/search", params={"q": "test", "mode": "ai"})
        assert r.status_code in (200, 503)
        data = r.json()
        if r.status_code == 200:
            assert "items" in data
            assert "counts" in data
            assert isinstance(data["items"], list)
        # 503 = AI model not configured (acceptable)


class TestPromptsPutSearchAi:
    """RED: PUT /api/prompts should accept search_ai type."""

    def test_put_search_ai_custom_prompt(self, client):
        """PUT /api/prompts with type=search_ai saves custom prompt."""
        r = client.put("/api/prompts", json={"type": "search_ai", "custom": "自定义搜索逻辑"})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["ok"] is True

    def test_put_search_ai_reset(self, client):
        """PUT /api/prompts with type=search_ai and empty custom resets."""
        r = client.put("/api/prompts", json={"type": "search_ai", "custom": ""})
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert r.json()["ok"] is True

    def test_put_search_ai_reflected_in_get(self, client):
        """After saving search_ai custom, GET returns it."""
        custom = "测试自定义搜索"
        client.put("/api/prompts", json={"type": "search_ai", "custom": custom})
        r = client.get("/api/prompts")
        assert r.status_code == 200
        data = r.json()
        assert data["search_ai"]["custom"] == custom


# ── s4: AI 搜索前后端集成 ──

class TestTaskModelsSearchAi:
    """RED: GET /api/task-models includes search_ai binding status."""

    def test_task_models_includes_search_ai(self, client):
        """GET /api/task-models returns search_ai entry."""
        r = client.get("/api/task-models")
        assert r.status_code == 200
        data = r.json()
        assert "search_ai" in data, "task-models missing search_ai"
        # Default binding has empty provider/model
        assert "provider" in data["search_ai"]
        assert "model" in data["search_ai"]

    def test_task_models_search_ai_empty_by_default(self, client):
        """By default search_ai has empty provider and model."""
        r = client.get("/api/task-models")
        data = r.json()
        sa = data["search_ai"]
        assert sa["provider"] == "", "Default search_ai provider should be empty"
        assert sa["model"] == "", "Default search_ai model should be empty"
