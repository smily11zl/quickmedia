"""V14 — Shared aggregation orchestration.

One module, one interface. Used by the API endpoint and the MCP tool — two adapters,
one seam.
"""

import os, json


def _get_adapter(config_dir: str):
    """Create an AI adapter from provider config. Returns (adapter, provider_name, model)."""
    from quickmedia.config import Config
    from quickmedia.providers import ProviderRegistry
    from quickmedia.ai import OllamaAdapter
    from quickmedia.openai_adapter import OpenAIAdapter

    cfg = Config(config_dir=config_dir)
    models_path = os.path.join(config_dir, "models.yaml")
    registry = ProviderRegistry(cfg, models_path)
    binding = registry.get_task_binding("aggregation")
    if not binding or not binding.get("provider") or not binding.get("model"):
        return None, "", ""
    provider_name = binding["provider"]
    model = binding["model"]

    url = registry.get_provider_url(provider_name) or ""

    if provider_name == "ollama":
        adapter = OllamaAdapter(base_url=url, model=model, timeout=300)
    else:
        env_path = os.path.join(config_dir, ".env")
        api_key = ""
        if os.path.isfile(env_path):
            with open(env_path) as f:
                for line in f:
                    if provider_name.upper() + "_API_KEY" in line:
                        api_key = line.split("=", 1)[1].strip()
                        break
        adapter = OpenAIAdapter(
            base_url=url, api_key=api_key, model=model,
            provider_name=provider_name, timeout=300,
        )
    return adapter, provider_name, model


def _parse_response(response: str) -> dict:
    """Parse JSON response from AI. Strips markdown and explanatory text, returns dict."""
    content = response.strip()
    # Strip markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:]) if len(lines) > 1 else content
        if content.endswith("```"):
            content = content[:-3]
    # Try direct json.loads first
    try:
        return json.loads(content)
    except Exception:
        pass
    # Extract JSON by finding matching braces
    depth = 0
    start = -1
    for i, ch in enumerate(content):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(content[start:i + 1])
                except Exception:
                    pass
                start = -1
    return {}


def run_aggregation(mode: str, db, config_dir: str) -> tuple[int, int]:
    """Execute aggregation synchronously. Returns (node_count, assignment_count).

    Args:
        mode: "full" | "full_append" | "append"
        db: Database instance
        config_dir: path to config directory (~/.asset-manager)

    Returns:
        (number of new nodes, number of asset assignments)
    """
    from quickmedia.aggregation.worker import get_all_assets, get_all_nodes, save_aggregation_result
    from quickmedia.aggregation.prompts import build_prompt

    assets = get_all_assets(db)
    nodes = get_all_nodes(db) if mode != "full" else None

    # Compute unassigned for append/full_append modes
    if mode in ("append", "full_append"):
        assigned_ids = set()
        for n in (nodes or []):
            for aid in n.get("asset_ids", []):
                assigned_ids.add(aid)
        unassigned = [a for a in assets if a["id"] not in assigned_ids]
        if mode == "append" and not unassigned:
            return 0, 0
        if mode == "append":
            assets = unassigned

    print(f"[Aggregation] 素材数: {len(assets)}, 已有节点数: {len(nodes) if nodes else 0}", flush=True)

    adapter, provider_name, model = _get_adapter(config_dir)
    if not adapter:
        raise RuntimeError("聚合任务需要配置模型，请在设置中绑定")
    print(f"[Aggregation] 调用 AI: provider={provider_name} model={model}", flush=True)

    prompt = build_prompt(mode, assets, nodes)
    print(f"[Aggregation] prompt 长度: {len(prompt)} 字符", flush=True)

    response = adapter.chat(prompt)
    result = _parse_response(response)

    if mode == "full":
        db.execute("DELETE FROM node_assets")
        db.execute("DELETE FROM nodes")

    save_aggregation_result(db, result)
    assignments = result.get("assignments", {})
    total_assigned = sum(len(v) for v in assignments.values()) if isinstance(assignments, dict) else 0
    return len(result.get("nodes", [])), total_assigned
