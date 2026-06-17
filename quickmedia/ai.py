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


class OllamaAdapter:
    """Adapter for Ollama's native /api/chat API with image support."""

    def __init__(self, base_url: str, model: str, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, prompt: str, images: list[str] = None) -> str:
        """Send to Ollama /api/chat. Returns text content."""
        import json as _json, urllib.request as _req
        body = _json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt, "images": images or []}],
            "stream": False,
            "think": True,
        }).encode("utf-8")
        url = f"{self.base_url}/api/chat"
        r = _req.Request(url, data=body)
        r.add_header("Content-Type", "application/json")
        print(f"[Ollama] model={self.model}", flush=True)
        print(f"[Ollama prompt] {prompt}", flush=True)
        with _req.urlopen(r, timeout=self.timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
            content = data.get("message", {}).get("content", "")
            print(f"[Ollama] {content}", flush=True)
            return content


class VisionAnalyzer:
    """Analyze images using AI vision models."""

    def __init__(
        self,
        adapter=None,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen3.5:9b",
        max_dimension: int = 672,
        timeout: int = 300,
        prompt_config = None,
    ):
        self.adapter = adapter or OllamaAdapter(ollama_url, model, timeout)
        self.max_dimension = max_dimension
        self._prompt_config = prompt_config

    def analyze(self, image_path: str) -> dict:
        """Analyze an image, returning {description, tags}."""
        img = self._prepare_image(image_path)
        img_b64 = self._encode_image(img)
        prompt = self._build_prompt()
        response = self.adapter.chat(prompt, [img_b64])
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
        if self._prompt_config:
            return self._prompt_config.get_prompt("vision")
        return (
            "请描述这张图片的场景、整体风格和色调（50字以内）。"
            "然后列出图片中出现的具体人物、动物、物体、建筑、文字等关键元素。\n\n"
            "标签示例：\n"
            "标签1\n"
            "标签2\n"
            "标签3\n\n"
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"description": "图片描述", "tags": ["标签1", "标签2", "标签3"], "text": "文字内容"}\n'
            "如果没有识别到文字，text 为空字符串。"
        )

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON object from LLM output that may contain markdown or extra text."""
        # Strip <think>...</think> blocks (MiniMax, DeepSeek-R1, etc.)
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Try ```json ... ``` block first
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        # Try to find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end + 1]
        return None

    @staticmethod
    def _parse_json_response(text: str) -> dict | None:
        """Try to parse LLM output as JSON. Returns None if parsing fails."""
        json_str = VisionAnalyzer._extract_json(text)
        if json_str is None:
            return None
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and "description" in data:
                return {
                    "description": str(data.get("description", "")),
                    "tags": data.get("tags", []) if isinstance(data.get("tags"), list) else [],
                    "ocr_text": str(data.get("text", "")),
                }
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return None

    def _parse_response(self, text: str) -> dict:
        """Parse the model's JSON response into {description, tags, ocr_text}."""
        result = self._parse_json_response(text)
        if result is not None:
            return result
        return {"description": "", "tags": [], "ocr_text": ""}


class TextAnalyzer:
    """Analyze text documents using AI text models."""

    def __init__(self, adapter=None, ollama_url: str = "http://localhost:11434", model: str = "qwen3.5:9b", timeout: int = 300, prompt_config = None):
        self.adapter = adapter or OllamaAdapter(ollama_url, model, timeout)
        self._prompt_config = prompt_config

    def analyze(self, text: str) -> dict:
        """Analyze text, returning {summary, tags}."""
        if self._prompt_config:
            prompt = self._prompt_config.get_prompt("text") + f"\n\n文档内容：\n{text[:4000]}"
        else:
            prompt = (
                "总结以下文档内容（200字以内），并提取5-10个主题关键词。\n\n"
                "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
                '{"summary": "文档摘要", "tags": ["标签1", "标签2", "标签3"]}\n'
                "如果没有标签，tags 为空数组。\n\n"
                f"文档内容：\n{text[:4000]}"
            )
        response = self.adapter.chat(prompt)
        return self._parse_response(response)

    @staticmethod
    def _parse_response(text: str) -> dict:
        """Parse text/speech JSON output into {summary, tags}."""
        from quickmedia.ai import VisionAnalyzer
        json_str = VisionAnalyzer._extract_json(text)
        if json_str:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and "summary" in data:
                    return {
                        "summary": str(data.get("summary", "")),
                        "tags": data.get("tags", []) if isinstance(data.get("tags"), list) else [],
                    }
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return {"summary": "", "tags": []}

    def analyze_speech(self, transcript: str) -> dict:
        """Analyze a speech transcript, returning {summary, tags}."""
        if self._prompt_config:
            prompt = self._prompt_config.get_prompt("speech") + f"\n\n语音转录：\n{transcript[:4000]}"
        else:
            prompt = (
                "以下是一段语音转录文本。请总结这段语音的主要内容（150字以内），"
                "并提取5-10个主题关键词。\n\n"
                "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
                '{"summary": "语音摘要", "tags": ["标签1", "标签2", "标签3"]}\n'
                "如果没有标签，tags 为空数组。\n\n"
                f"语音转录：\n{transcript[:4000]}"
            )
        response = self.adapter.chat(prompt)
        return self._parse_response(response)


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


class TranscriptionAnalyzer:
    """Transcribe audio/video files to text using faster-whisper."""

    def __init__(self, model_size: str = "small", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

    def _get_model(self):
        """Lazy-load the whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type="int8"
            )
        return self._model

    def transcribe(self, file_path: str) -> str:
        """Transcribe audio from a file. Returns empty string on failure
        or if no speech detected."""
        try:
            model = self._get_model()
            segments, _ = model.transcribe(file_path, beam_size=5)
            text = " ".join(s.text.strip() for s in segments)
            return text.strip()
        except Exception:
            return ""
