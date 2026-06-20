"""Async AI analysis worker for QuickMedia.

Uses a SQLite-backed queue (ai_queue table) to process AI analysis
tasks in the background without blocking file scanning.
"""

import os
from quickmedia.database import Database
from quickmedia.config import Config
from quickmedia.ai import VisionAnalyzer, TextAnalyzer, TranscriptionAnalyzer, OllamaAdapter, EmbeddingAnalyzer, merge_frame_results, extract_video_frames
from quickmedia.prompt_config import PromptConfig
from quickmedia.embedding import _build_field_text, ChromaStore, EmbeddingAdapter, OpenAiEmbeddingAdapter


class AIWorker:
    """Background worker that consumes ai_queue and runs AI analysis."""

    MAX_RETRIES = 3

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        timeout = config.get("ai.timeout") or 300
        self._timeout = timeout
        self._prompt_config = PromptConfig(config.config_dir) if hasattr(config, 'config_dir') else None
        self._transcriber = TranscriptionAnalyzer()

        # Load provider registry
        import os as _os
        self._config_dir = config.config_dir if hasattr(config, 'config_dir') else _os.path.expanduser("~/.asset-manager")
        self._env = {}
        env_path = _os.path.join(self._config_dir, ".env")
        if _os.path.isfile(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        self._env[k] = v
        from quickmedia.providers import ProviderRegistry
        models_path = _os.path.join(self._config_dir, "models.yaml")
        self._registry = ProviderRegistry(config, models_path)

    def _get_adapter(self, task_type: str):
        """Create an adapter for the given task type based on task_models config."""
        # Re-read config from disk to pick up live changes
        self.config._load()
        from quickmedia.providers import ProviderRegistry
        self._registry = ProviderRegistry(self.config, os.path.join(self._config_dir, "models.yaml"))
        # Also refresh .env
        env_path = os.path.join(self._config_dir, ".env")
        if os.path.isfile(env_path):
            self._env = {}
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        self._env[k] = v
        binding = self._registry.get_task_binding(task_type)
        if not binding:
            # Fall back to ollama provider config
            ollama_url = self.config.get("providers.ollama.url") or "http://localhost:11434"
            ollama_model = self.config.get("task_models.vision.model") or "qwen3.5:9b"
            return OllamaAdapter(ollama_url, ollama_model, self._timeout)
        provider_name = binding["provider"]
        model = binding["model"]
        provider = self._registry.get_provider(provider_name) or {}
        url = provider.get("url", "")
        api_key = self._env.get(f"{provider_name.upper()}_API_KEY", "")
        if provider_name == "ollama":
            api_key = api_key or "ollama"
            return OllamaAdapter(url.rstrip("/"), model, self._timeout)
        else:
            from quickmedia.openai_adapter import OpenAIAdapter
            return OpenAIAdapter(base_url=url, api_key=api_key, model=model, timeout=self._timeout, provider_name=provider_name)

    def enqueue(self, asset_id: int, task_type: str) -> None:
        """Add an AI analysis task to the queue (idempotent)."""
        existing = self.db.execute(
            "SELECT id FROM ai_queue WHERE asset_id=? AND task_type=? AND status='pending'",
            (asset_id, task_type),
        )
        if existing:
            return
        self.db.execute(
            "INSERT INTO ai_queue (asset_id, task_type) VALUES (?,?)",
            (asset_id, task_type),
        )

    def process_queue(self) -> int:
        """Process all pending AI tasks. Retries on failure up to MAX_RETRIES
        within the same loop iteration. Returns count of completed tasks."""
        print("[AIWorker] process_queue() called", flush=True)
        try:
            rows = self.db.execute(
                "SELECT aq.id, aq.asset_id, aq.task_type, a.path, a.asset_type, aq.attempt "
                "FROM ai_queue aq JOIN assets a ON aq.asset_id = a.id "
                "WHERE aq.status = 'pending' ORDER BY aq.id"
            )
            print(f"[AIWorker] query returned {len(rows)} rows", flush=True)
        except Exception as e:
            print(f"[AIWorker] query ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return 0
        if not rows:
            return 0
        print(f"[AIWorker] 发现 {len(rows)} 个待处理任务", flush=True)
        count = 0
        for row in rows:
            name = self.db.execute(
                "SELECT filename FROM assets WHERE id=?", (row["asset_id"],)
            )[0]["filename"]
            asset_type = row["asset_type"]
            task_type = row["task_type"]
            attempt = row["attempt"] or 0

            # Retry loop: keep trying the same task until success or max retries
            while True:
                self.db.execute(
                    "UPDATE ai_queue SET status='processing', attempt=? WHERE id=?",
                    (attempt, row["id"]),
                )
                print(f"[AIWorker] 分析中: {name} ({task_type}/{asset_type})"
                      f"{f' (第{attempt+1}次尝试)' if attempt > 0 else ''}", flush=True)
                try:
                    if task_type == "vision":
                        if asset_type == "video":
                            self._process_video(row["asset_id"], row["path"])
                        else:
                            self._process_vision(row["asset_id"], row["path"])
                    elif task_type == "text":
                        self._process_text(row["asset_id"], row["path"])
                    elif task_type == "transcribe":
                        self._process_transcribe(row["asset_id"], row["path"])
                    elif task_type == "embedding":
                        self._process_embedding(row["asset_id"])
                    self.db.execute(
                        "UPDATE ai_queue SET status='done', attempt=? WHERE id=?",
                        (attempt, row["id"]),
                    )
                    # Update analyzed_at timestamp
                    from datetime import datetime
                    self.db.execute(
                        "UPDATE assets SET analyzed_at=? WHERE id=?",
                        (datetime.now().isoformat(), row["asset_id"]),
                    )
                    print(f"[AIWorker] 完成: {name}", flush=True)
                    # Enqueue embedding if result is sufficient for vectorization
                    if task_type in ("vision", "text", "transcribe", "video_summary"):
                        self._enqueue_embedding(row["asset_id"])
                    break  # success
                except Exception as e:
                    attempt += 1
                    if attempt < self.MAX_RETRIES:
                        print(f"[AIWorker] 重试 {attempt}/{self.MAX_RETRIES}: {name} — {e}", flush=True)
                        import time; time.sleep(2)
                    else:
                        self.db.execute(
                            "UPDATE ai_queue SET status='failed', error=?, attempt=? WHERE id=?",
                            (str(e), attempt, row["id"]),
                        )
                        print(f"[AIWorker] 失败: {name} — {e}", flush=True)
                        break
            count += 1
        return count

    def _process_vision(self, asset_id: int, path: str) -> None:
        adapter = self._get_adapter("vision")
        analyzer = VisionAnalyzer(adapter=adapter, prompt_config=self._prompt_config)
        result = analyzer.analyze(path)
        name = self.db.execute("SELECT filename FROM assets WHERE id=?", (asset_id,))[0]["filename"]
        print(f"[AIWorker] vision result for {name}: desc={bool(result.get('description'))}, tags={len(result.get('tags',[]))}, ocr={bool(result.get('ocr_text'))}", flush=True)
        if result.get("description"):
            self.db.execute(
                "UPDATE assets SET ai_description=? WHERE id=?",
                (result["description"], asset_id),
            )
        if result.get("ocr_text"):
            self.db.execute(
                "UPDATE assets SET ocr_text=? WHERE id=?",
                (result["ocr_text"], asset_id),
            )
        if result.get("tags"):
            self._link_tags(asset_id, result["tags"], source="auto")

    def _process_video(self, asset_id: int, path: str) -> None:
        """Analyze a video using multi-frame sampling."""
        import tempfile
        num_frames = self.config.get("ai.video_frames") or 1
        frame_dir = tempfile.mkdtemp()
        frames = extract_video_frames(path, frame_dir, num_frames)
        if frames:
            frame_results = []
            adapter = self._get_adapter("vision")
            for fp in frames:
                analyzer = VisionAnalyzer(adapter=adapter, prompt_config=self._prompt_config)
                frame_results.append(analyzer.analyze(fp))
            merged = merge_frame_results(frame_results)
            if merged.get("description"):
                self.db.execute(
                    "UPDATE assets SET ai_description=? WHERE id=?",
                    (merged["description"], asset_id),
                )
            if merged.get("ocr_text"):
                self.db.execute(
                    "UPDATE assets SET ocr_text=? WHERE id=?",
                    (merged["ocr_text"], asset_id),
                )
            if merged.get("tags"):
                self._link_tags(asset_id, merged["tags"], source="auto")
        # Try generating combined summary if transcript exists
        self._try_generate_video_summary(asset_id)

    def _process_transcribe(self, asset_id: int, path: str) -> None:
        """Transcribe audio/video file, then run speech analysis."""
        transcript = self._transcriber.transcribe(path)
        if transcript:
            self.db.execute(
                "UPDATE assets SET transcript=? WHERE id=?",
                (transcript, asset_id),
            )
            name = self.db.execute(
                "SELECT filename FROM assets WHERE id=?", (asset_id,)
            )[0]["filename"]
            print(f"[AIWorker] 转录完成: {name} ({len(transcript)}字)", flush=True)
            # Run speech analysis on transcript
            adapter = self._get_adapter("speech")
            analyzer = TextAnalyzer(adapter=adapter, prompt_config=self._prompt_config)
            result = analyzer.analyze_speech(transcript)
            if result.get("summary"):
                self.db.execute(
                    "UPDATE assets SET ai_summary=? WHERE id=?",
                    (result["summary"], asset_id),
                )
            if result.get("tags"):
                self._link_tags(asset_id, result["tags"], source="auto")
            # Try generating combined summary if vision is also done
            self._try_generate_video_summary(asset_id)

    def _try_generate_video_summary(self, asset_id: int) -> None:
        """Generate combined summary if both speech and vision are done for a video."""
        rows = self.db.execute(
            "SELECT asset_type, ai_description, ai_summary FROM assets WHERE id=?",
            (asset_id,),
        )
        if not rows:
            return
        asset = rows[0]
        if asset["asset_type"] != "video":
            return
        if not asset["ai_description"] or not asset["ai_summary"]:
            return  # both analyses must be complete

        adapter = self._get_adapter("video_summary")
        # Generate combined summary via Ollama
        if self._prompt_config:
            base = self._prompt_config.get_prompt("video_summary")
        else:
            base = "请将以下两段关于同一视频的描述融合为一段综合总结（200字以内）："
        prompt = (
            f"{base}\n\n"
            f"画面内容：{asset['ai_description']}\n\n"
            f"语音内容：{asset['ai_summary']}\n\n"
            "综合总结："
        )
        response = adapter.chat(prompt)
        if response:
            self.db.execute(
                "UPDATE assets SET video_summary=? WHERE id=?",
                (response.strip(), asset_id),
            )
            name = self.db.execute(
                "SELECT filename FROM assets WHERE id=?", (asset_id,)
            )[0]["filename"]
            print(f"[AIWorker] 综合总结完成: {name}", flush=True)

    def _process_text(self, asset_id: int, path: str) -> None:
        text = self._read_text(path)
        if text:
            adapter = self._get_adapter("text")
            analyzer = TextAnalyzer(adapter=adapter, prompt_config=self._prompt_config)
            result = analyzer.analyze(text)
            if result.get("summary"):
                self.db.execute(
                    "UPDATE assets SET ai_summary=? WHERE id=?",
                    (result["summary"], asset_id),
                )
            if result.get("tags"):
                self._link_tags(asset_id, result["tags"], source="auto")

    def _read_text(self, path: str) -> str:
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext in {".txt", ".md"}:
            with open(path, "r", errors="replace") as f:
                return f.read()
        if ext == ".pdf":
            try:
                import fitz
                doc = fitz.open(path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                return text
            except ImportError:
                pass
        return ""

    def _link_tags(self, asset_id: int, tag_names: list[str], source: str = "auto") -> None:
        for name in tag_names:
            rows = self.db.execute("SELECT id FROM tags WHERE name=?", (name,))
            if rows:
                tag_id = rows[0]["id"]
            else:
                cursor = self.db.conn.execute(
                    "INSERT INTO tags (name) VALUES (?)", (name,)
                )
                self.db.conn.commit()
                tag_id = cursor.lastrowid
            existing = self.db.execute(
                "SELECT 1 FROM asset_tags WHERE asset_id=? AND tag_id=?",
                (asset_id, tag_id),
            )
            if not existing:
                self.db.execute(
                    "INSERT INTO asset_tags (asset_id, tag_id, source) VALUES (?,?,?)",
                    (asset_id, tag_id, source),
                )

    def _enqueue_embedding(self, asset_id: int) -> None:
        """Enqueue an embedding task if not already queued for this asset."""
        existing = self.db.execute(
            "SELECT 1 FROM ai_queue WHERE asset_id=? AND task_type='embedding'",
            (asset_id,),
        )
        if not existing:
            self.db.execute(
                "INSERT INTO ai_queue (asset_id, task_type) VALUES (?, 'embedding')",
                (asset_id,),
            )

    def _load_api_key(self, provider_name: str) -> str:
        """Load API key for a provider from env dict."""
        key = self._env.get(f"{provider_name.upper()}_API_KEY", "")
        if provider_name == "ollama":
            return key or "ollama"
        return key

    def _process_embedding(self, asset_id: int) -> None:
        """Generate and store embedding for a single asset."""
        from quickmedia.providers import ProviderRegistry

        # Get asset data
        rows = self.db.execute("SELECT * FROM assets WHERE id=?", (asset_id,))
        if not rows:
            raise ValueError(f"Asset {asset_id} not found")
        asset = dict(rows[0])
        tags = self.db.get_asset_tags(asset_id)
        asset["tags"] = [dict(t) for t in tags]

        # Get embedding adapter
        binding = self._registry.get_task_binding("embedding")
        if not binding:
            return  # no embedding model configured

        url = self._registry.get_provider_url(binding["provider"])
        if not url:
            return

        if binding["provider"] == "ollama":
            adapter = EmbeddingAdapter(base_url=url, model=binding["model"])
        else:
            api_key = self._load_api_key(binding["provider"])
            adapter = OpenAiEmbeddingAdapter(base_url=url, api_key=api_key, model=binding["model"])

        analyzer = EmbeddingAnalyzer(adapter=adapter)

        # Embed per field
        fields = {"description": 0.5, "tags": 0.3, "text": 0.2}
        vectors = {}
        for field in fields:
            field_text = _build_field_text(asset, field)
            if field_text:
                print(f"[Embedding] {field}: {field_text[:200]}", flush=True)
                vectors[field] = analyzer.embed(field_text)

        chroma_path = os.path.join(self._config_dir, "chroma_db")
        store = ChromaStore(persist_path=chroma_path)
        store.add_fields(asset_id, vectors)
        print(f"[Embedding] 完成: {asset['filename']}", flush=True)
