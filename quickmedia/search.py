"""Shared search logic used by API server and MCP server."""

import os, json


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
    similar = store.query_search_terms(query_vector, k=k, n_results=limit)

    # Semantic mode: pure vector results
    if mode == "semantic":
        result = []
        for s in similar[:limit]:
            row = db.execute(
                "SELECT id, filename, asset_type, size, visual_description, ai_summary FROM assets WHERE id=?",
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
            "SELECT id, filename, asset_type, size, visual_description, ai_summary FROM assets WHERE id=?",
            (aid,),
        )
        if row:
            r = dict(row[0])
            r["_rrf_score"] = score
            result.append(r)
    return result
