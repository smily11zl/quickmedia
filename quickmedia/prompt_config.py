"""AI prompt configuration management for QuickMedia.

Loads and manages prompt templates from ~/.asset-manager/prompts.yaml.
"""

import os
import threading
import yaml


DEFAULT_PROMPTS_ZH = {
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
        "context_label": "文档内容",
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
    "speech_summary": {
        "context_label": "语音转录",
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

    "aggregation_full": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}, ...]}\n'
        ),
        "default": (
            "你是一个素材库整理专家。\n\n"
            "请根据素材内容，为用户生成易于理解和浏览的主题节点。\n\n"
            "目标:\n"
            "- 帮助用户快速发现、浏览和管理素材\n"
            "- 节点应像素材库中的分类目录或收藏夹，而不是学术化分类\n"
            "- 优先生成用户真正关心和愿意点击浏览的主题\n\n"
            "每个节点包含:\n"
            "- name: 节点名称\n"
            "- description: 一句话描述该主题\n"
            "- asset_ids: 属于该节点的素材 ID 列表\n\n"
            "命名原则:\n"
            "- 优先使用用户日常语言\n"
            "- 优先体现主题、事件、人物、地点、兴趣或活动\n"
            "- 名称简洁明确，通常控制在2~8个字\n"
            "- 节点名称应像素材库中的分类目录或收藏夹名称\n"
            "- 优先使用用户会主动搜索或点击的名称\n\n"
            "优先示例:\n"
            "- 宠物日常\n- 猫咪合集\n- 家庭聚餐\n- 美食制作\n- 东京旅行\n- 健身训练\n- 工作记录\n- 产品演示\n- 咖啡探店\n- 居家办公\n\n"
            "避免示例:\n"
            "- 动物\n- 生物实体\n- 行为活动\n- 户外场景\n- 娱乐内容\n- 视觉对象\n\n"
            "主题识别优先级:\n- 人物\n- 动物\n- 地点\n- 事件\n- 项目\n- 兴趣爱好\n- 活动场景\n\n"
            "不要仅根据单个物体建立节点。\n\n"
            "避免:\n- 手机\n- 桌子\n- 杯子\n- 树木\n\n"
            "优先:\n- 数码产品\n- 办公场景\n- 咖啡时光\n- 产品展示\n\n"
            "节点粒度要求:\n"
            "- 不要过粗（如：动物、人物、场景）\n- 不要过细（如：橘猫睡觉、男子举手）\n"
            "- 以用户愿意点击浏览的专题粒度组织素材\n- 优先形成具有实际浏览价值的主题集合\n\n"
            "节点去重规则:\n"
            "- 不要生成语义重复或高度相似的节点\n- 不要同时生成上下级关系节点\n"
            "- 如果两个节点表达相近主题，应优先合并\n- 如果两个节点的大部分素材相同，应优先合并\n"
            "- 优先保留最容易理解、最具体且最有价值的名称\n\n"
            "示例:\n避免同时生成:\n- 宠物\n- 萌宠\n- 宠物日常\n\n应合并为:\n- 宠物日常\n\n"
            "避免同时生成:\n- 旅行\n- 东京旅行\n\n如果素材主要集中于东京，应保留:\n- 东京旅行\n\n"
            "覆盖原则:\n"
            "- 一个素材可以属于多个节点\n- 尽量覆盖有价值素材\n"
            "- 无法形成明确主题的零散素材可以忽略\n- 优先形成对用户有实际价值的专题集合\n\n"
            "节点质量要求:\n"
            "- 节点之间应具有明显区别\n- 每个节点都应有清晰主题\n"
            "- 避免仅因少量素材而创建节点\n- 新建节点至少关联2个以上素材，单素材节点不予创建\n"
            "- 单个素材应优先追加到已有节点，而非单独建节点\n"
            "- 如果一个素材无法归入任何节点，不要为它单独建节点，应省略\n"
            "- 如果只能为某素材创建一个节点，且该节点只有这一个素材，则不要创建\n"
            "- 避免产生大量名称相近的节点\n\n"
            "节点数量原则:\n"
            "- 宁可少而精，不要生成大量相似节点\n- 优先保留高价值主题\n- 仅保留用户最容易理解和使用的节点\n\n"
            "生成完成后请自检:\n- 是否存在重复主题\n- 是否存在上下级重复节点\n"
            "- 是否存在大量素材重叠的节点\n- 是否存在用户难以理解的抽象名称\n- 如存在，请先合并再输出\n\n"
            "素材列表：\n{assets}\n"
        ),
        "custom": "",
        "presets": [],
    },
    "aggregation_full_append": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"nodes": [{"name": "新节点名", "description": "...", "asset_ids": [1,2]}], "assignments": {"已有节点ID": [素材ID,...]}}\n'
        ),
        "default": (
            "你是一个素材分类专家。已有以下聚合节点，请分析全量素材后进行优化。\n\n"
            "已有节点:\n{nodes}\n\n"
            "你可以:\n"
            "- 增加新节点\n- 追加素材到已有节点\n"
            "- 每个素材可以属于多个节点\n- 节点尽量覆盖所有素材，但无意义的素材不需要进入节点\n\n"
            "新增节点约束:\n- 尽量不要新建与已有节点意义过于接近的节点\n"
            "- 如果新节点和已有节点表达相近主题，应追加到已有节点而非新建\n"
            "- 优先将素材分配到语义最匹配的已有节点\n- 新建节点至少关联2个以上素材，单素材节点不予创建\n"
            "- 单个素材应优先追加到已有节点\n"
            "- 如果只有一个素材无法归入任何已有节点，不要为它单独建节点，应省略\n\n"
            "命名原则:\n- 优先使用用户日常语言\n- 名称简洁明确，通常控制在2~8个字\n"
            "- 节点名称应像素材库中的分类目录或收藏夹名称\n\n"
            "避免单物体节点:\n- 不要针对单个物体建立节点（如：手机、桌子、杯子）\n"
            "- 应组织为主题集合（如：数码产品、办公场景）\n\n"
            "节点去重:\n- 不要生成语义重复或高度相似的节点\n"
            "- 如果两个节点的大部分素材相同，应优先合并\n- 不要同时生成上下级关系节点\n\n"
            "同时支持新建节点和追加素材到已有节点。\n"
            "- nodes: 新建的节点（已有节点不要出现在这里）\n- assignments: 将素材追加到已有节点，key 是已有节点的 ID\n"
            "- 如果不需要新建节点，nodes 可以为空数组\n- 如果不需要追加素材，assignments 可以为空对象\n\n"
            "全量素材列表：\n{assets}\n"
        ),
        "custom": "",
        "presets": [],
    },
    "aggregation_append": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"assignments": {"node_id": [asset_id, ...], ...}}\n'
        ),
        "default": (
            "你是一个素材分类专家。已有以下聚合节点，请将新素材分配到合适的已有节点。\n\n"
            "已有节点:\n{nodes}\n\n"
            "要求:\n- 每个素材可以属于多个节点\n"
            "- 节点尽量覆盖所有素材，但无意义的素材不需要进入节点\n\n"
            "新素材列表：\n{assets}\n"
        ),
        "custom": "",
        "presets": [],
    },
    "aggregation_analyze_append": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"asset_ids": [id1, id2, ...]}\n'
            '如果没有匹配素材，返回：{"asset_ids": []}\n'
        ),
        "default": (
            "你是一个素材分类助手。有一个聚合节点，请判断哪些候选素材应该加入它。\n\n"
            "节点名称: {node_name}\n"
            "节点描述: {node_description}\n"
            "{existing_assets}\n\n"
            "候选素材：\n{candidates}\n"
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

DEFAULT_PROMPTS_EN = {
    "vision": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"description": "Image description", "tags": ["tag1", "tag2", "tag3"], "text": "Text content in image", "search_terms": ["search term1", "search term2"]}\n'
            "If no text is recognized, set text to empty string.\n"
            "search_terms rules (3-8 terms):\n"
            "- Generate from a user search perspective, not simple rewrites of tags.\n"
            "- Must cover multiple dimensions: subject, scene, action, style, mood, usage, broader concepts, etc.\n"
            "- Can supplement with reasonably related search terms not directly appearing in the content.\n"
            "- Prioritize single-concept terms, avoid concatenating multiple concepts into long phrases.\n"
            "- Prioritize terms users would likely search for.\n"
            "- Search terms should maximize the discoverability of the asset.\n"
            "- Avoid duplicates, near-synonyms, and meaningless expansions.\n"
            "- Do not output complete sentences.\n"
        ),
        "default": ("Output in English.\n"
            "Analyze this image.\n"
            "- description: Describe the image content within 50 characters. Scene, subjects, events, etc.\n"
            "- tags: Identify key elements, text in image, etc. Extract the most important tags.\n"
            "Tag requirements:\n"
            "  * 3-8 most important tags\n"
            "  * Prioritize complete objects, don't split into components\n"
            "  * Avoid duplicate or obviously hierarchical tags\n"
            "  * Prioritize subject, scene, and key actions\n"
            "  * Retain important styles, colors, or design features valuable for search\n"
            "  * Ignore low-value details and decorative elements\n"
            "  * Tags should match human tagging conventions\n"
            "  * Only output elements explicitly present in the asset, do not speculate\n"
            "- search_terms:\n"
            "  * If style is design/scene: Analyze composition (rule of thirds, symmetry, etc.), lighting direction and intensity, color palette, depth of field, extract photographic elements and visual focus\n"
            "  * If style is graphic design: Analyze layout, color scheme, typography style, design style (retro, etc.), icons and interactive elements\n"
            "  * If style is pet photo: Describe breed, posture and quantity, describe environment and behavior\n"
            "  * If style is portrait: Describe gender, approximate age, clothing style and pose, identify accessories, makeup features, and any recognizable text\n"
        ),
        "custom": "",
        "presets": [
            {"name": "Photography", "content": "Analyze the composition of this photo (rule of thirds, center, symmetry, etc.), lighting direction and intensity, color palette, and depth of field. Extract photographic elements and visual focus."},
            {"name": "Design", "content": "Analyze the layout, color scheme, typography, and design style (minimal, flat, retro, etc.) of this image. Identify UI components, icons, and interaction elements."},
            {"name": "Pet", "content": "Describe the breed, coat color, posture, and count of the pet(s) in the image. Describe the environment and behavior state."},
            {"name": "Portrait", "content": "Describe the gender, approximate age, expression, clothing style, and pose of the person. Identify accessories, makeup features, and any recognizable text."},
        ],
    },
    "text": {
        "context_label": "Document content",
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"summary": "Document summary", "tags": ["tag1", "tag2", "tag3"], "search_terms": ["search term1", "search term2"]}\n'
            "search_terms rules (3-8 terms):\n"
            "- Generate from a knowledge retrieval perspective, not simple rewrites of tags.\n"
            "- Must cover: topic, technical direction, business domain, application scenario, broader concepts, etc.\n"
            "- For specific technologies, can supplement related domains and broader concepts.\n"
            "- Can supplement reasonably related search terms.\n"
            "- Prioritize terms users may search for in the future.\n"
            "- Prioritize single-concept terms.\n"
            "- Avoid duplicates and near-synonyms.\n"
            "- Do not output complete sentences.\n"
        ),
        "default": ("Output in English.\n"
            "Summarize the following document content within 50 characters, and extract the most important topic keywords.\n"
            "Tag requirements:\n"
            "  * 3-8 most important tags\n"
            "  * Prioritize core topics\n"
            "  * Prioritize tech stack, product names, domain terminology\n"
            "  * Prioritize important concepts covered in the document\n"
            "  * Avoid duplicate or obviously hierarchical tags\n"
            "  * Tags should match human tagging conventions\n"
            "  * Only output content explicitly important in the document\n"
            "  * If tech doc: Summarize tech stack, architecture design and core implementation, extract key technical terms, framework names and programming concepts\n"
            "  * If notes/diary: Summarize personal thoughts, key decisions and todos, extract emotional keywords, involved people and event types\n"
            "  * If study notes: Summarize core knowledge points, key concept definitions and relationships between concepts, extract subject areas, topic words and professional terminology\n"
        ),
        "custom": "",
        "presets": [
            {"name": "Tech Doc", "content": "Summarize the tech stack, architecture design, and core implementation. Extract key technical terms, framework names, and programming concepts."},
            {"name": "Notes/Diary", "content": "Summarize personal thoughts, key decisions, and action items in the notes. Extract emotional keywords, involved people, and event types."},
            {"name": "Study Notes", "content": "Summarize core knowledge points, key concept definitions, and relationships between concepts. Extract subject areas, topic words, and professional terminology."},
        ],
    },
    "speech_summary": {
        "context_label": "Speech transcript",
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"summary": "Speech summary", "tags": ["tag1", "tag2", "tag3"], "search_terms": ["search term1", "search term2"]}\n'
            "search_terms rules (3-8 terms):\n"
            "- Generate from a future retrieval perspective, not simple rewrites.\n"
            "- Must cover: topic, business domain, project background, technical direction, related concepts, etc.\n"
            "- For professional terminology, can supplement broader concepts and common expressions.\n"
            "- Can supplement reasonably related search terms.\n"
            "- Prioritize terms users may search for in the future.\n"
            "- Prioritize single-concept terms.\n"
            "- Avoid duplicates and near-synonyms.\n"
            "- Do not output complete sentences.\n"
        ),
        "default": ("Output in English.\n"
            "The following is a speech transcript. Summarize the main content within 50 characters.\n"
            "Tag requirements:\n"
            "  * 3-8 most important tags\n"
            "  * Prioritize core topics\n"
            "  * Prioritize project and person names\n"
            "  * Prioritize key decisions, action items and tasks\n"
            "  * Avoid duplicate or obviously hierarchical tags\n"
            "  * Tags should match human tagging conventions\n"
            "  * Only output information explicitly mentioned in the content\n"
            "  * If meeting notes: Summarize key decisions, action items and positions, extract participant roles, discussion topics and deadlines\n"
            "  * If interview/dialogue: Summarize core topics, interviewee viewpoints and key quotes, extract topic types, emotional tone and key figures\n"
            "  * If lecture/study: Summarize core knowledge points, examples and knowledge structure, extract subject areas, key concepts and learning methods\n"
        ),
        "custom": "",
        "presets": [
            {"name": "Meeting", "content": "Summarize key decisions, action items, and positions in the meeting. Extract participant roles, discussion topics, and deadlines."},
            {"name": "Interview", "content": "Summarize core topics, interviewee viewpoints, and key quotes. Extract topic types, emotional tone, and key figures."},
            {"name": "Lecture", "content": "Summarize core knowledge points, examples, and knowledge structure. Extract subject areas, key concepts, and learning methods."},
        ],
    },
    "video_summary": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"video_summary": "Comprehensive summary", "tags": ["tag1", "tag2", "tag3"], "search_terms": ["search term1", "search term2"]}\n'
            "search_terms rules (3-8 terms):\n"
            "- Generate from user search perspective, not simple rewrites.\n"
            "- Prioritize generation based on actual video content.\n"
            "- For specific entities, can supplement reasonable broader concepts and common search expressions.\n"
            "- Can supplement search terms highly relevant to the content.\n"
            "- Prioritize terms users may search for in the future.\n"
            "- When speech content contains opinions, jokes, or information inconsistent with the visual, do not generate corresponding search terms.\n"
            "- Do not generate subjective evaluations, emotional expressions or controversial search terms.\n"
            "- Do not generate weakly related terms just to broaden search scope.\n"
            "- Prioritize single-concept terms.\n"
            "- Avoid duplicates, near-synonyms and meaningless expansions.\n"
            "- Do not output complete sentences.\n"
        ),
        "default": ("Output in English.\n"
            "Merge the following two descriptions about the same video into a comprehensive summary within 50 characters.\n"
            "Tag requirements:\n"
            "  * 3-8 most important tags\n"
            "  * Prioritize the core theme and main events of the video\n"
            "  * Prioritize key entities such as people and locations\n"
            "  * Prioritize key actions and behaviors\n"
            "  * Analyze combining visual content and speech content\n"
            "  * Tags should prioritize visually confirmable facts, supplemented by speech information\n"
            "  * When speech content contains opinions, jokes, or information inconsistent with the visual, do not use as tags\n"
            "  * Do not use subjective evaluations, emotional expressions, insulting descriptions or analysis conclusions as tags\n"
            "  * Avoid duplicate or obviously hierarchical tags\n"
            "  * Tags should match human tagging conventions\n"
            "  * Only output content explicitly shown or mentioned in the video, do not speculate\n"
            "  * For educational, interview content, prioritize discussion topics over visual details\n"
        ),
    },
    "video_vision": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"description": "Frame description", "tags": ["tag1", "tag2", "tag3"], "text": "Text content in frame", "search_terms": ["search term1", "search term2"]}\n'
            "If no text is recognized, set text to empty string.\n"
            "search_terms rules (3-8 terms):\n"
            "- Generate from user search perspective.\n"
            "- Prioritize supplementing synonyms and reasonable broader concepts.\n"
            "- Search terms must be highly relevant to video content.\n"
            "- Can combine visual and speech to express the same theme.\n"
            "- Prioritize covering dimensions like topic, usage, etc.\n"
            "- Do not output generic terms or weakly related terms.\n"
            "- Prioritize single-concept terms.\n"
            "- Avoid duplicates and near-synonyms.\n"
            "- Do not output complete sentences.\n"
        ),
        "default": ("Output in English.\n"
            "This is a frame extracted from a video.\n"
            "- description: Describe the video content within 50 characters. Scene, subjects, events, etc.\n"
            "- tags: Identify key elements, text in frame, etc.\n"
            "- Ambiance: Overall atmosphere within 50 characters.\n"
            "Tag requirements:\n"
            "  * 3-8 most important tags\n"
            "  * Prioritize the core theme of the video\n"
            "  * Prioritize key entities such as people and locations\n"
            "  * Prioritize key actions, events or behaviors\n"
            "  * Analyze combining visual and speech content\n"
            "  * Avoid duplicate or obviously hierarchical tags\n"
            "  * Prioritize information most valuable for retrieval\n"
            "  * Only output content explicitly shown or mentioned, do not speculate\n"
            "  * Tags should match human tagging conventions\n"
        ),
    },
    "aggregation_full": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"nodes": [{"name": "Node name", "description": "Brief node description", "asset_ids": [1, 2, 3]}]}\n'
        ),
        "default": ("Output in English.\n"
            "You are an asset library organization expert.\n"
            "Please generate user-friendly topic nodes based on asset content for users to browse.\n"
            "\n"
            "Help users quickly discover, browse, and manage assets.\n"
            "Nodes should be like category folders or collections in an asset library, not academic classifications.\n"
            "Prioritize topics users genuinely care about and want to click to browse.\n"
            "Each node contains:\n"
            "- Node name\n"
            "- One-sentence description of the topic\n"
            "- Assets belonging to this node (by id)\n"
            "Naming principles:\n"
            "- Prioritize using everyday user language.\n"
            "- Prioritize reflecting interests, hobbies, or activities.\n"
            "- Names should be concise and clear, typically within 10 characters.\n"
            "- Node names should feel like category folder or collection names.\n"
            "- Prioritize names users would actively search for or click.\n"
            "- Priority examples: Pet Daily, Cat Collection, Family Dinner, Cooking, Tokyo Trip, Fitness, Work Log, Product Demo, Coffee Shop Visit, Home Office\n"
            "- Avoid: Biological Entities, Behavioral Activities, Outdoor Scenes, Entertainment Content, Visual Objects\n"
            "- Topic identification priority: Interests & Hobbies > Activity Scenes\n"
            "- Do not create nodes based solely on single objects.\n"
            "- Organize into thematic collections: Digital Products, Office Scene, Coffee Time, Product Display\n"
            "Node granularity requirements:\n"
            "- Not too coarse, not too fine (no 'Sleeping Orange Cat' or 'Man Raising Hand').\n"
            "- Organize assets at a topic granularity users would want to click and browse. Prioritize forming thematic collections with real browsing value.\n"
            "Deduplication rules:\n"
            "- Do not generate semantically duplicate or highly similar nodes. Do not generate parent-child relationship nodes simultaneously.\n"
            "- If two nodes express similar topics, prioritize merging. If two nodes share most assets, prioritize merging.\n"
            "- Prioritize keeping the most understandable, specific, and valuable name.\n"
            "- Avoid generating both 'Pets' and 'Pet Daily' — merge into 'Pet Daily'.\n"
            "- Avoid generating both 'Tokyo Trip' and 'Japan Travel' — if most assets are in Tokyo, keep 'Tokyo Trip'.\n"
            "Coverage principles:\n"
            "- One asset can belong to multiple nodes. Cover valuable assets as much as possible.\n"
            "- Scattered assets that can't form clear topics can be ignored. Prioritize forming thematic collections of real user value.\n"
            "Node quality requirements:\n"
            "- Nodes should have clear distinctions from each other. Each node should have a clear theme.\n"
            "- Avoid creating nodes for very few assets. New nodes must have at least 3+ assets. Single-asset nodes are not allowed.\n"
            "- Single assets should preferentially be appended to existing nodes, not create new nodes.\n"
            "- If an asset cannot be categorized into any node, do not create a node just for it — omit it.\n"
            "- If you can only create one node for an asset, and that node would have only this one asset, do not create it.\n"
            "- Avoid generating many similarly-named nodes.\n"
            "Node quantity principles:\n"
            "- Better few and high quality than many mediocre. Do not generate many similar nodes. Prioritize high-value topics, only keep the easiest to understand and use.\n"
            "After generating, self-check: Are there duplicate topics? Are there parent-child duplicate nodes? Are there nodes with heavy asset overlap? Are there hard-to-understand abstract names? If so, merge before outputting.\n"
            "Asset list:\n"
            "{assets}\n"
        ),
    },
    "aggregation_full_append": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"new_nodes": [{"name": "New node name", "description": "node description", "asset_ids": [1, 2, 3]}], "append_to_existing": {"node_id": [1, 2, 3], "other_node_id": [4, 5]}}\n'
        ),
        "default": ("Output in English.\n"
            "You are an asset classification expert. The following aggregation nodes already exist. Please analyze all assets and optimize.\n"
            "Existing nodes:\n"
            "{nodes}\n"
            "You can:\n"
            "- Add new nodes\n"
            "- Append assets to existing nodes\n"
            "Each asset can belong to multiple nodes. Try to cover all assets, but meaningless assets don't need to enter nodes.\n"
            "New node constraints: Avoid creating nodes too similar in meaning to existing nodes. If a new node and existing node express similar topics, append to existing instead of creating new. Prioritize assigning assets to the semantically best-matching existing node. New nodes must have at least 3+ assets. Single-asset nodes are not allowed. Single assets should preferentially be appended to existing nodes. If only one asset cannot fit any existing node, don't create a node just for it — omit it.\n"
            "Naming principles: Use everyday user language. Names should be concise and clear, typically within 10 characters. Node names should feel like category folder or collection names. Avoid single-object nodes — don't create nodes for individual objects. Organize as thematic collections: Digital Products, Office Scene.\n"
            "Deduplication: Do not generate semantically duplicate or highly similar nodes. If two nodes share most assets, prioritize merging. Do not generate parent-child relationship nodes simultaneously.\n"
            "Support both creating new nodes and appending assets to existing nodes.\n"
            "New nodes: new_nodes (don't include existing nodes here). Append to existing: append_to_existing (keys are existing node IDs).\n"
            "If no new nodes are needed, new_nodes can be an empty array. If no appends are needed, append_to_existing can be an empty object.\n"
            "All asset list:\n"
            "{assets}\n"
        ),
    },
    "aggregation_append": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"append_to_existing": {"existing_node_id": [1, 2, 3]}}\n'
        ),
        "default": ("Output in English.\n"
            "You are an asset classification expert. The following aggregation nodes already exist. Please assign new assets to the appropriate existing nodes.\n"
            "Existing nodes:\n"
            "{nodes}\n"
            "Each asset can belong to multiple nodes. Try to cover all assets, but meaningless assets don't need to enter nodes.\n"
            "New asset list:\n"
            "{assets}\n"
        ),
    },
    "aggregation_analyze_append": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"asset_ids": [1, 2, 3]}\n'
        ),
        "default": ("Output in English.\n"
            "Node name: {node_name}\n"
            "Node description: {node_description}\n"
            "The node currently contains {existing_count} assets with the following characteristics:\n"
            "{existing_assets}\n"
            "There are {candidate_count} candidate assets below. Please identify which ones should be added to this node:\n"
            "{candidates}\n"
        ),
    },
    "search_ai": {
        "system_format": (
            "Output strictly in JSON format (only JSON, no other text):\n"
            '{"asset_ids": [1, 2, 3]}\n'
            'If no matching assets, output: {"asset_ids": []}\n'
        ),
        "default": ("Output in English.\n"
            "You are an asset search assistant. Below is a list of assets:\n"
            "Format per line: [id] filename - analysis description\n"
            "{assets}\n"
            "User's search intent is: {query}\n"
            "Please return IDs of assets that are STRICTLY RELEVANT.\n"
            "Only return when asset content is clearly related to the user query.\n"
            "If uncertain about relevance, do not return. Better to miss than include irrelevant results.\n"
            "Sort by relevance from highest to lowest.\n"
        ),
    },
}


DEFAULT_PROMPTS_ZH
DEFAULT_PROMPTS_EN

def get_default_prompts(language: str = 'zh'):
    """Get default prompts for the given language."""
    return DEFAULT_PROMPTS_ZH if language == 'zh' else DEFAULT_PROMPTS_EN


_current_language: str = "zh"

def get_current_language() -> str:
    return _current_language

def set_current_language(lang: str) -> None:
    global _current_language
    _current_language = lang

class PromptConfig:
    """Manages AI prompt configuration stored in YAML."""

    def __init__(self, config_dir: str, language: str = "zh"):
        self.language = language
        self.config_dir = config_dir
        self._file = os.path.join(config_dir, "prompts.yaml")
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._file):
            with open(self._file, "r") as f:
                data = yaml.safe_load(f) or {}
        else:
            self._ensure_prompts_yaml()
            data = dict(get_default_prompts(self.language))
        # Merge missing fields from DEFAULT_PROMPTS (for upgrades)
        for key in get_default_prompts(self.language):
            if key not in data:
                data[key] = dict(get_default_prompts(self.language)[key])
            # Always sync system_format and presets from code
            data[key]["system_format"] = get_default_prompts(self.language)[key]["system_format"]
            if "presets" in get_default_prompts(self.language)[key]:
                data[key]["presets"] = get_default_prompts(self.language)[key]["presets"]
        return data

    def _ensure_prompts_yaml(self) -> None:
        os.makedirs(self.config_dir, exist_ok=True)
        with open(self._file, "w") as f:
            yaml.dump(get_default_prompts(self.language), f, allow_unicode=True, sort_keys=False)

    def get_prompt(self, task_type: str, language: str = "") -> str:
        if not language:
            language = self.language
        section = self._data.get(task_type, {})
        custom = section.get("custom", "")
        if custom:
            base = custom
        else:
            # Use language-specific default if provided, else from loaded data
            if language:
                defaults = get_default_prompts(language)
                base = defaults.get(task_type, {}).get("default", "")
                fmt = defaults.get(task_type, {}).get("system_format", "")
            else:
                base = section.get("default", "")
                fmt = section.get("system_format", "")
        if fmt:
            return f"{base}\n\n{fmt}"
        return base

    def get_all(self) -> dict:
        """Return all prompts with language-specific defaults."""
        result = dict(self._data)
        defaults = get_default_prompts(self.language)
        for key in defaults:
            if key not in result:
                result[key] = dict(defaults[key])
            else:
                result[key]["default"] = defaults[key].get("default", "")
                result[key]["system_format"] = defaults[key].get("system_format", "")
        return result

    def save(self, task_type: str, custom_prompt: str) -> None:
        self._data.setdefault(task_type, {})["custom"] = custom_prompt
        with open(self._file, "w") as f:
            yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)

    def reset(self, task_type: str) -> None:
        self._data.setdefault(task_type, {})["custom"] = DEFAULT_PROMPTS[task_type].get("custom", "")
        with open(self._file, "w") as f:
            yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)
