from fastapi import APIRouter
from fastapi.responses import FileResponse

from state import current_dir

router = APIRouter()


@router.get("/")
async def home():
    html_path = current_dir / "templates" / "index.html"
    return FileResponse(html_path)
