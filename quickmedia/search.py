"""Shared search logic used by API server and MCP server."""

import os, json, re


def get_embedding_adapter(cfg, data_dir: str):
    """Return (EmbeddingAdapter, binding_dict) or (None, None)."""
    from quickmedia.embedding import ChromaStore
    from quickmedia.providers import ProviderRegistry
    user_models = os.path.join(data_dir, "models.yaml")
    registry = ProviderRegistry(cfg, user_models)
    binding = registry.get_task_binding("embedding")
    if not binding:
        return None, None
    url = registry.get_provider_url(binding["provider"]) or ""
    if binding["provider"] == "ollama":
        from quickmedia.embedding import EmbeddingAdapter
        adapter = EmbeddingAdapter(base_url=url, model=binding.get("model", ""))
    else:
        from quickmedia.embedding import OpenAiEmbeddingAdapter
        env_path = os.path.join(data_dir, ".env")
        api_key = ""
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    if binding["provider"].upper() + "_API_KEY" in line:
                        api_key = line.split("=", 1)[1].strip()
                        break
        adapter = OpenAiEmbeddingAdapter(base_url=url, api_key=api_key, model=binding.get("model", ""))
    return adapter, binding


def search_assets(
    query: str,
    mode: str,
    limit: int,
    db,
    cfg,
    data_dir: str,
) -> list[dict]:
    """Search assets by keyword, semantic, or combined RRF mode.

    Returns list of asset dicts.
    """
    if not query.strip():
        return []

    # Tokenize
    try:
        import jieba
        tokens = [t for t in jieba.cut_for_search(query) if t.strip()]
    except ImportError:
        tokens = [query]

    # Keyword mode: FTS only
    if mode == "keyword":
        rows = db.search_tokens(tokens) if len(tokens) > 1 else db.search(query)
        return [dict(r) for r in rows][:limit]

    # Semantic modes: need ChromaDB
    chroma_path = os.path.join(data_dir, "chroma_db")
    if not os.path.isdir(chroma_path):
        return []

    from quickmedia.embedding import ChromaStore

    adapter, binding = get_embedding_adapter(cfg, data_dir)
    if not adapter:
        return []

    query_vector = adapter.embed(query)
    k = cfg.get("semantic.top_k") or 2
    store = ChromaStore(persist_path=chroma_path)
    # Clean orphan vectors before searching
    valid_ids = {r[0] for r in db.execute("SELECT id FROM assets")}
    store.clean_orphans(valid_ids)
    similar = store.query_search_terms(query_vector, k=k, n_results=limit)

    # Semantic mode: pure vector results
    if mode == "semantic":
        result = []
        for s in similar[:limit]:
            row = db.execute(
                "SELECT id, filename, asset_type, size, path, visual_description, ai_summary, "
                "ai_status, width, height, duration, transcript, video_summary, ocr_text, hash FROM assets WHERE id=?",
                (s["asset_id"],),
            )
            if row:
                r = dict(row[0])
                r["_distance"] = s["distance"]
                result.append(r)
        return result

    # Combined mode: RRF fusion
    kw_rows = db.search_tokens(tokens) if len(tokens) > 1 else db.search(query)
    kw_rank = {dict(r)["id"]: i + 1 for i, r in enumerate(kw_rows)}
    vec_rank = {s["asset_id"]: i + 1 for i, s in enumerate(similar)}
    all_ids = set(kw_rank.keys()) | set(vec_rank.keys())
    rrf_scores = {}
    for aid in all_ids:
        score = 0.0
        if aid in kw_rank:
            score += 1.0 / (60 + kw_rank[aid])
        if aid in vec_rank:
            score += 1.0 / (60 + vec_rank[aid])
        rrf_scores[aid] = score
    sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
    result = []
    for aid, score in sorted_ids:
        row = db.execute(
            "SELECT id, filename, asset_type, size, path, visual_description, ai_summary, "
            "ai_status, width, height, duration, transcript, video_summary, ocr_text, hash FROM assets WHERE id=?",
            (aid,),
        )
        if row:
            r = dict(row[0])
            r["_rrf_score"] = score
            result.append(r)
    return result


def _format_asset_text(asset: dict) -> str:
    """Format a single asset as text for AI search prompt.

    Priority: video_summary → visual_description → ai_summary.
    """
    desc = asset.get("video_summary") or asset.get("visual_description") or asset.get("ai_summary") or ""
    tags = [t["name"] for t in asset.get("tags", [])]
    return (
        f"  [{asset['id']}] {asset['filename']} ({asset['asset_type']})\n"
        f"    描述: {desc}\n"
        f"    标签: {', '.join(tags) if tags else '无'}"
    )


def parse_search_ai_result(raw: str) -> list[int]:
    """Extract asset_ids from LLM response JSON. Returns empty list on failure."""
    if not raw or not raw.strip():
        return []
    try:
        # Strip markdown code blocks
        cleaned = re.sub(r"```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"```", "", cleaned)
        cleaned = cleaned.strip()
        # Extract JSON object
        match = re.search(r'\{[^{}]*"asset_ids"\s*:\s*\[[^\]]*\][^{}]*\}', cleaned)
        if match:
            data = json.loads(match.group())
        else:
            data = json.loads(cleaned)
        return data.get("asset_ids", [])
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        return []


def search_ai_assets(
    query: str,
    db,
    cfg,
    data_dir: str,
) -> list[dict]:
    """AI-powered search: all assets → prompt → LLM → filter by asset_ids.

    Returns list of asset dicts with tags.
    """
    if not query.strip():
        return []

    # Get all active assets with descriptions
    rows = db.execute(
        "SELECT id, filename, asset_type, size, path, visual_description, ai_summary, ai_status, "
        "width, height, duration, transcript, video_summary, ocr_text "
        "FROM assets WHERE status='active'"
    )
    assets = []
    for r in rows:
        a = dict(r)
        tags = db.get_asset_tags(a["id"])
        a["tags"] = [dict(t) for t in tags]
        assets.append(a)

    if not assets:
        return []

    # Build asset text
    asset_lines = [_format_asset_text(a) for a in assets]
    asset_text = "\n".join(asset_lines)

    # Build prompt
    from quickmedia.prompt_config import PromptConfig
    pc = PromptConfig(data_dir)
    prompt = pc.get_prompt("search_ai")
    prompt = prompt.replace("{query}", query)
    prompt = prompt.replace("{assets}", asset_text)

    # Get AI adapter
    from quickmedia.providers import ProviderRegistry
    user_models = os.path.join(data_dir, "models.yaml")
    registry = ProviderRegistry(cfg, user_models)
    binding = registry.get_task_binding("search_ai")
    if not binding or not binding.get("provider") or not binding.get("model"):
        return []

    provider_name = binding["provider"]
    model = binding["model"]
    provider = registry.get_provider(provider_name) or {}
    url = provider.get("url", "")

    # Read API key from .env
    env_path = os.path.join(data_dir, ".env")
    api_key = ""
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                if provider_name.upper() + "_API_KEY" in line:
                    api_key = line.split("=", 1)[1].strip()
                    break

    if provider_name == "ollama":
        from quickmedia.ai_worker import OllamaAdapter
        adapter = OllamaAdapter(url.rstrip("/"), model, timeout=300)
    else:
        from quickmedia.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(base_url=url, api_key=api_key, model=model, timeout=300, provider_name=provider_name)

    print(f"[AI search] query={repr(query)} provider={provider_name} model={model} assets={len(assets)}", flush=True)

    # Call LLM
    response = adapter.chat(prompt)
    print(f"[AI search] response={repr(response)[:200]}", flush=True)

    # Parse result
    asset_ids = parse_search_ai_result(response or "")
    print(f"[AI search] matched={len(asset_ids)} ids={asset_ids}", flush=True)

    if not asset_ids:
        return []

    # Fetch full asset data for matched IDs
    result = []
    placeholders = ",".join("?" for _ in asset_ids)
    rows = db.execute(
        f"SELECT * FROM assets WHERE id IN ({placeholders})",
        tuple(asset_ids),
    )
    id_map = {asset_ids[i]: i for i in range(len(asset_ids))}
    for r in rows:
        item = dict(r)
        tags = db.get_asset_tags(item["id"])
        item["tags"] = [dict(t) for t in tags]
        result.append((id_map[item["id"]], item))

    # Sort by AI relevance order
    result.sort(key=lambda x: x[0])
    return [item for _, item in result]
