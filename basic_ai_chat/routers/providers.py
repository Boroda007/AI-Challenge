from fastapi import APIRouter
from fastapi.responses import JSONResponse

import reasoning
import state

router = APIRouter()


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
            models_list = [
                {"id": k, "name": v} for k, v in provider["models"].items()
            ]

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
