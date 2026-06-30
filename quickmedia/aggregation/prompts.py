"""Prompt building functions for V12 aggregation."""


def build_prompt(mode: str, assets: list[dict], nodes: list[dict] = None, language: str = "zh") -> str:
    """Build an aggregation prompt based on mode.

    Args:
        mode: "full" | "full_append" | "append"
        assets: List of asset dicts with id, filename, asset_type,
                visual_description, ai_summary, tags
        nodes: Existing nodes for full_append/append modes
    """
    if mode == "full":
        return _build_full(assets, language)
    elif mode == "full_append":
        return _build_full_append(assets, nodes or [], language)
    elif mode == "append":
        return _build_append(assets, nodes or [], language)
    raise ValueError(f"Unknown aggregation mode: {mode}")


def _asset_text(asset: dict) -> str:
    """Format a single asset as a text line for the prompt."""
    desc = asset.get("video_summary") or asset.get("visual_description") or asset.get("ai_summary") or ""
    tags = [t["name"] for t in asset.get("tags", [])]
    return (
        f"  [{asset['id']}] {asset['filename']} ({asset['asset_type']})\n"
        f"    描述: {desc}\n"
        f"    标签: {', '.join(tags) if tags else '无'}"
    )


def _build_full(assets: list[dict], language: str = "zh") -> str:
    """Build full aggregation prompt from PromptConfig template."""
    from quickmedia.prompt_config import PromptConfig
    from quickmedia.config import Config
    cfg = Config()
    pc = PromptConfig(cfg.config_dir, language or "zh")
    base = pc.get_prompt("aggregation_full")
    asset_text = "\n".join(_asset_text(a) for a in assets)
    if "{assets}" in base:
        return base.replace("{assets}", asset_text)
    return base + "\n\n素材列表：\n" + asset_text

def _build_full_append(assets: list[dict], nodes: list[dict], language: str = "zh") -> str:
    """Build full_append aggregation prompt from PromptConfig template."""
    from quickmedia.prompt_config import PromptConfig
    from quickmedia.config import Config
    cfg = Config()
    pc = PromptConfig(cfg.config_dir, language or "zh")
    base = pc.get_prompt("aggregation_full_append")
    node_text = "\n".join(
        f"  [{n['id']}] {n['name']}: {n.get('description','')} (素材: {n.get('asset_ids',[])}))"
        for n in nodes
    )
    asset_text = "\n".join(_asset_text(a) for a in assets)
    base = base.replace("{nodes}", node_text)
    base = base.replace("{assets}", asset_text)
    return base


def _build_append(assets: list[dict], nodes: list[dict], language: str = "zh") -> str:
    """Build append aggregation prompt from PromptConfig template."""
    from quickmedia.prompt_config import PromptConfig
    from quickmedia.config import Config
    cfg = Config()
    pc = PromptConfig(cfg.config_dir, language or "zh")
    base = pc.get_prompt("aggregation_append")
    node_text = "\n".join(
        f"  [{n['id']}] {n['name']}: {n.get('description','')} (素材: {n.get('asset_ids',[])}))"
        for n in nodes
    )
    asset_text = "\n".join(_asset_text(a) for a in assets)
    base = base.replace("{nodes}", node_text)
    base = base.replace("{assets}", asset_text)
    return base

def build_append_prompt(
    node_info: dict[str, str],
    existing_assets: list[dict],
    candidates: list[dict],
    language: str = "zh",
) -> str:
    """Build analyze-append prompt from PromptConfig template."""
    from quickmedia.prompt_config import PromptConfig
    from quickmedia.config import Config
    cfg = Config()
    pc = PromptConfig(cfg.config_dir, language or "zh")
    base = pc.get_prompt("aggregation_analyze_append")
    
    existing_text = ""
    if existing_assets:
        existing_text = f"该节点当前包含 {len(existing_assets)} 个素材，内容特征为:\n"
        for a in existing_assets[:10]:
            summary = a.get("video_summary") or a.get("ai_summary", "") or a.get("visual_description", "") or a.get("filename", "")
            existing_text += f"  [{a.get('id', '?')}] {a.get('filename', '')}: {summary[:80]}\n"
    
    candidates_text = f"以下有 {len(candidates)} 个候选素材，请找出应该加入此节点的:\n"
    for c in candidates[:200]:
        summary = c.get("video_summary") or c.get("ai_summary", "") or c.get("visual_description", "") or ""
        candidates_text += f"  [{c['id']}] {c.get('filename', '')} ({c.get('asset_type', '')}) {summary[:60]}\n"
    
    base = base.replace("{node_name}", node_info.get("name", ""))
    base = base.replace("{node_description}", node_info.get("description", ""))
    base = base.replace("{existing_assets}", existing_text.strip())
    base = base.replace("{candidates}", candidates_text.strip())
    return base

