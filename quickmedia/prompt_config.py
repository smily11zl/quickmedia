"""AI prompt configuration management for QuickMedia.

Loads and manages prompt templates from ~/.asset-manager/prompts.yaml.
"""

import os
import yaml


DEFAULT_PROMPTS = {
    "vision": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"description": "图片描述", "tags": ["标签1", "标签2", "标签3"], "text": "画面中文字内容", "search_terms": ["搜索词1", "搜索词2"]}\n'
            "如果没有识别到文字，text 为空字符串。\n"
            "search_terms 规则（3-8个）：\n"
            "- 从用户搜索角度生成，而不是简单改写 tags。\n"
            "- 必须覆盖多个维度：主体、场景、动作、风格、情绪、用途、上位概念等。\n"
            "- 可以补充原内容未直接出现但合理相关的搜索词。\n"
            "- 优先输出单一概念词，避免多个概念拼接成长短语。\n"
            "- 用户可能直接搜索的词优先。\n"
            "- 搜索词应尽量扩大素材的可检索范围。\n"
            "- 避免重复、近义重复和无意义扩展。\n"
            "- 不要输出完整句子。\n"
        ),
        "default": (
            "请分析图片\n"
            "1. 使用50字以内描述图片内容、整体场景、包含主体（人，动物，物件）、事件等\n"
            "2. 识别包含的关键元素、画面中文字等，提取最重要的标签\n\n"
            "标签内容要求：\n"
            "- 提取3-8个最重要标签。\n"
            "- 优先保留完整事物，不要拆分组成部分。\n"
            "- 避免重复或明显包含关系标签。\n"
            "- 优先输出主体、场景和关键动作。\n"
            "- 保留对搜索有价值的重要风格、颜色或设计特征。\n"
            "- 忽略检索价值较低的细节和装饰元素。\n"
            "- 标签应符合人工打标习惯。\n"
            "- 仅输出素材中明确存在的内容，不要推测。\n"
        ),
        "custom": "",
        "presets": [
            {"name": "摄影", "content": "请分析这张照片的构图方式（三分法/中心/对称等）、光线方向与强度、色彩搭配和景深效果。提取画面中的摄影元素和视觉焦点。"},
            {"name": "设计", "content": "请分析这张图片的版式布局、色彩方案、字体风格和设计风格（极简/扁平/复古等）。识别 UI 组件、图标和交互元素。"},
            {"name": "宠物", "content": "请描述图片中宠物的品种、毛色、体态和数量。描述宠物所在环境和行为状态。"},
            {"name": "人物", "content": "请描述图片中人物的性别、大致年龄、表情、穿着风格和姿态。识别配饰、妆容特征等视觉元素以及任何可识别的文本内容。"},
        ],
    },
    "text": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"summary": "文档摘要", "tags": ["标签1", "标签2", "标签3"], "search_terms": ["搜索词1", "搜索词2"]}\n'
            "search_terms 规则（5-10个）：\n"
            "- 从知识检索角度生成，而不是简单改写 tags。\n"
            "- 必须覆盖主题、技术方向、业务领域、应用场景、上位概念等多个维度。\n"
            "- 对于具体技术、框架、产品，可补充相关领域和上位概念。\n"
            "- 可以补充合理相关的搜索词。\n"
            "- 用户未来可能搜索的词优先。\n"
            "- 优先输出单一概念词。\n"
            "- 避免重复和近义重复。\n"
            "- 不要输出完整句子。\n"
        ),
        "default": (
            "总结以下文档内容（200字以内），并提取最重要的主题关键词。\n\n"
            "标签内容要求：\n"
            "- 提取5-10个最重要标签。\n"
            "- 优先保留核心主题。\n"
            "- 优先保留技术栈、框架、产品名称、领域术语。\n"
            "- 优先保留文档涉及的重要概念。\n"
            "- 避免重复或明显包含关系标签。\n"
            "- 标签应符合人工打标习惯。\n"
            "- 仅输出文档中明确出现的重要内容。\n"
        ),
        "custom": "",
        "presets": [
            {"name": "技术文档", "content": "总结文档涉及的技术栈、架构设计和核心实现方案。提取关键的技术名词、框架名称和编程概念。"},
            {"name": "笔记日记", "content": "总结笔记中记录的个人思考、关键决定和待办事项。提取情绪关键词、涉及的人物和事件类型。"},
            {"name": "学习总结", "content": "总结文档中的核心知识点、关键概念定义和知识点之间的关联。提取学科领域、主题词和专业术语。"},
        ],
    },
    "speech": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"summary": "语音摘要", "tags": ["标签1", "标签2", "标签3"], "search_terms": ["搜索词1", "搜索词2"]}\n'
            "search_terms 规则（3-8个）：\n"
            "- 从未来检索角度生成，而不是简单改写 tags。\n"
            "- 必须覆盖主题、业务领域、项目背景、技术方向、相关概念等多个维度。\n"
            "- 对于专业术语，可补充上位概念和常见表达。\n"
            "- 可以补充合理相关的搜索词。\n"
            "- 用户未来可能搜索的词优先。\n"
            "- 优先输出单一概念词。\n"
            "- 避免重复和近义重复。\n"
            "- 不要输出完整句子。\n"
        ),
        "default": (
            "以下是一段语音转录文本。请总结这段语音的主要内容（150字以内），"
            "标签内容要求：\n"
            "- 提取3-8个最重要标签。\n"
            "- 优先保留核心话题。\n"
            "- 优先保留项目、产品、组织、人物名称。\n"
            "- 优先保留关键决策、行动项和任务。\n"
            "- 避免重复或明显包含关系标签。\n"
            "- 标签应符合人工打标习惯。\n"
            "- 仅输出内容中明确提及的信息。\n"
        ),
        "custom": "",
        "presets": [
            {"name": "会议记录", "content": "总结会议中的关键决定、行动项和各方立场。提取参与人角色、讨论议题和截止时间。"},
            {"name": "采访对话", "content": "总结采访的核心话题、受访者观点和关键引用。提取话题类型、情绪基调和关键人物。"},
            {"name": "学习总结", "content": "总结讲解的核心知识点、举例说明和知识结构。提取学科领域、关键概念和学习方法。"},
        ],
    },
    "video_summary": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"video_summary": "综合总结", "tags": ["标签1", "标签2", "标签3"], "search_terms": ["搜索词1", "搜索词2"]}\n'
            "search_terms 规则（3-8个）：\n"
            "- 从用户搜索角度生成，而不是简单改写 tags。\n"
            "- 优先基于视频实际内容生成搜索词。\n"
            "- 对于具体实体，可补充合理的上位概念和常见搜索表达。\n"
            "- 可以补充与内容高度相关的搜索词。\n"
            "- 用户未来可能搜索的词优先。\n"
            "- 当语音内容包含评价、调侃、猜测、玩笑或与画面不一致的信息时，不应生成对应搜索词。\n"
            "- 不要生成主观评价、情绪表达或争议性搜索词。\n"
            "- 不要为了扩大搜索范围而生成弱关联词。\n"
            "- 优先输出单一概念词。\n"
            "- 避免重复、近义重复和无意义扩展。\n"
            "- 不要输出完整句子。\n"
        ),
        "default": (
            "请将以下两段关于同一视频的描述融合为一段综合总结（200字以内）："
            "标签内容要求：\n"
            "- 提取3-8个最重要标签。\n"
            "- 优先保留视频的核心主题和主要事件。\n"
            "- 优先保留人物、项目、产品、品牌、地点等关键实体。\n"
            "- 优先保留关键动作和行为。\n"
            "- 同时结合画面内容和语音内容进行分析。\n"
            "- 标签应优先基于画面可确认事实，其次参考语音补充信息。\n"
            "- 当语音内容包含评价、调侃、猜测、玩笑或与画面不一致的信息时，不作为标签。\n"
            "- 不要将主观评价、情绪表达、辱骂性描述或分析结论作为标签。\n"
            "- 避免重复或明显包含关系标签。\n"
            "- 标签应符合人工打标习惯。\n"
            "- 仅输出视频中明确出现或明确提及的内容，不要推测。\n"
            "- 对于教学、演讲、会议、采访等内容，优先输出讨论主题而非画面细节。\n"
        ),
        "custom": "",
        "presets": [],
    },
    "video_vision": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"description": "帧描述", "tags": ["标签1", "标签2", "标签3"], "text": "画面中文字内容", "search_terms": ["搜索词1", "搜索词2"]}\n'
            "如果没有识别到文字，text 为空字符串。\n"
            "search_terms 规则（3-8个）：\n"
            "- 从用户搜索角度生成。\n"
            "- 优先补充同义词和合理上位概念。\n"
            "- 搜索词必须与视频内容高度相关。\n"
            "- 可以结合画面和语音表达相同主题。\n"
            "- 优先覆盖主题、行业、场景、用途等维度。\n"
            "- 不要输出泛化词和弱关联词。\n"
            "- 优先输出单一概念词。\n"
            "- 避免重复和近义重复。\n"
            "- 不要输出完整句子。\n"
        ),
        "default": (
            "这是从视频中提取的帧画面。\n"
            "1. 使用50字以内描述视频内容、整体场景、包含主体（人，动物，物件）、事件等\n"
            "2. 识别包含的关键元素、画面中文字等，提取最重要的标签\n\n"
            "以及整体氛围。50字以内。"
            "标签内容要求：\n"
            "- 提取3-8个最重要标签。\n"
            "- 优先保留视频核心主题。\n"
            "- 优先保留关键人物、产品、项目、品牌、地点等实体。\n"
            "- 优先保留关键动作、事件或行为。\n"
            "- 同时结合画面内容和语音内容进行分析。\n"
            "- 避免重复或明显包含关系标签。\n"
            "- 优先输出对检索最有价值的信息。\n"
            "- 仅输出明确出现或明确提及的内容，不要推测。\n"
            "- 标签应符合人工打标习惯。\n"
        ),
        "custom": "",
        "presets": [],
    },
    "search_ai": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"asset_ids": [1, 5, 23]}\n'
            '如果没有找到相关素材，输出：{"asset_ids": []}\n'
        ),
        "default": (
            "你是素材搜索助手。下面是一批素材列表。\n\n"
            "每行格式：\n"
            "  [ID] 文件名 (类型)\n"
            "    描述: AI分析描述\n"
            "    标签: tag1, tag2, ...\n\n"
            "用户的搜索意图是：{query}\n\n"
            "请返回**严格相关**的素材ID列表。\n"
            "- 只有素材内容与用户查询明确相关时才返回\n"
            "- 不确定的相关性 → 不返回（宁可缺勿滥）\n"
            "- 按相关度从高到低排序\n\n"
            "素材列表：\n"
            "{assets}\n"
        ),
        "custom": "",
        "presets": [],
    },
}


class PromptConfig:
    """Manages AI prompt configuration stored in YAML."""

    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self._file = os.path.join(config_dir, "prompts.yaml")
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._file):
            with open(self._file, "r") as f:
                data = yaml.safe_load(f) or {}
        else:
            self._ensure_prompts_yaml()
            data = dict(DEFAULT_PROMPTS)
        # Merge missing fields from DEFAULT_PROMPTS (for upgrades)
        for key in DEFAULT_PROMPTS:
            if key not in data:
                data[key] = dict(DEFAULT_PROMPTS[key])
            # Always sync system_format from code (user edits go in custom/default)
            data[key]["system_format"] = DEFAULT_PROMPTS[key]["system_format"]
        return data

    def _ensure_prompts_yaml(self) -> None:
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self._file, "w") as f:
            yaml.dump(DEFAULT_PROMPTS, f, allow_unicode=True, sort_keys=False)

    def get_prompt(self, task_type: str) -> str:
        section = self._data.get(task_type, {})
        custom = section.get("custom", "")
        if custom:
            base = custom
        else:
            base = section.get("default", "")
        fmt = section.get("system_format", "")
        if fmt:
            return f"{base}\n\n{fmt}"
        return base

    def get_all(self) -> dict:
        return self._data

    def save(self, task_type: str, custom_prompt: str) -> None:
        self._data.setdefault(task_type, {})["custom"] = custom_prompt
        with open(self._file, "w") as f:
            yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)

    def reset(self, task_type: str) -> None:
        self._data.setdefault(task_type, {})["custom"] = DEFAULT_PROMPTS[task_type].get("custom", "")
        with open(self._file, "w") as f:
            yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)
