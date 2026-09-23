import json
from pathlib import Path

from openai import OpenAI

# Директория скрипта
current_dir = Path(__file__).resolve().parent

# ── Конфигурация провайдеров ────────────────────────────────────────────────
_providers_config: dict = {}
_active_provider: str = ""
_active_model: str = ""
_active_model_config: dict = {}
_client: OpenAI | None = None
_raw_config: dict = {}  # Полный JSON из providers.json (включая active_provider, active_model)


def _load_providers_config() -> None:
    """Загрузка providers.json из директории скрипта."""
    global _providers_config, _raw_config
    config_path = current_dir / "providers.json"
    if not config_path.exists():
        raise FileNotFoundError(f"❌ Файл конфигурации не найден: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        _raw_config = json.load(f)
    _providers_config = _raw_config.get("providers", {})


def _save_providers_config() -> None:
    """Сохранение providers.json (для смены active_provider / active_model)."""
    config_path = current_dir / "providers.json"
    _raw_config["active_provider"] = _active_provider
    _raw_config["active_model"] = _active_model
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(_raw_config, f, indent=2, ensure_ascii=False)


def _resolve_active_model() -> None:
    """Определение активной модели из конфига и создание OpenAI-клиента."""
    global _active_provider, _active_model, _active_model_config, _client

    _active_provider = _raw_config.get("active_provider", "")
    _active_model = _raw_config.get("active_model", "")

    if _active_provider not in _providers_config:
        raise ValueError(
            f"❌ Провайдер '{_active_provider}' не найден в providers.json"
        )

    provider = _providers_config[_active_provider]
    base_url = provider.get("base_url", "")
    api_key = provider.get("api_key", "")

    if not base_url:
        raise ValueError(f"❌ base_url не задан для провайдера '{_active_provider}'")

    _active_model_config = {}
    for m in provider.get("models", []):
        if m["id"] == _active_model:
            _active_model_config = m
            break

    if not _active_model_config:
        raise ValueError(
            f"❌ Модель '{_active_model}' не найдена у провайдера '{_active_provider}'"
        )

    _client = OpenAI(base_url=base_url, api_key=api_key or "none")


def _get_client() -> OpenAI:
    if _client is None:
        raise RuntimeError("❌ OpenAI-клиент не инициализирован")
    return _client


def _get_model_name() -> str:
    return _active_model
