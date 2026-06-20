"""Provider registry for multi-model AI configuration."""

import yaml


class ProviderRegistry:
    """Manages AI model providers and task-to-model bindings."""

    def __init__(self, config, models_path: str):
        self._config = config
        self._models = {}
        if models_path:
            with open(models_path, "r") as f:
                self._models = yaml.safe_load(f) or {}

    def get_provider(self, name: str) -> dict | None:
        """Return provider config {url} or None."""
        # Check user config first, fall back to built-in models.yaml URL
        providers = self._config.get("providers") or {}
        if name in providers:
            return providers[name]
        # Fall back to built-in URL from models.yaml
        section = self._models.get(name, {})
        if isinstance(section, dict) and "url" in section:
            return {"url": section["url"]}
        return None

    def get_models(self, provider_name: str, capability: str = None) -> list[dict]:
        """Return models for a provider, optionally filtered by capability."""
        section = self._models.get(provider_name, {})
        models = section.get("models", []) if isinstance(section, dict) else []
        if capability:
            models = [m for m in models if capability in m.get("capabilities", [])]
        return models

    def get_task_binding(self, task_type: str) -> dict | None:
        """Return {provider, model} for a task type."""
        task_models = self._config.get("task_models") or {}
        return task_models.get(task_type)

    def get_provider_url(self, provider_name: str) -> str | None:
        """Return the URL for a provider from user config or built-in models.yaml."""
        providers = self._config.get("providers") or {}
        if provider_name in providers:
            return providers[provider_name].get("url")
        # Fall back to models.yaml
        section = (self._models or {}).get(provider_name)
        if isinstance(section, dict):
            return section.get("url")
        return None
