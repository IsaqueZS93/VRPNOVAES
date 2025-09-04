# file: backend/VRP_SERVICE/export_paths.py
from __future__ import annotations
from pathlib import Path

# Descobre a raiz do projeto a partir deste arquivo:
#   .../<raiz>/backend/VRP_SERVICE/export_paths.py  -> raiz = parents[2]
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2]

BACKEND = _PROJECT_ROOT / "backend"
FRONTEND = _PROJECT_ROOT / "frontend"

DB_DIR = BACKEND / "VRP_DATABASE"
DB_PATH = DB_DIR / "vrp.db"

TEMPLATES_DIR = BACKEND / "VRP_SERVICE" / "templates"
LOGOS_DIR = FRONTEND / "assets" / "logos"
EXPORTS_DIR = FRONTEND / "assets" / "exports"

# (mantido para compatibilidade, mesmo que não usemos agora)
UPLOADS_DIR = FRONTEND / "assets" / "uploads"

# >>> armazenamento TEMPORÁRIO por sessão (USADO AGORA) <<<
SESSION_UPLOADS_DIR = FRONTEND / "assets" / "_session_uploads"

# Garante todas as pastas na inicialização do módulo
for p in [DB_DIR, TEMPLATES_DIR, LOGOS_DIR, EXPORTS_DIR, UPLOADS_DIR, SESSION_UPLOADS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
