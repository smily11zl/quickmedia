"""Metadata extraction for media files.

Uses Pillow for images and ffprobe for video/audio.
"""

import json
import os
import subprocess
from PIL import Image, UnidentifiedImageError


class MetadataExtractor:
    """Extract width, height, duration, and other metadata from media files."""

    def extract(self, filepath: str) -> dict:
        """Extract metadata from a file. Returns dict with at minimum:
        width, height, duration, has_metadata.
        """
        if not os.path.isfile(filepath):
            return self._empty()

        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        # Try image first
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            return self._extract_image(filepath)

        # Try video/audio with ffprobe
        if ext in {".mp4", ".mov", ".avi", ".mp3", ".wav", ".m4a"}:
            return self._extract_ffprobe(filepath)

        return self._empty()

    def _empty(self) -> dict:
        return {"width": None, "height": None, "duration": None}

    def _extract_image(self, filepath: str) -> dict:
        """Extract dimensions from an image file."""
        try:
            with Image.open(filepath) as img:
                w, h = img.size
                return {"width": w, "height": h, "duration": None}
        except (UnidentifiedImageError, OSError):
            return self._empty()

    def _extract_ffprobe(self, filepath: str) -> dict:
        """Extract metadata from video/audio using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    filepath,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return self._empty()

            data = json.loads(result.stdout)
            return self._parse_ffprobe(data)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return self._empty()

    def _parse_ffprobe(self, data: dict) -> dict:
        """Parse ffprobe JSON output into width/height/duration."""
        width = None
        height = None
        duration = None

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width") or width
                height = stream.get("height") or height

        # Duration from format section
        fmt = data.get("format", {})
        if fmt.get("duration"):
            try:
                duration = float(fmt["duration"])
            except (ValueError, TypeError):
                pass

        return {"width": width, "height": height, "duration": duration}
