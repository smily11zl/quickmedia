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
    def test_prompt_asks_for_chinese(self):
        p = VisionAnalyzer()._build_prompt()
        assert "描述" in p and "标签" in p and "中文" in p
    def test_prompt_has_format_instructions(self):
        p = VisionAnalyzer()._build_prompt()
        assert "描述：" in p and "标签：" in p

class TestResponseParsing:
    def test_parses_standard_format(self):
        r = VisionAnalyzer()._parse_response("描述：室内场景。\n标签：猫, 橘猫, 宠物")
        assert r["description"] == "室内场景。" and "猫" in r["tags"] and len(r["tags"]) == 3
    def test_parses_tags_only(self):
        r = VisionAnalyzer()._parse_response("标签：猫, 宠物")
        assert "猫" in r["tags"] and len(r["tags"]) == 2
    def test_parses_description_only(self):
        r = VisionAnalyzer()._parse_response("描述：一张风景照片。")
        assert r["description"] == "一张风景照片。" and r["tags"] == []
    def test_handles_empty_response(self):
        r = VisionAnalyzer()._parse_response("")
        assert r["description"] == "" and r["tags"] == []

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
        assert "文字" in p
    def test_prompt_has_ocr_format(self):
        p = VisionAnalyzer()._build_prompt()
        assert "文字：" in p

class TestOCRResponseParsing:
    def test_parses_ocr_text(self):
        r = VisionAnalyzer()._parse_response("描述：警告截图。\n标签：截图\n文字：WARNING, Danger")
        assert r["ocr_text"] == "WARNING, Danger"
    def test_parses_chinese_ocr(self):
        r = VisionAnalyzer()._parse_response("描述：聊天。\n标签：微信\n文字：你好, 明天见")
        assert "你好" in r["ocr_text"]
    def test_ocr_empty_when_no_text(self):
        r = VisionAnalyzer()._parse_response("描述：风景照。\n标签：自然")
        assert r["ocr_text"] == ""
    def test_ocr_handles_colon_variants(self):
        r = VisionAnalyzer()._parse_response("文字:Hello World")
        assert r["ocr_text"] == "Hello World"


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

    def test_transcribe_returns_text(self):
        """TranscriptionAnalyzer transcribes audio to text."""
        from quickmedia.ai import TranscriptionAnalyzer
        analyzer = TranscriptionAnalyzer()
        assert hasattr(analyzer, "transcribe")
        assert callable(analyzer.transcribe)

    def test_no_audio_returns_empty(self):
        """Silent audio returns empty transcript, no error."""
        from quickmedia.ai import TranscriptionAnalyzer
        analyzer = TranscriptionAnalyzer()
        path = self._make_silent_audio()
        assert os.path.isfile(path)


class TestSpeechAnalysis:
    """TextAnalyzer.analyze_speech for transcribed audio."""

    def test_speech_method_exists(self):
        """TextAnalyzer has analyze_speech method."""
        from quickmedia.ai import TextAnalyzer
        a = TextAnalyzer()
        assert hasattr(a, "analyze_speech")
        assert callable(a.analyze_speech)

    def test_speech_parse_returns_summary_and_tags(self):
        """Speech analysis returns {summary, tags} format."""
        from quickmedia.ai import TextAnalyzer
        a = TextAnalyzer()
        a._call_ollama = lambda p: "摘要：讨论了预算和计划。\n标签：会议, 预算, 计划"
        result = a.analyze_speech("今天我们讨论预算审批")
        assert result["summary"] == "讨论了预算和计划。"
        assert "会议" in result["tags"]
