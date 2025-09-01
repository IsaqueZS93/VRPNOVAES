# file: backend/VRP_SERVICE/export_paths.py
from pathlib import Path

BACKEND = Path("backend")
DB_DIR = BACKEND / "VRP_DATABASE"
DB_PATH = DB_DIR / "vrp.db"
TEMPLATES_DIR = BACKEND / "VRP_SERVICE" / "templates"
FRONTEND = Path("frontend")
LOGOS_DIR = FRONTEND / "assets" / "logos"
UPLOADS_DIR = FRONTEND / "assets" / "uploads"

# NOVO: uploads temporários por sessão
SESSION_UPLOADS_DIR = FRONTEND / "assets" / "_session_uploads"

for p in [DB_DIR, TEMPLATES_DIR, LOGOS_DIR, UPLOADS_DIR, SESSION_UPLOADS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
