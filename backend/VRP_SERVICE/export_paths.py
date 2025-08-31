"""
Centraliza e cria (se necessário) os diretórios de trabalho.
Evita caminhos mágicos e lida com ambientes somente-leitura via fallback.
"""
from pathlib import Path
import os
import tempfile

# Raiz do projeto (…/VRP)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Pastas “preferidas”
BACKEND   = PROJECT_ROOT / "backend"
FRONTEND  = PROJECT_ROOT / "frontend"
DB_DIR_P  = BACKEND / "VRP_DATABASE"
LOGOS_DIR = FRONTEND / "assets" / "logos"      # leitura
UP_DEF    = FRONTEND / "assets" / "uploads"    # escrita
EX_DEF    = FRONTEND / "assets" / "exports"    # escrita

def _ensure_writable(path: Path) -> Path:
    """
    Tenta criar e testar escrita; se falhar, retorna fallback em %TEMP%/vrp_data/<nome>.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return path
    except Exception:
        tmp = Path(tempfile.gettempdir()) / "vrp_data" / path.name
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp

# DB dir pode ser sobreposto
DB_DIR = Path(os.environ.get("VRP_DB_DIR", str(DB_DIR_P)))
DB_DIR = _ensure_writable(DB_DIR)
DB_PATH = DB_DIR / "vrp.db"

# Data dir (uploads/exports) pode ser sobreposto
DATA_DIR = Path(os.environ.get("VRP_DATA_DIR", str(FRONTEND / "assets")))
UPLOADS_DIR = _ensure_writable(DATA_DIR / "uploads")
EXPORTS_DIR = _ensure_writable(DATA_DIR / "exports")

# Logos: só garantir existência (sem exigir escrita se já existir)
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
