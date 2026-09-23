import asyncio

import markdown
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import BadRequestError, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

import state
from routers.models import router as models_router
from routers.providers import router as providers_router
from state import _get_client, _get_model_name, current_dir

# ── Инициализация ───────────────────────────────────────────────────────────
app = FastAPI()

state._load_providers_config()
state._resolve_active_model()

app.include_router(providers_router)
app.include_router(models_router)


# ── Pydantic-схемы ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    free_history: list[ChatCompletionMessageParam] = []
    controlled_history: list[ChatCompletionMessageParam] = []
    constraints: dict = {}
    include_free: bool = True


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
    messages: list[ChatCompletionMessageParam] = history + [
        {"role": "user", "content": message}
    ]
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
        }
        if response.usage
        else None,
    }


def call_controlled(
    history: list[ChatCompletionMessageParam], message: str, constraints: dict
) -> dict:
    """Контролируемый вызов — с системным промптом и параметрами из constraints."""
    client = _get_client()
    model = _get_model_name()
    messages: list[ChatCompletionMessageParam] = list(history) + [
        {"role": "user", "content": message}
    ]

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

    for attempt in range(len(retry_params) + 1):
        try:
            response = client.chat.completions.create(**api_params)
            break
        except BadRequestError as e:
            error_msg = str(e).lower()
            for param in retry_params:
                if param in api_params and param in error_msg:
                    del api_params[param]
                    dropped_params.append(param)
                    break
            else:
                raise  # ошибка не связана с retry-параметрами — пробрасываем
            if attempt == len(retry_params):
                raise  # ретраи исчерпаны

    if response is None:  # недостижимо, но нужно для статического анализа
        raise RuntimeError(
            f"Запрос не удался после сброса параметров: {', '.join(dropped_params)}"
        )

    choice = response.choices[0]

    # Собираем информацию о применённых параметрах
    applied_params = {}
    if constraints.get("max_tokens") is not None:
        applied_params["Длина"] = constraints["max_tokens"]
    if constraints.get("temperature") is not None:
        applied_params["Температура"] = constraints["temperature"]
    if constraints.get("stop") is not None:
        applied_params["Стоп-символ"] = constraints["stop"]
    if (
        constraints.get("response_format") is not None
        and "response_format" not in dropped_params
    ):
        fmt = constraints["response_format"]
        applied_params["Формат"] = (
            fmt.get("type", fmt) if isinstance(fmt, dict) else fmt
        )
    if (
        constraints.get("reasoning_effort") is not None
        and "reasoning_effort" not in dropped_params
    ):
        applied_params["Reasoning"] = constraints["reasoning_effort"]
    if dropped_params:
        applied_params["⚠ Сброшен"] = ", ".join(dropped_params)

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
        }
        if response.usage
        else None,
    }


# ── API-эндпоинты ───────────────────────────────────────────────────────────
@app.get("/")
async def home():
    html_path = current_dir / "templates" / "index.html"
    return FileResponse(html_path)


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        if req.include_free:
            free_result, controlled_result = await asyncio.gather(
                asyncio.to_thread(call_free, req.free_history, req.message),
                asyncio.to_thread(
                    call_controlled,
                    req.controlled_history,
                    req.message,
                    req.constraints,
                ),
            )
            free_response = {
                "raw": free_result["raw"],
                "raw_request": free_result.get("request_payload"),
                "content": render_markdown(free_result["content"]),
                "raw_content": free_result["content"],
                "usage": free_result["usage"],
            }
        else:
            controlled_result = await asyncio.to_thread(
                call_controlled, req.controlled_history, req.message, req.constraints
            )
            free_response = None

        return JSONResponse(
            {
                "free_response": free_response,
                "controlled_response": {
                    "raw": controlled_result["raw"],
                    "raw_request": controlled_result.get("request_payload"),
                    "content": render_markdown(controlled_result["content"]),
                    "raw_content": controlled_result["content"],
                    "finish_reason": (
                        controlled_result["finish_reason"]
                        if req.constraints
                        and (
                            req.constraints.get("stop")
                            or controlled_result["finish_reason"] != "stop"
                        )
                        else None
                    ),
                    "applied_params": controlled_result["applied_params"]
                    if req.constraints
                    else {},
                    "usage": controlled_result["usage"],
                },
            }
        )

    except (OpenAIError, RuntimeError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Статика ─────────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=current_dir / "templates"), name="static")


# ── Точка входа ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("🚀 Инициализация ИИ-сервера...")
    print(f"🔗 Эндпоинт API: {state._active_provider} / {state._active_model}")
    print(f"🤖 Модель: {state._active_model_config.get('name', state._active_model)}")

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
