"""AI prompt configuration management for QuickMedia.

Loads and manages prompt templates from ~/.asset-manager/prompts.yaml.
"""

import os
import yaml

DEFAULT_PROMPTS = {
    "vision": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"description": "图片描述", "tags": ["标签1", "标签2", "标签3"], "text": "画面中文字内容"}\n'
            "如果没有识别到文字，text 为空字符串。"
        ),
        "default": (
            "请分析图片\n"
            "1. 使用50字以内描述图片内容、整体场景、事件等\n"
            "2. 识别包含的关键元素、画面中文字等，提取最多10个最重要的标签\n\n"
            "标签的内容要求：\n"
            "- 优先保留完整事物，不要拆分组成部分。\n"
            "- 不要输出重复或包含关系标签。例如：食物、美食等相关性过高的词\n"
            "- 优先输出主体和场景。\n"
            "- 忽略细节、装饰和设计类标签。\n"
            "- 标签应符合人工打标习惯。"
        ),
        "custom": "",
        "presets": [
            {"name": "摄影", "content": (
                "请分析这张照片的构图方式（三分法/中心/对称等）、光线方向与强度、"
                "色彩搭配和景深效果。提取画面中的摄影元素和视觉焦点。"
            )},
            {"name": "设计", "content": (
                "请分析这张图片的版式布局、色彩方案、字体风格和设计风格"
                "（极简/扁平/复古等）。识别 UI 组件、图标和交互元素。"
            )},
            {"name": "宠物", "content": (
                "请描述图片中宠物的品种、毛色、体态和数量。"
                "描述宠物所在环境和行为状态。"
            )},
            {"name": "人物", "content": (
                "请描述图片中人物的性别、大致年龄、表情、穿着风格和姿态。"
                "识别配饰、妆容特征等视觉元素以及任何可识别的文本内容。"
            )},
        ],
    },
    "text": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"summary": "文档摘要", "tags": ["标签1", "标签2", "标签3"]}'
        ),
        "default": (
            "总结以下文档内容（200字以内），并提取5-10个主题关键词。\n\n"
            "标签示例：\n"
            "1. 技术栈（如：Python、React）\n"
            "2. 核心概念（如：状态管理、路由）\n"
            "3. 领域关键词\n"
            "4. ..."
        ),
        "custom": "",
        "presets": [
            {"name": "技术文档", "content": (
                "总结文档涉及的技术栈、架构设计和核心实现方案。"
                "提取关键的技术名词、框架名称和编程概念。"
            )},
            {"name": "笔记日记", "content": (
                "总结笔记中记录的个人思考、关键决定和待办事项。"
                "提取情绪关键词、涉及的人物和事件类型。"
            )},
            {"name": "学习总结", "content": (
                "总结文档中的核心知识点、关键概念定义和知识点之间的关联。"
                "提取学科领域、主题词和专业术语。"
            )},
        ],
    },
    "speech": {
        "system_format": (
            "请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：\n"
            '{"summary": "语音摘要", "tags": ["标签1", "标签2", "标签3"]}'
        ),
        "default": (
            "以下是一段语音转录文本。请总结这段语音的主要内容（150字以内），"
            "并提取5-10个主题关键词。\n\n"
            "标签示例：\n"
            "1. 核心话题（如：项目规划）\n"
            "2. 关键人物或角色\n"
            "3. 决定或行动项\n"
            "4. ..."
        ),
        "custom": "",
        "presets": [
            {"name": "会议记录", "content": (
                "总结会议中的关键决定、行动项和各方立场。"
                "提取参与人角色、讨论议题和截止时间。"
            )},
            {"name": "采访对话", "content": (
                "总结采访的核心话题、受访者观点和关键引用。"
                "提取话题类型、情绪基调和关键人物。"
            )},
            {"name": "学习总结", "content": (
                "总结讲解的核心知识点、举例说明和知识结构。"
                "提取学科领域、关键概念和学习方法。"
            )},
        ],
    },
    "video_summary": {
        "system_format": "",
        "default": (
            "请将以下两段关于同一视频的描述融合为一段综合总结（200字以内）："
        ),
        "custom": "",
        "presets": [],
    },
}


class PromptConfig:
    """Load and manage AI prompt configuration."""

    def __init__(self, config_dir: str):
        self._path = os.path.join(config_dir, "prompts.yaml")
        self._ensure_defaults()

    def _ensure_defaults(self):
        """Create or update prompts.yaml, preserving user custom values."""
        if not os.path.isfile(self._path):
            self._write_defaults()
            return
        # Update system-managed fields, preserve custom
        data = self._load()
        for key, default_section in DEFAULT_PROMPTS.items():
            if key not in data:
                data[key] = dict(default_section)
            else:
                data[key]["default"] = default_section["default"]
                data[key]["system_format"] = default_section["system_format"]
                data[key]["presets"] = default_section["presets"]
                data[key].setdefault("custom", "")
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def _write_defaults(self):
        """Write the default prompt configuration to disk."""
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_PROMPTS, f, allow_unicode=True, sort_keys=False)

    def _load(self) -> dict:
        """Load the current configuration from disk."""
        with open(self._path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_config(self) -> dict:
        """Return the full prompt configuration."""
        return self._load()

    def get_prompt(self, analysis_type: str) -> str:
        """Return the effective prompt for an analysis type.
        Priority: custom (if non-empty) > default.
        Always appends system_format if present."""
        data = self._load()
        section = data.get(analysis_type, {})
        base = section.get("custom", "").strip()
        if not base:
            base = section.get("default", "")
        fmt = section.get("system_format", "")
        if fmt:
            return base + "\n\n" + fmt
        return base

    def update_custom(self, analysis_type: str, custom: str):
        """Update the custom prompt for an analysis type."""
        data = self._load()
        if analysis_type in data:
            data[analysis_type]["custom"] = custom
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
