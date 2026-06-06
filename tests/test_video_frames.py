"""Tests for quickmedia.ai — video multi-frame analysis."""

import os, tempfile, json
from quickmedia.ai import merge_frame_results


class TestFrameMerge:
    """Label merging and dedup across video frames."""

    def test_tags_merged_deduped(self):
        frames = [
            {"description": "首帧：暗色开场", "tags": ["暗色", "室内"], "ocr_text": ""},
            {"description": "中间：人物出现", "tags": ["人物", "对话"], "ocr_text": "Hello"},
            {"description": "尾帧：室外", "tags": ["室外", "人物"], "ocr_text": "Goodbye"},
        ]
        result = merge_frame_results(frames)
        assert result["description"] == "首帧：暗色开场"
        assert set(result["tags"]) == {"暗色", "室内", "人物", "对话", "室外"}
        assert "Hello" in result["ocr_text"]
        assert "Goodbye" in result["ocr_text"]

    def test_single_frame_passthrough(self):
        frames = [{"description": "单帧描述", "tags": ["A", "B"], "ocr_text": "text"}]
        result = merge_frame_results(frames)
        assert result["description"] == "单帧描述"
        assert result["tags"] == ["A", "B"]
        assert result["ocr_text"] == "text"

    def test_empty_frames_returns_empty(self):
        result = merge_frame_results([])
        assert result["description"] == ""
        assert result["tags"] == []
        assert result["ocr_text"] == ""

    def test_ocr_deduped(self):
        frames = [
            {"description": "", "tags": [], "ocr_text": "A, B, C"},
            {"description": "", "tags": [], "ocr_text": "B, C, D"},
        ]
        result = merge_frame_results(frames)
        # OCR text deduped
        ocr_parts = set(result["ocr_text"].split(", "))
        assert ocr_parts == {"A", "B", "C", "D"}


class TestFrameExtraction:
    """ffmpeg frame extraction from video files."""

    def test_extract_frames(self):
        from quickmedia.ai import extract_video_frames
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.mp4")
        # Create a 2-second test video
        os.system(
            f"ffmpeg -y -f lavfi -i color=c=blue:s=320x240:d=2 "
            f"-c:v libx264 -an {path} 2>/dev/null"
        )
        out_dir = tempfile.mkdtemp()
        frames = extract_video_frames(path, out_dir, num_frames=3)
        assert len(frames) == 3
        for f in frames:
            assert os.path.isfile(f)

    def test_extract_single_frame(self):
        from quickmedia.ai import extract_video_frames
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.mp4")
        os.system(
            f"ffmpeg -y -f lavfi -i color=c=red:s=160x120:d=1 "
            f"-c:v libx264 -an {path} 2>/dev/null"
        )
        out_dir = tempfile.mkdtemp()
        frames = extract_video_frames(path, out_dir, num_frames=1)
        assert len(frames) == 1
