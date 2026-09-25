import logging
from typing import Any

from openai import BadRequestError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

import state

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatCompletionMessageParam] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


def call_controlled(
    history: list[ChatCompletionMessageParam], message: str, constraints: dict[str, Any]
) -> dict[str, Any]:
    """Контролируемый вызов — с системным промптом и параметрами из constraints."""
    client = state._get_client()
    model = state._get_model_name()
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


def render_markdown(text: str) -> str:
    import markdown

    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )
