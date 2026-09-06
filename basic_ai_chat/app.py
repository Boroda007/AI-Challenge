import json
import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI, BadRequestError
from openai.types.chat import ChatCompletionMessageParam
import markdown

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
        raise ValueError(f"❌ Провайдер '{_active_provider}' не найден в providers.json")

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
        raise ValueError(f"❌ Модель '{_active_model}' не найдена у провайдера '{_active_provider}'")

    _client = OpenAI(base_url=base_url, api_key=api_key or "none")


def _get_client() -> OpenAI:
    if _client is None:
        raise RuntimeError("❌ OpenAI-клиент не инициализирован")
    return _client


def _get_model_name() -> str:
    return _active_model


# ── Инициализация ───────────────────────────────────────────────────────────
app = FastAPI()

_load_providers_config()
_resolve_active_model()

# Хранилище системного промпта
_current_system_prompt: str = ""


# ── Pydantic-схемы ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    free_history: list[ChatCompletionMessageParam] = []
    controlled_history: list[ChatCompletionMessageParam] = []
    constraints: dict = {}


class SystemPromptRequest(BaseModel):
    prompt: str


class SwitchModelRequest(BaseModel):
    provider: str
    model: str


# ── Утилиты ─────────────────────────────────────────────────────────────────
def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )


# ── LLM-вызовы ──────────────────────────────────────────────────────────────
def call_free(history: list[ChatCompletionMessageParam], message: str) -> dict:
    """Свободный вызов — стандартные параметры, без системного промпта."""
    client = _get_client()
    model = _get_model_name()
    messages: list[ChatCompletionMessageParam] = history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(model=model, messages=messages)
    choice = response.choices[0]
    return {
        "raw": response.model_dump(),
        "request_payload": {"model": model, "messages": messages},
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "usage": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        } if response.usage else None,
    }


def call_controlled(history: list[ChatCompletionMessageParam], message: str, constraints: dict) -> dict:
    """Контролируемый вызов — с системным промптом и параметрами из constraints."""
    client = _get_client()
    model = _get_model_name()
    messages: list[ChatCompletionMessageParam] = []

    if _current_system_prompt:
        messages.append({"role": "system", "content": _current_system_prompt})

    messages.extend(history + [{"role": "user", "content": message}])

    # Собираем параметры API — только из constraints, без хардкода
    api_params: dict = {
        "model": model,
        "messages": messages,
    }

    mapping = {
        "max_tokens": "max_tokens",
        "temperature": "temperature",
        "stop": "stop",
        "response_format": "response_format",
        "reasoning_effort": "reasoning_effort",
    }

    for key, param_name in mapping.items():
        value = constraints.get(key)
        if value is not None:
            api_params[param_name] = value

    # Параметры, которые могут быть отклонены API (в порядке приоритета)
    retry_params = ["reasoning_effort", "response_format"]
    dropped_params = []

    response = None
    last_error = None

    for attempt in range(len(retry_params) + 1):
        try:
            response = client.chat.completions.create(**api_params)
            break
        except BadRequestError as e:
            last_error = e
            error_msg = str(e).lower()
            removed = False
            for param in retry_params:
                if param in api_params and param in error_msg:
                    del api_params[param]
                    dropped_params.append(param)
                    removed = True
                    break
            if not removed:
                raise

    if response is None:
        raise last_error

    choice = response.choices[0]

    # Собираем информацию о применённых параметрах
    applied_params = {}
    if constraints.get("max_tokens") is not None:
        applied_params["Длина"] = constraints["max_tokens"]
    if constraints.get("temperature") is not None:
        applied_params["Температура"] = constraints["temperature"]
    if constraints.get("stop") is not None:
        applied_params["Стоп-символ"] = constraints["stop"]
    if constraints.get("response_format") is not None and "response_format" not in dropped_params:
        fmt = constraints["response_format"]
        applied_params["Формат"] = fmt.get("type", fmt) if isinstance(fmt, dict) else fmt
    if constraints.get("reasoning_effort") is not None and "reasoning_effort" not in dropped_params:
        applied_params["Reasoning"] = constraints["reasoning_effort"]
    if dropped_params:
        applied_params["⚠ Сброшен"] = ", ".join(dropped_params)
    if _current_system_prompt:
        applied_params["Системный промпт"] = _current_system_prompt[:30] + "..." if len(_current_system_prompt) > 30 else _current_system_prompt

    return {
        "raw": response.model_dump(),
        "request_payload": api_params,
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "applied_params": applied_params,
        "usage": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        } if response.usage else None,
    }


# ── API-эндпоинты ───────────────────────────────────────────────────────────
@app.get("/")
async def home():
    html_path = current_dir / "templates" / "index.html"
    return FileResponse(html_path)


@app.get("/api/providers")
async def get_providers():
    """Список всех провайдеров и моделей из providers.json."""
    result = {}
    for provider_id, provider in _providers_config.items():
        result[provider_id] = {
            "name": provider.get("name", provider_id),
            "base_url": provider.get("base_url", ""),
            "models": [
                {"id": m["id"], "name": m.get("name", m["id"])}
                for m in provider.get("models", [])
            ],
        }
    return JSONResponse({"providers": result, "active_provider": _active_provider, "active_model": _active_model})


@app.get("/api/supported-values")
async def get_supported_values():
    """Capabilities активной модели из providers.json."""
    return JSONResponse({
        "reasoning_effort": _active_model_config.get("reasoning_effort", []),
        "temperature": _active_model_config.get("temperature", {}),
        "max_tokens": _active_model_config.get("max_tokens", {}),
    })


@app.post("/api/switch-model")
async def switch_model(req: SwitchModelRequest):
    """Смена провайдера/модели без перезапуска сервера."""
    global _active_provider, _active_model, _active_model_config, _client

    if req.provider not in _providers_config:
        return JSONResponse({"error": f"Провайдер '{req.provider}' не найден"}, status_code=400)

    provider = _providers_config[req.provider]
    model_config = None
    for m in provider.get("models", []):
        if m["id"] == req.model:
            model_config = m
            break

    if model_config is None:
        return JSONResponse({"error": f"Модель '{req.model}' не найдена у провайдера '{req.provider}'"}, status_code=400)

    _active_provider = req.provider
    _active_model = req.model
    _active_model_config = model_config
    _client = OpenAI(base_url=provider["base_url"], api_key=provider.get("api_key", "") or "none")

    _save_providers_config()

    return JSONResponse({
        "provider": _active_provider,
        "model": _active_model,
        "supported_values": {
            "reasoning_effort": _active_model_config.get("reasoning_effort", []),
            "temperature": _active_model_config.get("temperature", {}),
            "max_tokens": _active_model_config.get("max_tokens", {}),
        },
    })


@app.post("/api/system-prompt")
async def set_system_prompt(req: SystemPromptRequest):
    global _current_system_prompt
    _current_system_prompt = req.prompt
    return JSONResponse({
        "model": _get_model_name(),
        "messages": [{"role": "system", "content": _current_system_prompt}],
    })


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        free_result, controlled_result = await asyncio.gather(
            asyncio.to_thread(call_free, req.free_history, req.message),
            asyncio.to_thread(call_controlled, req.controlled_history, req.message, req.constraints),
        )

        return JSONResponse({
            "free_response": {
                "raw": free_result["raw"],
                "raw_request": free_result.get("request_payload"),
                "content": render_markdown(free_result["content"]),
                "raw_content": free_result["content"],
                "usage": free_result["usage"],
            },
            "controlled_response": {
                "raw": controlled_result["raw"],
                "raw_request": controlled_result.get("request_payload"),
                "content": render_markdown(controlled_result["content"]),
                "raw_content": controlled_result["content"],
                "finish_reason": (
                    controlled_result["finish_reason"]
                    if req.constraints and (req.constraints.get("stop") or controlled_result["finish_reason"] != "stop")
                    else None
                ),
                "applied_params": controlled_result["applied_params"] if req.constraints else {},
                "usage": controlled_result["usage"],
            },
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Статика ─────────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=current_dir / "templates"), name="static")


# ── Точка входа ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Инициализация ИИ-сервера...")
    print(f"🔗 Эндпоинт API: {_active_provider} / {_active_model}")
    print(f"🤖 Модель: {_active_model_config.get('name', _active_model)}")

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
