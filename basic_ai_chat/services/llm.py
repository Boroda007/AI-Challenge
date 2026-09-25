import logging
from typing import Any

from openai import BadRequestError
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from state import state

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatCompletionMessageParam] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


# Ограничения UI -> параметры API
PARAM_MAPPING = {
    "max_tokens": "max_tokens",
    "temperature": "temperature",
    "stop": "stop",
    "response_format": "response_format",
    "reasoning_effort": "reasoning_effort",
}

# Параметры, которые API может отклонить (в порядке приоритета сброса)
RETRY_PARAMS = ["reasoning_effort", "response_format"]


def _build_api_params(
    history: list[ChatCompletionMessageParam], message: str, constraints: dict[str, Any]
) -> dict[str, Any]:
    """Собирает параметры API — только из constraints, без хардкода."""
    messages: list[ChatCompletionMessageParam] = list(history) + [
        {"role": "user", "content": message}
    ]
    api_params: dict[str, Any] = {
        "model": state.get_active_model(),
        "messages": messages,
    }
    for key, param_name in PARAM_MAPPING.items():
        value = constraints.get(key)
        if value is not None:
            api_params[param_name] = value
    return api_params


def _create_with_retry(
    client: Any, api_params: dict[str, Any], **extra: Any
) -> tuple[Any, list[str]]:
    """Вызывает create(), при отказе API убирает retry-параметры и повторяет.

    Возвращает ответ и список отброшенных параметров. `api_params` мутируется
    на месте, поэтому в нём остаётся фактически отправленный запрос.
    """
    dropped_params: list[str] = []
    response = None

    for attempt in range(len(RETRY_PARAMS) + 1):
        try:
            response = client.chat.completions.create(**api_params, **extra)
            break
        except BadRequestError as e:
            error_msg = str(e).lower()
            for param in RETRY_PARAMS:
                if param in api_params and param in error_msg:
                    del api_params[param]
                    dropped_params.append(param)
                    break
            else:
                raise  # ошибка не связана с retry-параметрами — пробрасываем
            if attempt == len(RETRY_PARAMS):
                raise  # ретраи исчерпаны

    if response is None:  # недостижимо, но нужно для статического анализа
        raise RuntimeError(
            f"Запрос не удался после сброса параметров: {', '.join(dropped_params)}"
        )
    return response, dropped_params


def _applied_params(
    constraints: dict[str, Any], dropped_params: list[str]
) -> dict[str, Any]:
    """Человекочитаемое описание применённых параметров для UI."""
    applied: dict[str, Any] = {}
    if constraints.get("max_tokens") is not None:
        applied["Длина"] = constraints["max_tokens"]
    if constraints.get("temperature") is not None:
        applied["Температура"] = constraints["temperature"]
    if constraints.get("stop") is not None:
        applied["Стоп-символ"] = constraints["stop"]
    if (
        constraints.get("response_format") is not None
        and "response_format" not in dropped_params
    ):
        fmt = constraints["response_format"]
        applied["Формат"] = fmt.get("type", fmt) if isinstance(fmt, dict) else fmt
    if (
        constraints.get("reasoning_effort") is not None
        and "reasoning_effort" not in dropped_params
    ):
        applied["Reasoning"] = constraints["reasoning_effort"]
    if dropped_params:
        applied["⚠ Сброшен"] = ", ".join(dropped_params)
    return applied


def _usage_dict(response: Any) -> dict[str, int] | None:
    """Токены использования из ответа API (None, если их нет)."""
    if not response.usage:
        return None
    return {
        "prompt": response.usage.prompt_tokens,
        "completion": response.usage.completion_tokens,
        "total": response.usage.total_tokens,
    }


def call_controlled(
    history: list[ChatCompletionMessageParam], message: str, constraints: dict[str, Any]
) -> dict[str, Any]:
    """Контролируемый вызов — с системным промптом и параметрами из constraints."""
    client = state.get_client()
    api_params = _build_api_params(history, message, constraints)
    response, dropped_params = _create_with_retry(client, api_params)
    choice = response.choices[0]

    return {
        "raw": response.model_dump(),
        "request_payload": api_params,
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "applied_params": _applied_params(constraints, dropped_params),
        "usage": _usage_dict(response),
    }


def render_markdown(text: str) -> str:
    import markdown

    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )
