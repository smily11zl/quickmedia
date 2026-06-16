"""Tests for quickmedia.ai — Ollama vision analysis."""

import tempfile, os
from PIL import Image
from quickmedia.ai import VisionAnalyzer

def _make_test_image(text="test"):
    d = tempfile.mkdtemp()
    path = os.path.join(d, f"{text}.png")
    Image.new("RGB", (400, 300), color="salmon").save(path)
    return path

class TestPromptBuilding:
    def test_prompt_has_template(self):
        p = VisionAnalyzer()._build_prompt()
        assert "标签示例" in p and "description" in p
    def test_prompt_has_format_instructions(self):
        p = VisionAnalyzer()._build_prompt()
        assert "description" in p and "tags" in p

class TestResponseParsing:
    def test_parses_valid_json(self):
        r = VisionAnalyzer()._parse_response(
            '{"description": "室内场景", "tags": ["猫", "橘猫", "宠物"], "text": ""}'
        )
        assert r["description"] == "室内场景" and r["tags"] == ["猫", "橘猫", "宠物"] and r["ocr_text"] == ""

    def test_parses_json_in_markdown(self):
        r = VisionAnalyzer()._parse_response(
            '```json\n{"description": "风景", "tags": ["山", "湖"], "text": ""}\n```'
        )
        assert r["description"] == "风景" and r["tags"] == ["山", "湖"]

    def test_parses_json_with_extra_text(self):
        r = VisionAnalyzer()._parse_response(
            '这是一张图片的分析结果：\n{"description": "日落", "tags": ["夕阳", "海滩"], "text": "Hello"}'
        )
        assert r["description"] == "日落" and r["tags"] == ["夕阳", "海滩"]

    def test_non_json_returns_empty(self):
        r = VisionAnalyzer()._parse_response("描述：室内场景。\n标签：猫, 橘猫, 宠物")
        assert r["description"] == "" and r["tags"] == []

    def test_handles_invalid_json(self):
        r = VisionAnalyzer()._parse_response("{invalid json")
        assert r["description"] == "" and r["tags"] == []

    def test_handles_empty_response(self):
        r = VisionAnalyzer()._parse_response("")
        assert r["description"] == "" and r["tags"] == []

class TestJSONExtract:
    def test_extracts_json_from_markdown(self):
        j = VisionAnalyzer._extract_json('```json\n{"a": 1}\n```')
        assert j == '{"a": 1}'

    def test_extracts_json_from_text(self):
        j = VisionAnalyzer._extract_json('prefix {"a": 1} suffix')
        assert j == '{"a": 1}'

    def test_returns_none_for_no_json(self):
        assert VisionAnalyzer._extract_json("no json here") is None

class TestImagePreprocessing:
    def test_resize_large_image(self):
        a = VisionAnalyzer(max_dimension=512)
        p = _make_test_image()
        Image.new("RGB", (2000, 1500), color="blue").save(p)
        assert max(a._prepare_image(p).size) <= 512
    def test_small_image_unchanged(self):
        a = VisionAnalyzer(max_dimension=512)
        p = _make_test_image()
        assert a._prepare_image(p).size == (400, 300)

class TestOCRPrompt:
    def test_prompt_includes_ocr_instruction(self):
        p = VisionAnalyzer()._build_prompt()
        assert "text" in p

class TestOCRResponseParsing:
    def test_parses_ocr_text(self):
        r = VisionAnalyzer()._parse_response(
            '{"description": "警告截图", "tags": ["截图"], "text": "WARNING, Danger"}'
        )
        assert r["ocr_text"] == "WARNING, Danger"
    def test_parses_chinese_ocr(self):
        r = VisionAnalyzer()._parse_response(
            '{"description": "聊天", "tags": ["微信"], "text": "你好, 明天见"}'
        )
        assert "你好" in r["ocr_text"]
    def test_ocr_empty_when_no_text(self):
        r = VisionAnalyzer()._parse_response(
            '{"description": "风景照", "tags": ["自然"], "text": ""}'
        )
        assert r["ocr_text"] == ""


class TestTranscriptionAnalyzer:
    """Speech transcription via faster-whisper."""

    def _make_silent_audio(self):
        """Create a silent WAV file for testing no-audio scenario."""
        import subprocess
        d = tempfile.mkdtemp()
        path = os.path.join(d, "silent.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
             "-t", "1", path],
            capture_output=True, timeout=5,
        )
        return path

    def test_transcribe_silent_audio(self):
        """Silent audio returns empty string."""
        from quickmedia.ai import TranscriptionAnalyzer
        a = TranscriptionAnalyzer(model_size="tiny", device="cpu")
        result = a.transcribe(self._make_silent_audio())
        assert result == ""


class TestMergeFrameResults:
    def test_merges_tags_across_frames(self):
        from quickmedia.ai import merge_frame_results
        frames = [
            {"description": "frame 1", "tags": ["a", "b"], "ocr_text": "hello"},
            {"description": "frame 2", "tags": ["b", "c"], "ocr_text": "world"},
        ]
        result = merge_frame_results(frames)
        assert result["description"] == "frame 1"
        assert result["tags"] == ["a", "b", "c"]
        assert "hello" in result["ocr_text"] and "world" in result["ocr_text"]

    def test_empty_frames(self):
        from quickmedia.ai import merge_frame_results
        result = merge_frame_results([])
        assert result["description"] == "" and result["tags"] == []


class TestPromptConfigIntegration:
    """Analyzers use PromptConfig instead of hardcoded prompts."""

    def test_vision_uses_prompt_config(self):
        """VisionAnalyzer reads prompt from PromptConfig."""
        import tempfile
        from quickmedia.prompt_config import PromptConfig
        from quickmedia.ai import VisionAnalyzer

        d = tempfile.mkdtemp()
        pc = PromptConfig(d)
        pc.update_custom("vision", "测试用自定义prompt：分析构图")

        analyzer = VisionAnalyzer(prompt_config=pc)
        prompt = analyzer._build_prompt()
        assert "测试用自定义prompt" in prompt
        assert "请严格按以下JSON格式输出" in prompt  # system_format appended

    def test_text_uses_prompt_config(self):
        """TextAnalyzer reads prompt from PromptConfig."""
        import tempfile
        from quickmedia.prompt_config import PromptConfig
        from quickmedia.ai import TextAnalyzer

        d = tempfile.mkdtemp()
        pc = PromptConfig(d)
        pc.update_custom("text", "测试用自定义文档prompt")

        analyzer = TextAnalyzer(prompt_config=pc)
        # Mock _call_ollama to avoid real API call
        analyzer._call_ollama = lambda p: '{"summary": "测试摘要", "tags": ["测试", "标签"]}'
        result = analyzer.analyze("test content")
        assert result["summary"] == "测试摘要"
        assert "测试" in result["tags"]

    def test_speech_uses_prompt_config(self):
        """TextAnalyzer.analyze_speech reads from PromptConfig."""
        import tempfile
        from quickmedia.prompt_config import PromptConfig
        from quickmedia.ai import TextAnalyzer

        d = tempfile.mkdtemp()
        pc = PromptConfig(d)
        pc.update_custom("speech", "测试用自定义语音prompt")

        analyzer = TextAnalyzer(prompt_config=pc)
        analyzer._call_ollama = lambda p: '{"summary": "语音摘要", "tags": ["语音", "测试"]}'
        result = analyzer.analyze_speech("test transcript")
        assert result["summary"] == "语音摘要"
        assert "语音" in result["tags"]
