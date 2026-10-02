from typing import Literal, cast

from openai.types.chat import ChatCompletionMessageParam

_history: list[ChatCompletionMessageParam] = []


def get_history() -> list[ChatCompletionMessageParam]:
    return list(_history)


def append_message(role: Literal["system", "user", "assistant"], content: str) -> None:
    _history.append(cast(ChatCompletionMessageParam, {"role": role, "content": content}))


def append_turn(message: str, answer: str) -> None:
    append_message("user", message)
    append_message("assistant", answer)


def clear_history() -> None:
    _history.clear()
