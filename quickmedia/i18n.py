"""Server-side i18n for API messages."""

from quickmedia.prompt_config import get_current_language

_SERVER_MSG = {
    "scan_dir": {"zh": "已扫描目录 {}，新增 {} 个素材", "en": "Scanned directory {}, {} new assets"},
    "add_asset": {"zh": "已添加 {}", "en": "Added {}"},
    "save_paths": {"zh": "已保存 {} 条路径", "en": "Saved {} paths"},
    "reset_retry": {"zh": "已重置待重试", "en": "Retry queue reset"},
    "reenqueue": {"zh": "已重新入队分析任务", "en": "Re-enqueued analysis tasks"},
    "reenqueue_batch": {"zh": "已重新入队 {} 个素材", "en": "Re-enqueued {} assets"},
    "scan_new": {"zh": "新增 {} 个素材", "en": "{} new assets"},
    "semantic_failed": {"zh": "语义搜索失败（{}: {}）", "en": "Semantic search failed ({}: {})"},
    "macos_only": {"zh": "仅支持 macOS", "en": "macOS only"},
    "file_not_found": {"zh": "文件不存在: {}", "en": "File not found: {}"},
    "dir_not_found": {"zh": "文件夹不存在: {}", "en": "Directory not found: {}"},
}

def server_msg(key: str, *args) -> str:
    """Return a localized message string by key and format args."""
    lang = get_current_language()
    messages = _SERVER_MSG.get(key, {})
    tmpl = messages.get(lang) or messages.get("en", key)
    return tmpl.format(*args)
