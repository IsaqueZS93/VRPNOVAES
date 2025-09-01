# file: backend/VRP_SERVICE/export_paths.py
"""
Centraliza e cria (se necessário) os diretórios de trabalho.
Usado por toda a aplicação para evitar 'caminhos mágicos'.
Compatível com armazenamento temporário por sessão.
"""
from pathlib import Path

# Raízes relativas ao projeto (funciona local e no Streamlit Cloud)
BACKEND = Path("backend")
FRONTEND = Path("frontend")

# Banco de dados
DB_DIR = BACKEND / "VRP_DATABASE"
DB_PATH = DB_DIR / "vrp.db"

# Templates e assets fixos
TEMPLATES_DIR = BACKEND / "VRP_SERVICE" / "templates"
LOGOS_DIR = FRONTEND / "assets" / "logos"
EXPORTS_DIR = FRONTEND / "assets" / "exports"

# Uploads persistentes (se algum dia voltar a usar)
UPLOADS_DIR = FRONTEND / "assets" / "uploads"

# >>> Armazenamento TEMPORÁRIO por sessão (usado agora) <<<
SESSION_UPLOADS_DIR = FRONTEND / "assets" / "_session_uploads"

# Garante que as pastas existam
for p in [DB_DIR, TEMPLATES_DIR, LOGOS_DIR, EXPORTS_DIR, UPLOADS_DIR, SESSION_UPLOADS_DIR]:
    p.mkdir(parents=True, exist_ok=True)
