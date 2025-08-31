# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_SERVICE\export_paths.py
"""
Centraliza e cria (se necessário) os diretórios de trabalho.
Usado por toda a aplicação para evitar 'caminhos mágicos' espalhados.
"""
from pathlib import Path

ROOT = Path(r"C:\Users\Novaes Engenharia\github - deploy\VRP").resolve()

BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

DB_DIR = BACKEND / "VRP_DATABASE"
DB_PATH = DB_DIR / "vrp.db"

TEMPLATES_DIR = BACKEND / "VRP_SERVICE" / "templates"
LOGOS_DIR = FRONTEND / "assets" / "logos"
UPLOADS_DIR = FRONTEND / "assets" / "uploads"
EXPORTS_DIR = FRONTEND / "assets" / "exports"

for p in [DB_DIR, TEMPLATES_DIR, LOGOS_DIR, UPLOADS_DIR, EXPORTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
