"""Tests for QuickMedia V16 — Aggregation Prompt Customization."""
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


# ── s1: DEFAULT_PROMPTS 加 4 个聚合条目 + PUT validator ──

class TestDefaultPromptsAggregation:
    """RED: DEFAULT_PROMPTS must include 4 aggregation entries."""

    AGG_TYPES = [
        "aggregation_full",
        "aggregation_full_append",
        "aggregation_append",
        "aggregation_analyze_append",
    ]

    def test_aggregation_types_in_default_prompts(self):
        """DEFAULT_PROMPTS contains all 4 aggregation types."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        for t in self.AGG_TYPES:
            assert t in DEFAULT_PROMPTS, f"DEFAULT_PROMPTS missing {t}"

    def test_aggregation_types_have_required_structure(self):
        """Each aggregation type has system_format, default, custom, presets."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        for t in self.AGG_TYPES:
            sa = DEFAULT_PROMPTS[t]
            assert "system_format" in sa, f"{t} missing system_format"
            assert "default" in sa, f"{t} missing default"
            assert "custom" in sa, f"{t} missing custom"
            assert "presets" in sa, f"{t} missing presets"

    def test_aggregation_system_format_requires_json(self):
        """Each aggregation system_format requires JSON output."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        for t in self.AGG_TYPES:
            fmt = str(DEFAULT_PROMPTS[t]["system_format"])
            assert "JSON" in fmt, f"{t} system_format missing JSON"

    def test_aggregation_full_has_assets_placeholder(self):
        """aggregation_full default contains {assets} placeholder."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        default = str(DEFAULT_PROMPTS["aggregation_full"]["default"])
        assert "{assets}" in default

    def test_aggregation_full_append_has_placeholders(self):
        """aggregation_full_append has {nodes} and {assets}."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        default = str(DEFAULT_PROMPTS["aggregation_full_append"]["default"])
        assert "{nodes}" in default
        assert "{assets}" in default

    def test_aggregation_analyze_append_has_placeholders(self):
        """aggregation_analyze_append has node placeholders."""
        from quickmedia.prompt_config import DEFAULT_PROMPTS
        default = str(DEFAULT_PROMPTS["aggregation_analyze_append"]["default"])
        assert "{node_name}" in default
        assert "{node_description}" in default
        assert "{existing_assets}" in default
        assert "{candidates}" in default


class TestApiPromptsAggregation:
    """RED: PUT /api/prompts accepts aggregation types."""

    def test_put_aggregation_full(self, client):
        """PUT with type=aggregation_full saves custom prompt."""
        r = client.put("/api/prompts", json={"type": "aggregation_full", "custom": "自定义聚合逻辑"})
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_put_aggregation_full_append(self, client):
        """PUT with type=aggregation_full_append succeeds."""
        r = client.put("/api/prompts", json={"type": "aggregation_full_append", "custom": ""})
        assert r.status_code == 200

    def test_put_aggregation_append(self, client):
        """PUT with type=aggregation_append succeeds."""
        r = client.put("/api/prompts", json={"type": "aggregation_append", "custom": ""})
        assert r.status_code == 200

    def test_put_aggregation_analyze_append(self, client):
        """PUT with type=aggregation_analyze_append succeeds."""
        r = client.put("/api/prompts", json={"type": "aggregation_analyze_append", "custom": ""})
        assert r.status_code == 200

    def test_get_includes_aggregation_types(self, client):
        """GET /api/prompts returns all 4 aggregation types."""
        r = client.get("/api/prompts")
        assert r.status_code == 200
        data = r.json()
        for t in TestDefaultPromptsAggregation.AGG_TYPES:
            assert t in data, f"GET /api/prompts missing {t}"


# ── s2: DEFAULT_CONFIG 加 aggregation task_model ──

class TestDefaultConfigAggregation:
    """RED: DEFAULT_CONFIG.task_models must include aggregation."""

    def test_aggregation_in_default_task_models(self):
        """DEFAULT_CONFIG.task_models contains aggregation."""
        from quickmedia.config import DEFAULT_CONFIG
        tm = DEFAULT_CONFIG.get("task_models") or {}
        assert "aggregation" in tm, "DEFAULT_CONFIG.task_models missing aggregation"

    def test_fill_missing_adds_aggregation(self):
        """_fill_missing_task_models copies aggregation from DEFAULT_CONFIG."""
        d = tempfile.mkdtemp()
        cfg = Config(config_dir=d)
        tm = cfg.get("task_models") or {}
        assert "aggregation" in tm, "_fill_missing_task_models did not add aggregation"

    def test_aggregation_empty_by_default(self):
        """By default aggregation has empty provider and model."""
        d = tempfile.mkdtemp()
        cfg = Config(config_dir=d)
        tm = cfg.get("task_models") or {}
        sa = tm["aggregation"]
        assert sa["provider"] == ""
        assert sa["model"] == ""


class TestTaskModelsApiAggregation:
    """RED: GET /api/task-models returns aggregation."""

    def test_task_models_includes_aggregation(self, client):
        """GET /api/task-models returns aggregation entry."""
        r = client.get("/api/task-models")
        assert r.status_code == 200
        data = r.json()
        assert "aggregation" in data, "task-models missing aggregation"
        assert "provider" in data["aggregation"]
        assert "model" in data["aggregation"]


# ── s3: aggregation/prompts.py 改为 PromptConfig 读取 ──

class TestAggregationPromptsFromConfig:
    """Verify aggregation prompts use PromptConfig templates."""

    def test_build_full_uses_prompt_config(self):
        """build_prompt('full') generates assets with [id] format."""
        from quickmedia.aggregation.prompts import build_prompt
        assets = [{"id": 1, "filename": "test.jpg", "asset_type": "image",
                    "video_summary": "", "visual_description": "desc", "ai_summary": "",
                    "tags": [{"name": "t1"}]}]
        prompt = build_prompt("full", assets)
        assert "[1]" in prompt
        assert "素材列表" in prompt

    def test_build_full_append_uses_template(self):
        """build_prompt('full_append') replaces {nodes} placeholder."""
        from quickmedia.aggregation.prompts import build_prompt
        assets = [{"id": 1, "filename": "a.jpg", "asset_type": "image",
                    "video_summary": "", "visual_description": "d", "ai_summary": "",
                    "tags": [{"name": "x"}]}]
        nodes = [{"id": 5, "name": "节点A", "description": "desc", "asset_ids": [1]}]
        prompt = build_prompt("full_append", assets, nodes)
        assert "节点A" in prompt
        assert "[1]" in prompt

    def test_build_append_uses_template(self):
        """build_prompt('append') replaces {nodes} placeholder."""
        from quickmedia.aggregation.prompts import build_prompt
        assets = [{"id": 1, "filename": "a.jpg", "asset_type": "image",
                    "video_summary": "", "visual_description": "d", "ai_summary": "",
                    "tags": [{"name": "x"}]}]
        nodes = [{"id": 2, "name": "N2", "description": "", "asset_ids": []}]
        prompt = build_prompt("append", assets, nodes)
        assert "N2" in prompt
        assert "[1]" in prompt

    def test_build_analyze_append_uses_template(self):
        """build_append_prompt includes node_name and candidates with IDs."""
        from quickmedia.aggregation.prompts import build_append_prompt
        node_info = {"name": "宠物", "description": "宠物相关"}
        existing = [{"id": 3, "filename": "cat.jpg", "ai_summary": "猫", "visual_description": "", "video_summary": ""}]
        candidates = [{"id": 5, "filename": "dog.jpg", "asset_type": "image",
                        "ai_summary": "狗", "visual_description": "", "video_summary": ""}]
        prompt = build_append_prompt(node_info, existing, candidates)
        assert "宠物" in prompt
        assert "[5]" in prompt
        assert "[3]" in prompt


# ── s4: aggregation/core.py 改为 task_models.aggregation ──

class TestAggregationTaskBinding:
    """RED: Aggregation uses task_models.aggregation instead of text."""

    def test_aggregation_adapter_uses_aggregation_binding(self):
        """_get_adapter uses 'aggregation' binding, not 'text'."""
        from quickmedia.aggregation import core
        import inspect
        src = inspect.getsource(core._get_adapter)
        assert 'get_task_binding("aggregation")' in src, \
            "_get_adapter should use aggregation binding"
        assert 'get_task_binding("text")' not in src, \
            "_get_adapter should NOT use text binding"


# ── s5: SettingsModal 三组布局 + ModelManager ──

class TestPromptGroupsLayout:
    """RED: SettingsModal prompts tab should have 3 groups."""

    def test_prompt_groups_mapping(self):
        """Groups map types correctly."""
        groups = {
            "分析": ["vision", "text", "speech", "video_vision", "video_summary"],
            "聚合": ["aggregation_full", "aggregation_full_append", "aggregation_append", "aggregation_analyze_append"],
            "搜索": ["search_ai"],
        }
        assert len(groups["分析"]) == 5
        assert len(groups["聚合"]) == 4
        assert len(groups["搜索"]) == 1
        assert "aggregation_full" in groups["聚合"]

    def test_placeholder_hints_mapping(self):
        """Each aggregation type has placeholder hints."""
        hints = {
            "aggregation_full": "{assets} 素材列表",
            "aggregation_full_append": "{assets} 素材列表, {nodes} 已有节点",
            "aggregation_append": "{assets} 素材列表, {nodes} 已有节点",
            "aggregation_analyze_append": "{node_name} 节点名, {node_description} 节点描述, {existing_assets} 已有素材摘要, {candidates} 候选素材",
            "search_ai": "{assets} 素材列表, {query} 搜索查询",
        }
        for k in hints:
            assert len(hints[k]) > 0, f"Missing hint for {k}"


class TestModelManagerAggregation:
    """RED: ModelManager TASK_LABELS includes aggregation."""

    def test_task_labels_has_aggregation(self):
        """TASK_LABELS has aggregation entry."""
        labels = {
            "aggregation": "聚合分析",
        }
        assert "aggregation" in labels
        assert labels["aggregation"] == "聚合分析"
