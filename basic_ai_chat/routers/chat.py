from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAIError

from services.llm import ChatRequest, call_controlled, render_markdown

router = APIRouter()


@router.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        result = call_controlled(
            req.conversation_history,
            req.message,
            req.constraints,
        )

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
