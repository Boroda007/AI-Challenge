from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import state
from routers.chat import router as chat_router
from routers.pages import router as pages_router
from routers.providers import router as providers_router
from state import current_dir

# ── Инициализация ───────────────────────────────────────────────────────────
app = FastAPI()

state._load_providers_config()
state._resolve_active_model()

app.include_router(providers_router)
app.include_router(chat_router)
app.include_router(pages_router)




# ── Статика ─────────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory=current_dir / "templates"), name="static")


# ── Точка входа ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    print("🚀 Инициализация ИИ-сервера...")
    print(f"🔗 Эндпоинт API: {state._active_provider} / {state._active_model}")
    print(f"🤖 Модель: {state._active_model_config.get('name', state._active_model)}")

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
