from fastapi import APIRouter
from fastapi.responses import FileResponse

from state import state

router = APIRouter()


@router.get("/")
async def home():
    html_path = state.get_project_dir() / "templates" / "index.html"
    return FileResponse(html_path)
