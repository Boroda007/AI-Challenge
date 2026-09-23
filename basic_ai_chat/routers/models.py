from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAI

import state

router = APIRouter()


@router.post("/switch-model")
async def switch_model(provider: str, model: str):
    """Смена провайдера/модели без перезапуска сервера."""
    if provider not in state._providers_config:
        return JSONResponse(
            {"error": f"Провайдер '{provider}' не найден"},
            status_code=400,
        )

    provider_cfg = state._providers_config[provider]
    model_config = None

    for m in provider_cfg.get("models", []):
        if m["id"] == model:
            model_config = m
            break

    if model_config is None:
        return JSONResponse(
            {"error": f"Модель '{model}' не найдена у провайдера '{provider}'"},
            status_code=400,
        )

    state._active_provider = provider
    state._active_model = model
    state._active_model_config = model_config

    state._client = OpenAI(
        base_url=provider_cfg["base_url"],
        api_key=provider_cfg.get("api_key", "") or "none",
    )

    state._save_providers_config()

    from reasoning import effort_levels

    return JSONResponse(
        {
            "provider": state._active_provider,
            "model": state._active_model,
            "supported_values": {
                "reasoning_effort": effort_levels(state._active_model),
                "temperature": state._active_model_config.get("temperature", {}),
                "max_tokens": state._active_model_config.get("max_tokens", {}),
            },
        }
    )
