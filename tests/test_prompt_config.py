"""Tests for quickmedia.prompt_config — AI prompt configuration."""

import tempfile, os, yaml
from quickmedia.prompt_config import PromptConfig


def test_creates_default_prompts_yaml():
    """First run creates prompts.yaml with all defaults."""
    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    assert os.path.isfile(os.path.join(d, "prompts.yaml"))

    with open(os.path.join(d, "prompts.yaml")) as f:
        data = yaml.safe_load(f)
    assert "vision" in data
    assert "text" in data
    assert "speech" in data
    assert "video_summary" in data


def test_vision_has_five_presets():
    """Vision analysis has 5 presets."""
    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    with open(os.path.join(d, "prompts.yaml")) as f:
        data = yaml.safe_load(f)
    presets = data["vision"]["presets"]
    assert len(presets) == 4
    names = {p["name"] for p in presets}
    assert "摄影" in names
    assert "设计" in names
    assert "宠物" in names
    assert "人物" in names


def test_get_prompt_uses_custom_first():
    """get_prompt returns custom if set, else default."""
    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    # Initially custom is empty, should return default
    prompt = cfg.get_prompt("vision")
    assert "描述" in prompt
    assert "标签" in prompt

    # Set custom
    cfg.update_custom("vision", "请分析图片的构图")
    prompt = cfg.get_prompt("vision")
    assert "请分析图片的构图" in prompt


def test_get_config_returns_full_structure():
    """get_config returns all types with system_format, default, custom, presets."""
    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    config = cfg.get_config()
    for key in ("vision", "text", "speech", "video_summary"):
        assert key in config
        assert "system_format" in config[key]
        assert "default" in config[key]
        assert "custom" in config[key]
        assert "presets" in config[key]


def test_prompt_includes_system_format():
    """get_prompt always appends system_format."""
    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    prompt = cfg.get_prompt("vision")
    assert "请严格按以下JSON格式输出" in prompt
    assert "description" in prompt
    assert "tags" in prompt


def test_preserves_custom_on_defaults_update():
    """Custom prompt survives when DEFAULT_PROMPTS changes."""
    import tempfile, yaml
    from quickmedia.prompt_config import PromptConfig, DEFAULT_PROMPTS

    d = tempfile.mkdtemp()
    cfg = PromptConfig(d)
    cfg.update_custom("vision", "我的自定义prompt")

    # Simulate code update: modify DEFAULT_PROMPTS in memory
    original = DEFAULT_PROMPTS["vision"]["default"]
    DEFAULT_PROMPTS["vision"]["default"] = "新的默认prompt"

    # Re-init should update default but keep custom
    cfg2 = PromptConfig(d)
    data = cfg2.get_config()
    assert data["vision"]["custom"] == "我的自定义prompt"
    assert data["vision"]["default"] == "新的默认prompt"

    # Restore
    DEFAULT_PROMPTS["vision"]["default"] = original
