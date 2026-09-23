from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAI

import reasoning
import state

router = APIRouter()


@router.post("/api/switch-model")
async def switch_model(provider: str, model: str):
    """Смена провайдера/модели без перезапуска сервера."""
    provider_cfg = state._providers_config.get(provider) if provider else None

    if provider not in state._providers_config:
        return JSONResponse(
            {"error": f"Провайдер '{provider}' не найден"}, status_code=400
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

    return JSONResponse(
        {
            "provider": state._active_provider,
            "model": state._active_model,
            "supported_values": {
                "reasoning_effort": reasoning.effort_levels(state._active_model),
                "temperature": state._active_model_config.get("temperature", {}),
                "max_tokens": state._active_model_config.get("max_tokens", {}),
            },
        }
    )


@router.get("/api/providers")
async def get_providers():
    """Список всех провайдеров и моделей из providers.json."""
    result = {}
    for provider_name, provider in state._providers_config.items():
        models_list = []
        if "models" in provider and isinstance(provider["models"], list):
            models_list = [
                {"id": m["id"], "name": m.get("name", m["id"])}
                for m in provider["models"]
            ]
        elif "models" in provider and isinstance(provider["models"], dict):
            models_list = [{"id": k, "name": v} for k, v in provider["models"].items()]

        result[provider_name] = {
            "name": provider.get("name", provider_name),
            "base_url": provider.get("base_url", ""),
            "models": models_list,
        }

    return {
        "providers": result,
        "active_provider": state._active_provider,
        "active_model": state._active_model,
    }


@router.get("/api/supported-values")
async def get_supported_values():
    """Capabilities активной модели: reasoning_effort из models.json,
    temperature/max_tokens из providers.json."""
    return JSONResponse(
        {
            "reasoning_effort": reasoning.effort_levels(state._active_model),
            "temperature": state._active_model_config.get("temperature", {}),
            "max_tokens": state._active_model_config.get("max_tokens", {}),
        }
    )
