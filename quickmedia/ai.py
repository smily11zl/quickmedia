"""AI analysis for QuickMedia using Ollama vision models.

Handles image description and tag generation via local multimodal models
like Qwen 3.5.
"""

import json
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
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.max_dimension = max_dimension

    def analyze(self, image_path: str) -> dict:
        """Analyze an image, returning {description, tags}."""
        try:
            img = self._prepare_image(image_path)
            img_b64 = self._encode_image(img)
            prompt = self._build_prompt()

            response = self._call_ollama(prompt, img_b64)
            return self._parse_response(response)
        except Exception:
            return {"description": "", "tags": []}

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
            "以逗号分隔的标签形式输出，标签使用中文。\n\n"
            "输出格式：\n"
            "描述：<描述文本>\n"
            "标签：<标签1>, <标签2>, <标签3>, ..."
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

        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")

    def _parse_response(self, text: str) -> dict:
        """Parse the model's response into {description, tags}."""
        desc = ""
        tags = []

        # Extract description
        desc_match = re.search(r"描述[：:]\s*(.+?)(?:\n|标签|$)", text)
        if desc_match:
            desc = desc_match.group(1).strip()

        # Extract tags
        tags_match = re.search(r"标签[：:]\s*(.+)", text)
        if tags_match:
            tags_str = tags_match.group(1).strip()
            tags = [
                t.strip().strip("<>")  # Remove angle brackets some models add
                for t in re.split(r"[，,、]", tags_str)
                if t.strip().strip("<>")
            ]

        return {"description": desc, "tags": tags}


class TextAnalyzer:
    """Analyze text documents using Ollama text models."""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen3.5:9b"):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    def analyze(self, text: str) -> dict:
        """Analyze text, returning {summary, tags}."""
        try:
            prompt = (
                "总结以下文档内容（200字以内），并提取5-10个主题关键词作为标签。\n"
                "关键词以逗号分隔，使用中文。\n\n"
                "输出格式：\n"
                "摘要：<摘要文本>\n"
                "标签：<标签1>, <标签2>, ...\n\n"
                f"文档内容：\n{text[:4000]}"  # truncate for model limits
            )
            response = self._call_ollama(prompt)
            return self._parse_response(response)
        except Exception:
            return {"summary": "", "tags": []}

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
        with urllib.request.urlopen(req, timeout=60) as resp:
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
