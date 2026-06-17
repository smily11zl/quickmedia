"""OpenAI-compatible API adapter for remote AI model providers."""

import json
import urllib.request


class OpenAIAdapter:
    """Adapter for OpenAI-compatible /v1/chat/completions API."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 300, provider_name: str = "openai"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.provider_name = provider_name

    def test(self) -> bool:
        """Test connection by listing models. Returns True if reachable."""
        try:
            data = self._request("GET", "/models")
            return "data" in data or "models" in data
        except Exception:
            return False

    def chat(self, prompt: str, images: list[str] = None) -> str:
        """Send a chat completion request. Returns content string."""
        content = [{"type": "text", "text": prompt}]
        if images:
            for img in images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                })
        body = {"model": self.model, "messages": [{"role": "user", "content": content}]}
        # DeepSeek V4 models have thinking ON by default — explicitly disable
        if self.provider_name == "deepseek":
            body["thinking"] = {"type": "disabled"}
        print(f"[{self.provider_name}] model={self.model}", flush=True)
        print(f"[{self.provider_name} prompt] {prompt}", flush=True)
        data = self._request("POST", "/chat/completions", body)
        msg = data.get("choices", [{}])[0].get("message", {})
        content_text = msg.get("content", "")
        # Log reasoning_content if present (some providers output thinking separately)
        if msg.get("reasoning_content"):
            print(f"[{self.provider_name}] reasoning: {msg['reasoning_content'][:200]}", flush=True)
        print(f"[{self.provider_name}] {content_text}", flush=True)
        return content_text

    def _request(self, method: str, path: str, body: dict = None) -> dict:
        """Send an HTTP request to the API. Returns parsed JSON."""
        url = f"{self.base_url}{path}"
        req_body = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=req_body, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        if body:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
