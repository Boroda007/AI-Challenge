from fastapi import APIRouter
from fastapi.responses import JSONResponse

import reasoning
from state import state

router = APIRouter()


@router.post("/api/switch-model")
async def switch_model(provider: str, model: str):
    """Смена провайдера/модели без перезапуска сервера."""
    try:
        state.switch_model(provider, model)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    model_config = state.get_active_model_config()

    return JSONResponse(
        {
            "provider": state.get_active_provider(),
            "model": state.get_active_model(),
            "supported_values": {
                "reasoning_effort": reasoning.effort_levels(state.get_active_model()),
                "temperature": model_config.get("temperature", {}),
                "max_tokens": model_config.get("max_tokens", {}),
            },
        }
    )


@router.get("/api/providers")
async def get_providers():
    """Список всех провайдеров и моделей из providers.json."""
    result = {}
    for provider_name, provider in state.get_providers_config().items():
        models_list = [
            {"id": m["id"], "name": m["name"]}
            for m in provider.get("models", [])
        ]

        result[provider_name] = {
            "name": provider["name"],
            "base_url": provider["base_url"],
            "models": models_list,
        }

    return {
        "providers": result,
        "active_provider": state.get_active_provider(),
        "active_model": state.get_active_model(),
    }


@router.get("/api/supported-values")
async def get_supported_values():
    """Capabilities активной модели: reasoning_effort из models.json,
    temperature/max_tokens из providers.json."""
    return JSONResponse(
        {
            "reasoning_effort": reasoning.effort_levels(state.get_active_model()),
            "temperature": state.get_active_model_config().get("temperature", {}),
            "max_tokens": state.get_active_model_config().get("max_tokens", {}),
        }
    )
