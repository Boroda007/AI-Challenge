import os
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from dotenv import load_dotenv
import markdown

# Загружаем .env из текущей папки
current_dir = Path(__file__).resolve().parent
dotenv_path = current_dir / ".env"

load_dotenv(dotenv_path=dotenv_path)

# Извлечение переменных окружения
BASE_URL: str = os.getenv("BASE_URL") or ""
API_KEY: str = os.getenv("API_KEY") or ""
MODEL_NAME: str = os.getenv("MODEL_NAME") or ""

if not BASE_URL:
    raise ValueError("❌ Критическая ошибка: Переменная BASE_URL не задана в .env или консоли!")
if not MODEL_NAME:
    raise ValueError("❌ Критическая ошибка: Переменная MODEL_NAME не задана в .env или консоли!")
if not API_KEY:
    raise ValueError("❌ Критическая ошибка: Переменная API_KEY не задана в .env или консоли!")

# Инициализация FastAPI и клиента OpenAI
app = FastAPI()
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# Pydantic-схема входных данных
class ChatRequest(BaseModel):
    message: str
    free_history: list[ChatCompletionMessageParam] = []
    controlled_history: list[ChatCompletionMessageParam] = []
    constraints: dict = {}


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )


def call_free(history: list[ChatCompletionMessageParam], message: str) -> dict:
    """Свободный вызов — стандартные параметры, без системного промпта."""
    messages: list[ChatCompletionMessageParam] = history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    choice = response.choices[0]
    return {
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
    messages: list[ChatCompletionMessageParam] = []

    # Добавляем системный промпт первым сообщением, если задан
    system_prompt = constraints.get("system_prompt")
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.extend(history + [{"role": "user", "content": message}])

    # Собираем параметры API только из не-None значений
    api_params: dict = {
        "model": MODEL_NAME,
        "messages": messages,
    }

    mapping = {
        "max_tokens": "max_tokens",
        "temperature": "temperature",
        "stop": "stop",
        "response_format": "response_format",
    }

    for key, param_name in mapping.items():
        value = constraints.get(key)
        if value is not None:
            api_params[param_name] = value

    response = client.chat.completions.create(**api_params)

    choice = response.choices[0]

    # Собираем информацию о применённых параметрах
    applied_params = {}
    if constraints.get("max_tokens") is not None:
        applied_params["Длина"] = constraints["max_tokens"]
    if constraints.get("temperature") is not None:
        applied_params["Температура"] = constraints["temperature"]
    if constraints.get("stop") is not None:
        applied_params["Стоп-символ"] = constraints["stop"]
    if constraints.get("response_format") is not None:
        fmt = constraints["response_format"]
        applied_params["Формат"] = fmt.get("type", fmt) if isinstance(fmt, dict) else fmt
    if constraints.get("system_prompt") is not None:
        prompt = constraints["system_prompt"]
        applied_params["Системный промпт"] = prompt[:30] + "..." if len(prompt) > 30 else prompt

    return {
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "applied_params": applied_params,
        "usage": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        } if response.usage else None,
    }


@app.get("/")
async def home():
    html_path = current_dir / "templates" / "index.html"
    return FileResponse(html_path)


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        # Параллельные вызовы через asyncio.to_thread (синхронный OpenAI-клиент)
        free_result, controlled_result = await asyncio.gather(
            asyncio.to_thread(call_free, req.free_history, req.message),
            asyncio.to_thread(call_controlled, req.controlled_history, req.message, req.constraints),
        )

        return JSONResponse({
            "free_response": {
                "content": render_markdown(free_result["content"]),
                "usage": free_result["usage"],
            },
            "controlled_response": {
                "content": render_markdown(controlled_result["content"]),
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


# Статические файлы (CSS, JS) из папки templates
app.mount("/", StaticFiles(directory=current_dir / "templates"), name="static")


# Точка входа
if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Инициализация ИИ-сервера...")
    print(f"🔗 Эндпоинт API: {BASE_URL}")
    print(f"🤖 Используемая модель: {MODEL_NAME}")

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
