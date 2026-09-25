import json
from pathlib import Path
from typing import Any, TypedDict

from openai import OpenAI


# ── Типы конфигурации ───────────────────────────────────────────────────────
class ParameterRange(TypedDict, total=False):
    """Диапазон числового параметра модели."""

    min: int | float
    max: int | float
    default: int | float


class ModelConfigBase(TypedDict):
    """Обязательные поля модели."""

    id: str
    name: str


class ModelConfig(ModelConfigBase, total=False):
    """Конфигурация одной модели провайдера."""

    reasoning_effort: str
    temperature: ParameterRange
    max_tokens: ParameterRange


class ProviderConfigBase(TypedDict):
    """Обязательные поля провайдера."""

    name: str
    base_url: str


class ProviderConfig(ProviderConfigBase, total=False):
    """Конфигурация провайдера из providers.json."""

    api_key: str
    models: list[ModelConfig]


ProvidersConfig = dict[str, ProviderConfig]
RawConfig = dict[str, Any]


# ── Состояние ───────────────────────────────────────────────────────────────
class State:
    """Конфигурация провайдеров и активная модель."""

    def __init__(self) -> None:
        self._config_path: Path | None = None
        self._active_provider: str = ""
        self._active_model_config: ModelConfig | None = None
        self._client: OpenAI | None = None
        # Полный JSON из providers.json (включая active_provider, active_model)
        self._raw_config: RawConfig = {}

    # ── Внутренние методы ────────────────────────────────────────────────────
    def _path(self) -> Path:
        """Путь к providers.json (по умолчанию — рядом со скриптом)."""
        return self._config_path or self.get_project_dir() / "providers.json"

    def _load(self) -> None:
        """Загрузка providers.json."""
        config_path = self._path()
        if not config_path.exists():
            raise FileNotFoundError(f"❌ Файл конфигурации не найден: {config_path}")

        with open(config_path, encoding="utf-8") as f:
            self._raw_config = json.load(f)

    def _providers(self) -> ProvidersConfig:
        """Провайдеры из загруженного конфига."""
        return self._raw_config.get("providers", {})

    def _save(self) -> None:
        """Сохранение providers.json (для смены active_provider / active_model)."""
        self._raw_config["active_provider"] = self._active_provider
        self._raw_config["active_model"] = (self._active_model_config or {}).get("id", "")

        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(self._raw_config, f, indent=2, ensure_ascii=False)

    def _model_and_client(self, provider: str, model: str) -> tuple[ModelConfig, OpenAI]:
        """Проверка провайдера/модели, поиск конфига модели и создание клиента."""
        providers = self._providers()
        if provider not in providers:
            raise ValueError(f"❌ Провайдер '{provider}' не найден в providers.json")

        provider_cfg = providers[provider]
        if not provider_cfg.get("base_url", ""):
            raise ValueError(f"❌ base_url не задан для провайдера '{provider}'")

        for m in provider_cfg.get("models", []):
            if m["id"] == model:
                client = OpenAI(
                    base_url=provider_cfg["base_url"],
                    api_key=provider_cfg.get("api_key", "") or "none",
                )
                return m, client

        raise ValueError(f"❌ Модель '{model}' не найдена у провайдера '{provider}'")

    def _resolve(self) -> None:
        """Определение активной модели из конфига и создание OpenAI-клиента."""
        self._active_provider = self._raw_config.get("active_provider", "")
        self._active_model_config, self._client = self._model_and_client(
            self._active_provider, self._raw_config.get("active_model", "")
        )

    # ── Публичный API ────────────────────────────────────────────────────────
    def init(self, config_path: Path | None = None) -> None:
        """Загрузка конфигурации и создание клиента активной модели."""
        self._config_path = config_path
        self._load()
        self._resolve()

    def get_project_dir(self) -> Path:
        """Корень проекта (директория, где лежат providers.json и templates/)."""
        return Path(__file__).resolve().parent

    def get_providers_config(self) -> ProvidersConfig:
        """Все провайдеры из providers.json (ключ — id провайдера)."""
        return self._providers()

    def get_active_provider(self) -> str:
        """Id активного провайдера."""
        return self._active_provider

    def get_active_model(self) -> str:
        """Id активной модели."""
        return self._active_model_config["id"] if self._active_model_config else ""

    def get_active_model_config(self) -> ModelConfig:
        """Конфигурация активной модели.

        Бросает RuntimeError, если состояние не инициализировано через init().
        """
        if self._active_model_config is None:
            raise RuntimeError("❌ Модель не инициализирована")
        return self._active_model_config

    def get_client(self) -> OpenAI:
        """Готовый OpenAI-клиент активной модели.

        Бросает RuntimeError, если состояние не инициализировано через init().
        """
        if self._client is None:
            raise RuntimeError("❌ OpenAI-клиент не инициализирован")
        return self._client

    def switch_model(self, provider: str, model: str) -> None:
        """Смена активного провайдера/модели без перезапуска сервера.

        Сохраняет выбор в providers.json и пересоздаёт OpenAI-клиент.
        Бросает ValueError, если провайдер или модель не найдены.
        """
        self._active_model_config, self._client = self._model_and_client(provider, model)
        self._active_provider = provider
        self._save()


state = State()
