"""Prompt building functions for V12 aggregation."""


def build_prompt(mode: str, assets: list[dict], nodes: list[dict] = None) -> str:
    """Build an aggregation prompt based on mode.

    Args:
        mode: "full" | "full_append" | "append"
        assets: List of asset dicts with id, filename, asset_type,
                visual_description, ai_summary, tags
        nodes: Existing nodes for full_append/append modes
    """
    if mode == "full":
        return _build_full(assets)
    elif mode == "full_append":
        return _build_full_append(assets, nodes or [])
    elif mode == "append":
        return _build_append(assets, nodes or [])
    raise ValueError(f"Unknown aggregation mode: {mode}")


def _asset_text(asset: dict) -> str:
    """Format a single asset as a text line for the prompt."""
    desc = asset.get("visual_description") or asset.get("ai_summary") or ""
    tags = [t["name"] for t in asset.get("tags", [])]
    return (
        f"  [{asset['id']}] {asset['filename']} ({asset['asset_type']})\n"
        f"    描述: {desc}\n"
        f"    标签: {', '.join(tags) if tags else '无'}"
    )


def _build_full(assets: list[dict]) -> str:
    # parts = [
    #     "你是一个素材分类专家。请分析以下素材，生成精炼的聚合节点。",
    #     "",
    #     "每个节点代表一个语义主题，包含:",
    #     "- name: 节点名称 (简洁中文，如 '宠物日常')",
    #     "- description: 节点描述 (一句话说明主题)",
    #     "- asset_ids: 属于该节点的素材 ID 列表",
    #     "",
    #     "要求:",
    #     "- 节点尽量精炼，适合用户理解",
    #     "- 每个素材可以属于多个节点",
    #     "- 节点尽量覆盖所有素材，但无意义的素材不需要进入节点",
    #     "- 只输出 JSON，格式:",
    #     '  {"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}, ...]}',
    #     "",
    #     "素材列表:",
    # ]
    parts = [
        "你是一个素材库整理专家。",
        "",
        "请根据素材内容，为用户生成易于理解和浏览的主题节点。",
        "",
        "目标:",
        "- 帮助用户快速发现、浏览和管理素材",
        "- 节点应像素材库中的分类目录或收藏夹，而不是学术化分类",
        "- 优先生成用户真正关心和愿意点击浏览的主题",
        "",
        "每个节点包含:",
        "- name: 节点名称",
        "- description: 一句话描述该主题",
        "- asset_ids: 属于该节点的素材 ID 列表",
        "",
        "命名原则:",
        "- 优先使用用户日常语言",
        "- 优先体现主题、事件、人物、地点、兴趣或活动",
        "- 名称简洁明确，通常控制在2~8个字",
        "- 节点名称应像素材库中的分类目录或收藏夹名称",
        "- 优先使用用户会主动搜索或点击的名称",
        "",
        "优先示例:",
        "- 宠物日常",
        "- 猫咪合集",
        "- 家庭聚餐",
        "- 美食制作",
        "- 东京旅行",
        "- 健身训练",
        "- 工作记录",
        "- 产品演示",
        "- 咖啡探店",
        "- 居家办公",
        "",
        "避免示例:",
        "- 动物",
        "- 生物实体",
        "- 行为活动",
        "- 户外场景",
        "- 娱乐内容",
        "- 视觉对象",
        "",
        "主题识别优先级:",
        "- 人物",
        "- 动物",
        "- 地点",
        "- 事件",
        "- 项目",
        "- 兴趣爱好",
        "- 活动场景",
        "",
        "不要仅根据单个物体建立节点。",
        "",
        "避免:",
        "- 手机",
        "- 桌子",
        "- 杯子",
        "- 树木",
        "",
        "优先:",
        "- 数码产品",
        "- 办公场景",
        "- 咖啡时光",
        "- 产品展示",
        "",
        "节点粒度要求:",
        "- 不要过粗（如：动物、人物、场景）",
        "- 不要过细（如：橘猫睡觉、男子举手）",
        "- 以用户愿意点击浏览的专题粒度组织素材",
        "- 优先形成具有实际浏览价值的主题集合",
        "",
        "节点去重规则:",
        "- 不要生成语义重复或高度相似的节点",
        "- 不要同时生成上下级关系节点",
        "- 如果两个节点表达相近主题，应优先合并",
        "- 如果两个节点的大部分素材相同，应优先合并",
        "- 优先保留最容易理解、最具体且最有价值的名称",
        "",
        "示例:",
        "避免同时生成:",
        "- 宠物",
        "- 萌宠",
        "- 宠物日常",
        "",
        "应合并为:",
        "- 宠物日常",
        "",
        "避免同时生成:",
        "- 旅行",
        "- 东京旅行",
        "",
        "如果素材主要集中于东京，应保留:",
        "- 东京旅行",
        "",
        "覆盖原则:",
        "- 一个素材可以属于多个节点",
        "- 尽量覆盖有价值素材",
        "- 无法形成明确主题的零散素材可以忽略",
        "- 优先形成对用户有实际价值的专题集合",
        "",
        "节点质量要求:",
        "- 节点之间应具有明显区别",
        "- 每个节点都应有清晰主题",
        "- 避免仅因少量素材而创建节点",
        "- 避免产生大量名称相近的节点",
        "",
        "节点数量原则:",
        "- 宁可少而精，不要生成大量相似节点",
        "- 优先保留高价值主题",
        "- 仅保留用户最容易理解和使用的节点",
        "",
        "生成完成后请自检:",
        "- 是否存在重复主题",
        "- 是否存在上下级重复节点",
        "- 是否存在大量素材重叠的节点",
        "- 是否存在用户难以理解的抽象名称",
        "- 如存在，请先合并再输出",
        "",
        "输出要求:",
        "- 只输出 JSON",
        "- 不要输出解释说明",
        "- 格式如下:",
        '  {"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}, ...]}',
        "",
        "素材列表:",
    ]
    for a in assets:
        parts.append(_asset_text(a))
    return "\n".join(parts)


def _build_full_append(assets: list[dict], nodes: list[dict]) -> str:
    node_text = "\n".join(
        f"  [{n['id']}] {n['name']}: {n.get('description','')} (素材: {n.get('asset_ids',[])})"
        for n in nodes
    )
    parts = [
        "你是一个素材分类专家。已有以下聚合节点，请分析全量素材后进行优化。",
        "",
        "已有节点:",
        node_text,
        "",
        "你可以:",
        "- 增加新节点",
        "- 追加素材到已有节点",
        "- 修改已有节点的素材归属",
        "- 每个素材可以属于多个节点",
        "- 节点尽量覆盖所有素材，但无意义的素材不需要进入节点",
        "",
        "要求:",
        "只输出 JSON，格式:",
        '  {"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}, ...]}',
        "",
        "全量素材列表:",
    ]
    for a in assets:
        parts.append(_asset_text(a))
    return "\n".join(parts)


def _build_append(assets: list[dict], nodes: list[dict]) -> str:
    node_text = "\n".join(
        f"  [{n['id']}] {n['name']}: {n.get('description','')} (素材: {n.get('asset_ids',[])})"
        for n in nodes
    )
    parts = [
        "你是一个素材分类专家。已有以下聚合节点，请将新素材分配到合适的已有节点。",
        "",
        "已有节点:",
        node_text,
        "",
        "要求:",
        "- 每个素材可以属于多个节点",
        "- 节点尽量覆盖所有素材，但无意义的素材不需要进入节点",
        "只输出 JSON，格式:",
        '  {"assignments": {"node_id": [asset_id, ...], ...}}',
        "",
        "新素材列表:",
    ]
    for a in assets:
        parts.append(_asset_text(a))
    return "\n".join(parts)


def build_append_prompt(
    node_info: dict[str, str],
    existing_assets: list[dict],
    candidates: list[dict],
) -> str:
    """Build a prompt for analyzing which candidate assets should join a node.

    Args:
        node_info: {"name": str, "description": str}
        existing_assets: Assets already in the node [{filename, ai_summary}, ...]
        candidates: Candidate assets [{id, filename, asset_type, ai_summary}, ...]
    """
    parts = [
        "你是一个素材分类助手。有一个聚合节点，请判断哪些候选素材应该加入它。",
        f"节点名称: {node_info.get('name', '')}",
        f"节点描述: {node_info.get('description', '')}",
    ]
    if existing_assets:
        parts.append(f"该节点当前包含 {len(existing_assets)} 个素材，内容特征为:")
        for a in existing_assets[:10]:
            summary = a.get("ai_summary", "") or a.get("visual_description", "") or a.get("filename", "")
            parts.append(f"  - {a.get('filename', '')}: {summary[:80]}")
    parts.append("")
    parts.append(f"以下有 {len(candidates)} 个候选素材，请找出应该加入此节点的:")
    for c in candidates[:200]:
        summary = c.get("ai_summary", "") or c.get("visual_description", "") or ""
        parts.append(f"  [{c['id']}] {c.get('filename', '')} ({c.get('asset_type', '')}) {summary[:60]}")
    parts.append("")
    parts.append("仅返回 JSON: {\"asset_ids\": [id1, id2, ...]}")
    parts.append("如果没有匹配素材，返回 {\"asset_ids\": []}")
    return "\n".join(parts)
