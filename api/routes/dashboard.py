from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web Dashboard"])

WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"
INDEX_FILE = WEB_DIR / "index.html"

@router.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    """Serves the JobRadar AI interactive web dashboard (Kanban, async scanner & resume manager)"""
    if not INDEX_FILE.exists():
        # Fallback if accessed from different working directory
        alt_path = Path("web") / "index.html"
        if alt_path.exists():
            return HTMLResponse(content=alt_path.read_text(encoding="utf-8"))
        raise HTTPException(status_code=404, detail="Dashboard UI not found.")
    
    return HTMLResponse(content=INDEX_FILE.read_text(encoding="utf-8"))
