import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAIError

from services.llm import ChatRequest, call_controlled, call_free, render_markdown

router = APIRouter()


@router.post("/api/chat")
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
