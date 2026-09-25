import logging
from collections.abc import Iterator
from typing import Any

from openai import BadRequestError, OpenAIError
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
        "reasoning": getattr(choice.message, "reasoning", None)
        or getattr(choice.message, "reasoning_content", None)
        or "",
        "finish_reason": choice.finish_reason,
        "applied_params": _applied_params(constraints, dropped_params),
        "usage": _usage_dict(response),
    }


def _open_stream(client: Any, api_params: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Открывает поток с учётом usage; при отказе в stream_options повторяет без него.

    Возвращает поток и фактически отправленные параметры потока.
    """
    extra: dict[str, Any] = {"stream": True, "stream_options": {"include_usage": True}}
    while True:
        try:
            return client.chat.completions.create(**api_params, **extra), extra
        except BadRequestError as e:
            if "stream_options" not in extra or "stream_options" not in str(e).lower():
                raise
            del extra["stream_options"]  # провайдер не умеет отдавать usage в потоке


def _chunk_raw(chunk: Any, content: str, finish_reason: Any) -> dict[str, Any]:
    """Сырые данные чанка для блока «JSON-ответ»."""
    model_dump = getattr(chunk, "model_dump", None)
    if callable(model_dump):
        raw: object = model_dump()
        if isinstance(raw, dict):
            return raw
    return {"delta": {"content": content}, "finish_reason": finish_reason}


def stream_controlled(
    history: list[ChatCompletionMessageParam], message: str, constraints: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Потоковая версия call_controlled: отдаёт чанки по мере поступления.

    Первым отдаётся кадр {"type": "start"} — чтобы отклик начинался сразу,
    затем кадры {"type": "reasoning", ...} (размышление модели) и
    {"type": "delta", ...}, затем один кадр {"type": "done", ...} со всеми
    метаданными ответа.
    """
    client = state.get_client()
    api_params = _build_api_params(history, message, constraints)
    stream, stream_params = _open_stream(client, api_params)
    dropped_params: list[str] = []

    parts: list[str] = []
    reasoning_parts: list[str] = []
    raw_chunks: list[dict[str, Any]] = []
    finish_reason: Any = None
    usage: dict[str, int] | None = None

    yield {"type": "start"}

    try:
        for chunk in stream:
            if getattr(chunk, "usage", None):
                usage = _usage_dict(chunk)
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            content = getattr(choice.delta, "content", None)
            reasoning = getattr(choice.delta, "reasoning", None) or getattr(
                choice.delta, "reasoning_content", None
            )
            if not content and reasoning:
                reasoning_parts.append(reasoning)
                raw_chunks.append(_chunk_raw(chunk, reasoning, choice.finish_reason))
                yield {"type": "reasoning", "content": reasoning}
                continue
            if not content:
                continue
            parts.append(content)
            raw_chunks.append(_chunk_raw(chunk, content, choice.finish_reason))
            yield {"type": "delta", "content": content}
    except OpenAIError as e:
        logger.error("Ошибка во время стриминга: %s", e)
        yield {"type": "error", "message": str(e)}
        return

    for param in RETRY_PARAMS:
        if param not in api_params and constraints.get(param) is not None:
            dropped_params.append(param)

    yield {
        "type": "done",
        "content": "".join(parts),
        "reasoning": "".join(reasoning_parts),
        "raw": raw_chunks,
        "request_payload": {**api_params, **stream_params},
        "finish_reason": finish_reason,
        "applied_params": _applied_params(constraints, dropped_params),
        "usage": usage,
    }


def render_markdown(text: str) -> str:
    import markdown

    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )
