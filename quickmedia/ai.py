"""AI analysis for QuickMedia using Ollama vision models.

Handles image description and tag generation via local multimodal models
like Qwen 3.5.
"""

import json
import os
import base64
import io
import re
import urllib.request
from PIL import Image


class VisionAnalyzer:
    """Analyze images using Ollama vision models."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen3.5:9b",
        max_dimension: int = 672,
        timeout: int = 300,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.max_dimension = max_dimension
        self.timeout = timeout

    def analyze(self, image_path: str) -> dict:
        """Analyze an image, returning {description, tags}."""
        img = self._prepare_image(image_path)
        img_b64 = self._encode_image(img)
        prompt = self._build_prompt()
        response = self._call_ollama(prompt, img_b64)
        return self._parse_response(response)

    def _prepare_image(self, image_path: str) -> Image.Image:
        """Load and optionally resize an image for the model."""
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        if max(w, h) > self.max_dimension:
            scale = self.max_dimension / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        return img

    def _encode_image(self, img: Image.Image) -> str:
        """Encode PIL Image to base64 string."""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _build_prompt(self) -> str:
        return (
            "请描述这张图片的场景、整体风格和色调（50字以内）。"
            "然后列出图片中出现的具体元素（人物、动物、物体、建筑、文字等），"
            "以逗号分隔的标签形式输出，标签使用中文。"
            "如果图片中有文字，请识别并以逗号分隔输出。\n\n"
            "输出格式：\n"
            "描述：<描述文本>\n"
            "标签：<标签1>, <标签2>, <标签3>, ...\n"
            "文字：<文字1>, <文字2>, ..."
        )

    def _call_ollama(self, prompt: str, image_b64: str) -> str:
        """Send a request to Ollama's chat API and return the text response."""
        url = f"{self.ollama_url}/api/chat"
        body = json.dumps({
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }],
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")

    def _parse_response(self, text: str) -> dict:
        """Parse the model's response into {description, tags, ocr_text}."""
        desc = ""
        tags = []
        ocr_text = ""

        desc_match = re.search(r"描述[：:]\s*(.+?)(?:\n|标签|$)", text)
        if desc_match:
            desc = desc_match.group(1).strip()

        tags_match = re.search(r"标签[：:]\s*(.+)", text)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            tags = [
                t.strip().strip("<>")
                for t in re.split(r"[，,、]", tags_str)
                if t.strip().strip("<>")
            ]

        ocr_match = re.search(r"文字[：:]\s*(.+)", text)
        if ocr_match:
            ocr_text = ocr_match.group(1).strip()

        return {"description": desc, "tags": tags, "ocr_text": ocr_text}


class TextAnalyzer:
    """Analyze text documents using Ollama text models."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen3.5:9b", timeout: int = 300):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def analyze(self, text: str) -> dict:
        """Analyze text, returning {summary, tags}."""
        prompt = (
            "总结以下文档内容（200字以内），并提取5-10个主题关键词作为标签。\n"
            "关键词以逗号分隔，使用中文。\n\n"
            "输出格式：\n"
            "摘要：<摘要文本>\n"
            "标签：<标签1>, <标签2>, ...\n\n"
            f"文档内容：\n{text[:4000]}"
        )
        response = self._call_ollama(prompt)
        return self._parse_response(response)

    def _call_ollama(self, prompt: str) -> str:
        import json, urllib.request
        url = f"{self.ollama_url}/api/chat"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")

    def _parse_response(self, text: str) -> dict:
        summary = ""
        tags = []
        m = re.search(r"摘要[：:]\s*(.+?)(?:\n|标签|$)", text)
        if m:
            summary = m.group(1).strip()
        m = re.search(r"标签[：:]\s*(.+)", text)
        if m:
            tags = [t.strip().strip("<>") for t in re.split(r"[，,、]", m.group(1)) if t.strip().strip("<>")]
        return {"summary": summary, "tags": tags}


def merge_frame_results(frames: list[dict]) -> dict:
    """Merge results from multiple video frames into one.

    - description: uses the first frame's description
    - tags: deduplicated union of all frames' tags
    - ocr_text: deduplicated union of all frames' OCR text
    """
    if not frames:
        return {"description": "", "tags": [], "ocr_text": ""}

    all_tags = []
    all_ocr_parts = []
    first_desc = ""

    for i, f in enumerate(frames):
        if i == 0:
            first_desc = f.get("description", "")
        all_tags.extend(f.get("tags", []))
        ocr = f.get("ocr_text", "")
        if ocr:
            all_ocr_parts.extend(p.strip() for p in ocr.split(",") if p.strip())

    # Deduplicate while preserving order
    seen_tags = set()
    tags = []
    for t in all_tags:
        if t not in seen_tags:
            seen_tags.add(t)
            tags.append(t)

    seen_ocr = set()
    ocr_parts = []
    for p in all_ocr_parts:
        if p not in seen_ocr:
            seen_ocr.add(p)
            ocr_parts.append(p)

    return {
        "description": first_desc,
        "tags": tags,
        "ocr_text": ", ".join(ocr_parts),
    }


def extract_video_frames(
    video_path: str, output_dir: str, num_frames: int = 5
) -> list[str]:
    """Extract uniformly distributed frames from a video.

    Returns list of paths to extracted JPEG frames.
    """
    import subprocess, json

    # Get video duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", video_path],
        capture_output=True, text=True, timeout=10,
    )
    if probe.returncode != 0:
        return []

    info = json.loads(probe.stdout)
    duration = float(info.get("format", {}).get("duration", 0))
    if duration <= 0:
        return []

    frame_paths = []
    os.makedirs(output_dir, exist_ok=True)

    for i in range(num_frames):
        t = duration * (i + 1) / (num_frames + 1)
        out_path = os.path.join(output_dir, f"frame_{i+1:02d}.jpg")
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(t), "-i", video_path,
             "-vframes", "1", "-q:v", "2", out_path],
            capture_output=True, timeout=15,
        )
        if os.path.isfile(out_path):
            frame_paths.append(out_path)

    return frame_paths
