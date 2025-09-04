# backend/VRP_SERVICE/export_paths.py
from pathlib import Path

BACKEND = Path("backend")
FRONTEND = Path("frontend")

DB_DIR = BACKEND / "VRP_DATABASE"
DB_PATH = DB_DIR / "vrp.db"

TEMPLATES_DIR = BACKEND / "VRP_SERVICE" / "templates"
LOGOS_DIR = FRONTEND / "assets" / "logos"
EXPORTS_DIR = FRONTEND / "assets" / "exports"

# (mantido para compatibilidade, mesmo que não usemos agora)
UPLOADS_DIR = FRONTEND / "assets" / "uploads"

# >>> armazenamento TEMPORÁRIO por sessão (USADO AGORA) <<<
SESSION_UPLOADS_DIR = FRONTEND / "assets" / "_session_uploads"

for p in [DB_DIR, TEMPLATES_DIR, LOGOS_DIR, EXPORTS_DIR, UPLOADS_DIR, SESSION_UPLOADS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
