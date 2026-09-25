from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAIError
from pydantic import BaseModel

from services import history
from services.llm import ChatRequest, call_controlled, render_markdown

router = APIRouter()


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
    try:
        result = call_controlled(
            history.get_history(),
            req.message,
            req.constraints,
        )
        history.append_turn(req.message, result["content"])

        return JSONResponse(
            {
                "raw": result["raw"],
                "raw_request": result.get("request_payload"),
                "content": render_markdown(result["content"]),
                "raw_content": result["content"],
                "finish_reason": (
                    result["finish_reason"]
                    if req.constraints
                    and (
                        req.constraints.get("stop")
                        or result["finish_reason"] != "stop"
                    )
                    else None
                ),
                "applied_params": result["applied_params"]
                if req.constraints
                else {},
                "usage": result["usage"],
            }
        )
    except (OpenAIError, RuntimeError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=500)
