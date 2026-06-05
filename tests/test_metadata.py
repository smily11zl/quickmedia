"""Tests for quickmedia.metadata — EXIF and media metadata extraction."""

import os
import tempfile
from quickmedia.metadata import MetadataExtractor


class TestImageMetadata:
    """Extracting metadata from image files."""

    def test_png_dimensions(self):
        from PIL import Image
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.png")
        img = Image.new("RGB", (800, 600), color="red")
        img.save(path)

        extractor = MetadataExtractor()
        meta = extractor.extract(path)
        assert meta["width"] == 800
        assert meta["height"] == 600

    def test_jpg_dimensions(self):
        from PIL import Image
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.jpg")
        img = Image.new("RGB", (400, 300), color="blue")
        img.save(path)

        extractor = MetadataExtractor()
        meta = extractor.extract(path)
        assert meta["width"] == 400
        assert meta["height"] == 300


class TestVideoMetadata:
    """Extracting metadata from video files."""

    def test_mp4_resolution_and_duration(self):
        """ffprobe extracts width, height, duration from mp4."""
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.mp4")
        # Create a 640x480 1-second test video
        os.system(
            f"ffmpeg -y -f lavfi -i color=c=green:s=640x480:d=1 "
            f"-c:v libx264 -an {path} 2>/dev/null"
        )

        extractor = MetadataExtractor()
        meta = extractor.extract(path)
        assert meta["width"] == 640
        assert meta["height"] == 480
        assert 0.5 < meta["duration"] < 1.5  # ~1 second

    def test_audio_extraction(self):
        """ffprobe extracts duration from wav."""
        d = tempfile.mkdtemp()
        path = os.path.join(d, "test.wav")
        os.system(
            f"ffmpeg -y -f lavfi -i sine=frequency=440:duration=2 "
            f"-c:a pcm_s16le {path} 2>/dev/null"
        )

        extractor = MetadataExtractor()
        meta = extractor.extract(path)
        assert 1.5 < meta["duration"] < 2.5


class TestUnsupportedFiles:
    """Graceful handling of files without metadata."""

    def test_text_file_returns_empty(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "notes.md")
        with open(path, "w") as f:
            f.write("hello")

        extractor = MetadataExtractor()
        meta = extractor.extract(path)
        # Should return dict with default/empty values, not crash
        assert isinstance(meta, dict)
        assert "width" in meta
