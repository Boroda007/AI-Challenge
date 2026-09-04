import os
from pathlib import Path
from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, HTMLResponse
from openai import OpenAI
from dotenv import load_dotenv
import markdown

# Загружаем .env из текущей папки
current_dir = Path(__file__).resolve().parent
dotenv_path = current_dir / ".env"

# Принудительно загружаем переменные из этого файла в память системы
load_dotenv(dotenv_path=dotenv_path)

# Извлечение переменных окружения
BASE_URL: str = os.getenv("BASE_URL") or ""
API_KEY: str = os.getenv("API_KEY") or ""
MODEL_NAME: str = os.getenv("MODEL_NAME") or ""

if not BASE_URL:
    raise ValueError("❌ Критическая ошибка: Переменная BASE_URL не задана в .env или консоли!")
if not MODEL_NAME:
    raise ValueError("❌ Критическая ошибка: Переменная MODEL_NAME не задана в .env или консоли!")
if not API_KEY:
    raise ValueError("❌ Критическая ошибка: Переменная API_KEY не задана в .env или консоли!")


# Инициализация FastAPI и клиента OpenAI
app = FastAPI()
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br"],
    )


@app.get("/")
async def home():
    # Отдаем чистый HTML-файл из папки templates
    html_path = current_dir / "templates" / "index.html"
    return FileResponse(html_path)


@app.post("/ask")
async def ask_ai(text: str = Form(...)):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, 
            messages=[{"role": "user", "content": text}]
        )
        return HTMLResponse(render_markdown(response.choices[0].message.content or ""))
        
    except Exception as e:
        return HTMLResponse(f"Ошибка при запросе к ИИ-роутеру: {str(e)}")

# Точка входа
if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Инициализация ИИ-сервера...")
    print(f"🔗 Эндпоинт API: {BASE_URL}")
    print(f"🤖 Используемая модель: {MODEL_NAME}")

    # Запускаем uvicorn напрямую из Python
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)