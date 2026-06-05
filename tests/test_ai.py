"""Tests for quickmedia.ai — Ollama vision analysis."""

import tempfile
import os
from PIL import Image
from quickmedia.ai import VisionAnalyzer


def _make_test_image(text: str = "test") -> str:
    """Create a simple test image and return its path."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, f"{text}.png")
    img = Image.new("RGB", (400, 300), color="salmon")
    img.save(path)
    return path


class TestPromptBuilding:
    """Prompt construction for vision analysis."""

    def test_prompt_asks_for_chinese(self):
        analyzer = VisionAnalyzer()
        prompt = analyzer._build_prompt()
        assert "描述" in prompt
        assert "标签" in prompt
        assert "中文" in prompt

    def test_prompt_has_format_instructions(self):
        analyzer = VisionAnalyzer()
        prompt = analyzer._build_prompt()
        assert "描述：" in prompt
        assert "标签：" in prompt


class TestResponseParsing:
    """Parsing Ollama vision model responses."""

    def test_parses_standard_format(self):
        analyzer = VisionAnalyzer()
        response = "描述：室内场景，暖色调。一只橘猫趴在窗台上。\n标签：猫, 橘猫, 宠物, 窗台, 室内"
        result = analyzer._parse_response(response)
        assert result["description"] == "室内场景，暖色调。一只橘猫趴在窗台上。"
        assert "猫" in result["tags"]
        assert "宠物" in result["tags"]
        assert len(result["tags"]) == 5

    def test_parses_tags_only(self):
        analyzer = VisionAnalyzer()
        response = "标签：猫, 宠物, 室内"
        result = analyzer._parse_response(response)
        assert "猫" in result["tags"]
        assert len(result["tags"]) == 3

    def test_parses_description_only(self):
        analyzer = VisionAnalyzer()
        response = "描述：一张风景照片。"
        result = analyzer._parse_response(response)
        assert result["description"] == "一张风景照片。"
        assert result["tags"] == []

    def test_handles_empty_response(self):
        analyzer = VisionAnalyzer()
        result = analyzer._parse_response("")
        assert result["description"] == ""
        assert result["tags"] == []


class TestImagePreprocessing:
    """Image resize before sending to model."""

    def test_resize_large_image(self):
        analyzer = VisionAnalyzer(max_dimension=512)
        path = _make_test_image()
        # Create a large image
        img = Image.new("RGB", (2000, 1500), color="blue")
        img.save(path)
        resized = analyzer._prepare_image(path)
        assert max(resized.size) <= 512

    def test_small_image_unchanged(self):
        analyzer = VisionAnalyzer(max_dimension=512)
        path = _make_test_image()
        # 400x300 is already small
        resized = analyzer._prepare_image(path)
        assert resized.size[0] == 400
        assert resized.size[1] == 300
