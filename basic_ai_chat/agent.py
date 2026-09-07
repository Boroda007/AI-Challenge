import json
import asyncio
from typing import Callable
from pydantic import BaseModel
from openai.types.chat import ChatCompletionMessageParam

# ── Константы ────────────────────────────────────────────────────────────────
MAX_AGENT_STEPS = 3


def _try_loads_dict(s: str) -> dict | None:
    """Пытается распарсить строку как JSON-объект."""
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _scan_json_object(text: str) -> dict | None:
    """Ищет первый сбалансированный JSON-объект, игнорируя преамбулу и хвост."""
    n = len(text)
    start = 0
    while True:
        start = text.find('{', start)
        if start == -1:
            return None

        depth = 0
        in_str = False
        esc = False
        end = -1
        j = start
        while j < n:
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = j
                        break
            j += 1

        if end == -1:
            return None

        obj = _try_loads_dict(text[start:end + 1])
        if obj is not None:
            return obj
        start = end + 1


def _extract_json(text: str) -> dict | None:
    """Извлекает JSON-объект из строки.

    Устойчив к:
    - тексту-преамбуле до JSON;
    - обёртке вызова в массив: ["...", {"tool": ...}];
    - мусору после объекта (в т.ч. markdown-обрамлению ```json ... ```).
    """
    if not isinstance(text, str) or not text.strip():
        return None

    stripped = text.strip()

    # 1) Вся строка — уже JSON-объект
    obj = _try_loads_dict(stripped)
    if obj is not None:
        return obj

    # 2) Вся строка — JSON-массив: ищем внутри объект-вызов тула
    try:
        arr = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        arr = None
    if isinstance(arr, list):
        for item in arr:
            if isinstance(item, dict) and "tool" in item:
                return item
        for item in arr:
            if isinstance(item, dict):
                return item
        return None

    # 3) Побуквенный скан по сбалансированным скобкам
    return _scan_json_object(stripped)

# ── Pydantic-схемы ──────────────────────────────────────────────────────────


class AgentRequest(BaseModel):
    """Входной запрос от фронтенда."""
    message: str
    history: list[ChatCompletionMessageParam] = []


class AgentStep(BaseModel):
    """Один шаг рассуждения агента."""
    type: str  # "thinking" | "tool_call" | "tool_result" | "clarification" | "answer"
    content: str = ""
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: dict | None = None
    raw_request: dict | None = None
    raw_response: dict | None = None
    usage: dict | None = None


class AgentResponse(BaseModel):
    """Ответ агента фронтенду."""
    type: str  # "answer" | "clarification"
    content: str
    steps: list[AgentStep] = []
    results: list[dict] | None = None  # для compare_responses — массив ответов
    raw_request: dict | None = None
    raw_response: dict | None = None
    usage: dict | None = None


# ── Промпт ───────────────────────────────────────────────────────────────────


def get_agent_system_prompt(model_name: str, model_config: dict) -> str:
    """Системный промпт агента с описанием доступных tools."""
    reasoning_values = model_config.get("reasoning_effort", [])
    temp_config = model_config.get("temperature", {})
    max_tokens_config = model_config.get("max_tokens", {})

    reasoning_hint = ""
    if reasoning_values:
        reasoning_hint = f"\n- reasoning_effort: {', '.join(reasoning_values)} (если поддерживается моделью)"

    temp_hint = f"0.0-{temp_config.get('max', 2.0)} (по умолчанию {temp_config.get('default', 0.7)})"
    max_tokens_hint = f"{max_tokens_config.get('min', 5)}-{max_tokens_config.get('max', 32768)} (по умолчанию {max_tokens_config.get('default', 150)})"

    return f"""Ты — AI-агент, выполняющий задачи пользователя. Твоя задача — проанализировать запрос и выполнить его, используя доступные инструменты.

## Доступные инструменты

### compare_responses
Сравнение ответов модели с разными параметрами генерации.
Параметры:
- message (str): текст запроса
- variants (list): список вариантов, каждый содержит:
  - constraints (dict): параметры генерации
  - label (str, опционально): подпись варианта

Пример вызова:
{{"tool": "compare_responses", "params": {{"message": "Объясни квантовую физику", "variants": [{{"constraints": {{"temperature": 0}}, "label": "T=0"}}, {{"constraints": {{"temperature": 0.7}}, "label": "T=0.7"}}]}}}}

Доступные параметры в constraints:
- temperature: {temp_hint}
- max_tokens: {max_tokens_hint}
- stop: стоп-символ
- response_format: {{"type": "text"}} или {{"type": "json_object"}}{reasoning_hint}

### get_model_info
Получение информации о текущей модели и её возможностях.
Параметры: {{}} (пустой объект)
Возвращает: название модели, поддерживаемые параметры, диапазоны значений.

### ask_user
Задать уточняющий вопрос пользователю перед выполнением задачи.
Параметры:
- question (str): текст вопроса

Используй этот инструмент, если в запросе недостаточно информации для выполнения задачи.

## Формат ответа

Когда тебе нужно вызвать инструмент, ответь JSON без markdown-обёртки:
{{"tool": "имя_инструмента", "params": {{параметры}}}}

Когда ты получил результат инструмента и готов дать финальный ответ, ответь обычным текстом (не JSON).

## Правила

1. Если запрос простой (привет, представься, справка о возможностях) — ответь текстом без JSON и инструментов.
2. Анализируй запрос и определяй, какие инструменты нужны
3. Если информации недостаточно — задай уточняющий вопрос через ask_user
4. Максимум {MAX_AGENT_STEPS} вызова инструментов за один цикл
5. После получения результата анализируй его и решай: ещё вызов или финальный ответ
6. Будь точен в параметрах — используй значения из запроса пользователя
7. Если пользователь не указал параметры, используй разумные значения по умолчанию (temperature: {temp_config.get('default', 0.7)}, max_tokens: {max_tokens_config.get('default', 150)})"""


__all__ = [
    "AgentRequest",
    "AgentStep",
    "AgentResponse",
    "get_agent_system_prompt",
    "execute_tool",
    "agent_loop",
    "MAX_AGENT_STEPS",
]


# ── Tools ────────────────────────────────────────────────────────────────────


async def tool_compare_responses(
    message: str,
    variants: list[dict],
    call_llm_fn: Callable,
) -> dict:
    """Параллельные вызовы LLM с разными constraints."""
    tasks = []
    labels = []

    for v in variants:
        constraints = v.get("constraints", {})
        label = v.get("label", "")
        tasks.append(asyncio.to_thread(call_llm_fn, message, [], constraints))
        labels.append(label)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for i, (label, result) in enumerate(zip(labels, results)):
        if isinstance(result, Exception):
            output.append({
                "label": label or f"Вариант {i + 1}",
                "constraints": variants[i].get("constraints", {}),
                "error": str(result),
            })
        else:
            output.append({
                "label": label or f"Вариант {i + 1}",
                "constraints": variants[i].get("constraints", {}),
                "response": {
                    "content": result["content"],
                    "raw_content": result["content"],
                    "applied_params": result.get("applied_params", {}),
                    "usage": result.get("usage"),
                    "raw": result.get("raw"),
                    "raw_request": result.get("request_payload"),
                },
            })

    return {"results": output}


def tool_get_model_info(model_config: dict) -> dict:
    """Информация о текущей модели и её возможностях."""
    return {
        "model": {
            "id": model_config.get("id", ""),
            "name": model_config.get("name", ""),
        },
        "capabilities": {
            "reasoning_effort": model_config.get("reasoning_effort", []),
            "temperature": model_config.get("temperature", {}),
            "max_tokens": model_config.get("max_tokens", {}),
        },
    }


def tool_ask_user(question: str) -> dict:
    """Уточняющий вопрос пользователю."""
    return {"type": "clarification", "question": question}


# ── Диспетчер tools ─────────────────────────────────────────────────────────


async def execute_tool(
    tool_name: str,
    tool_args: dict,
    call_llm_fn: Callable,
    model_config: dict,
) -> dict:
    """Вызов tool по имени с диспетчеризацией."""
    if tool_name == "compare_responses":
        message = tool_args.get("message", "")
        variants = tool_args.get("variants", [])
        return await tool_compare_responses(message, variants, call_llm_fn)

    elif tool_name == "get_model_info":
        return tool_get_model_info(model_config)

    elif tool_name == "ask_user":
        question = tool_args.get("question", "")
        return tool_ask_user(question)

    else:
        return {"error": f"Неизвестный инструмент: {tool_name}"}


# ── Agent loop ───────────────────────────────────────────────────────────────


async def agent_loop(
    message: str,
    history: list[ChatCompletionMessageParam],
    call_llm_fn: Callable,
    model_config: dict,
    system_prompt: str,
    constraints: dict | None = None,
) -> dict:
    """Основной цикл агента: LLM → парсинг → tool call → повтор."""
    steps: list[AgentStep] = []
    current_history: list[ChatCompletionMessageParam] = list(history)
    results: list[dict] | None = None
    response_text = ""
    last_raw_request: dict | None = None
    last_raw_response: dict | None = None
    last_usage: dict | None = None

    # Текущее user-сообщение, ещё не зафиксированное в current_history
    pending = message

    for attempt in range(MAX_AGENT_STEPS):
        # Вызов LLM
        response = await asyncio.to_thread(
            call_llm_fn, pending, current_history, constraints or {}, system_prompt
        )
        response_text = response["content"]
        last_raw_request = response.get("request_payload")
        last_raw_response = response.get("raw")
        last_usage = response.get("usage")

        # Попытка JSON parse
        parsed = _extract_json(response_text)
        if parsed is None:
            # Не JSON — финальный ответ
            steps.append(AgentStep(type="answer", content=response_text))
            return AgentResponse(
                type="answer", content=response_text, steps=steps,
                results=results,
                raw_request=last_raw_request, raw_response=last_raw_response, usage=last_usage,
            ).model_dump()

        # Проверка на tool call
        if "tool" not in parsed:
            steps.append(AgentStep(type="answer", content=response_text))
            return AgentResponse(
                type="answer", content=response_text, steps=steps,
                results=results,
                raw_request=last_raw_request, raw_response=last_raw_response, usage=last_usage,
            ).model_dump()

        # Tool call
        tool_name = parsed["tool"]
        tool_args = parsed.get("params", {})

        steps.append(AgentStep(
            type="tool_call",
            content=f"Вызов {tool_name}",
            tool_name=tool_name,
            tool_args=tool_args,
            raw_request=last_raw_request,
            raw_response=last_raw_response,
            usage=last_usage,
        ))

        # Выполнение tool
        tool_result = await execute_tool(
            tool_name, tool_args, call_llm_fn, model_config,
        )

        steps.append(AgentStep(
            type="tool_result",
            content=json.dumps(tool_result, ensure_ascii=False)[:500],
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
        ))

        # Проверка на clarification
        if tool_name == "ask_user":
            question = tool_result.get("question", "")
            return AgentResponse(
                type="clarification",
                content=question,
                steps=steps,
                raw_request=last_raw_request, raw_response=last_raw_response, usage=last_usage,
            ).model_dump()

        # Сохранение результатов для compare_responses
        if tool_name == "compare_responses":
            results = tool_result.get("results")

        # Фиксируем отправленное user-сообщение и JSON-вызов тула в истории;
        # следующим user-поворотом будет результат инструмента
        current_history.append({"role": "user", "content": pending})
        current_history.append({"role": "assistant", "content": response_text})
        pending = (
            f"Результат инструмента `{tool_name}`:\n"
            f"{json.dumps(tool_result, ensure_ascii=False)}\n\n"
            "Проанализируй результат и дай финальный ответ пользователю текстом (не JSON)."
        )

    # Цикл исчерпан — вернуть последний ответ
    return AgentResponse(
        type="answer",
        content=response_text,
        steps=steps,
        results=results,
        raw_request=last_raw_request, raw_response=last_raw_response, usage=last_usage,
    ).model_dump()
