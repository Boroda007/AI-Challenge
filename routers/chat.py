import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAIError
from pydantic import BaseModel

from services import history
from services.llm import ChatRequest, render_markdown, stream_controlled

router = APIRouter()


def _sse(frame: dict) -> str:
    """Кадр в формате SSE."""
    return f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"


class SystemPromptRequest(BaseModel):
    content: str


@router.post("/api/system-prompt")
async def api_system_prompt(req: SystemPromptRequest):
    content = req.content.strip()
    if not content:
        return JSONResponse({"error": "System prompt cannot be empty"}, status_code=400)
    history.append_message("system", content)
    return JSONResponse({"content": content})


@router.post("/api/chat")
async def api_chat(req: ChatRequest):
    stream = stream_controlled(
        history.get_history(),
        req.message,
        req.constraints,
    )

    # Первый кадр получаем до ответа: ошибки запуска запроса должны быть JSON, а не потоком.
    try:
        first = next(stream)
    except (OpenAIError, RuntimeError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    if first.get("type") == "error":
        return JSONResponse({"error": first["message"]}, status_code=500)

    async def events():
        yield _sse(first)
        try:
            for frame in stream:
                if frame.get("type") == "done":
                    history.append_turn(req.message, frame["content"])
                    finish_reason = frame["finish_reason"]
                    frame = {
                        **frame,
                        "raw_request": frame.get("request_payload"),
                        "content": render_markdown(frame["content"]),
                        "raw_content": frame["content"],
                        "finish_reason": (
                            finish_reason
                            if req.constraints
                            and (
                                req.constraints.get("stop")
                                or finish_reason != "stop"
                            )
                            else None
                        ),
                        "applied_params": frame["applied_params"]
                        if req.constraints
                        else {},
                    }
                if frame.get("type") == "error":
                    yield _sse(frame)
                    return
                yield _sse(frame)
        except (OpenAIError, RuntimeError, ValueError) as e:
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
