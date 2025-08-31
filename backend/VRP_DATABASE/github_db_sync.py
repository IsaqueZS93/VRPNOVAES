import os
import requests
from github import Github

GITHUB_REPO = "IsaqueZS93/VRPNOVAES"
DB_FILE = os.path.join(os.path.dirname(__file__), "vrp.db")
DB_PATH_GITHUB = "backend/VRP_DATABASE/vrp.db"

RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{DB_PATH_GITHUB}"

def baixar_banco_github():
    """Baixa o banco de dados do GitHub e salva localmente."""
    resp = requests.get(RAW_URL)
    if resp.status_code == 200:
        # Verifica se o arquivo baixado tem tamanho mínimo (SQLite > 0.5KB)
        if len(resp.content) > 512:
            with open(DB_FILE, "wb") as f:
                f.write(resp.content)
            print("Banco de dados baixado do GitHub!")
        else:
            print("Banco baixado do GitHub está vazio ou corrompido. Mantendo banco local.")
    else:
        print(f"Erro ao baixar banco: {resp.status_code}")

def subir_banco_github():
    """Faz commit e push do banco de dados para o GitHub."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN não definido!")
        return
    g = Github(token)
    repo = g.get_repo(GITHUB_REPO)
    with open(DB_FILE, "rb") as f:
        content = f.read()
    try:
        contents = repo.get_contents(DB_PATH_GITHUB)
        repo.update_file(contents.path, "Atualizando banco de dados", content, contents.sha, branch="main")
    except Exception:
        repo.create_file(DB_PATH_GITHUB, "Adicionando banco de dados", content, branch="main")
    print("Banco de dados enviado para o GitHub!")

# Exemplo de uso:
# baixar_banco_github()  # Chame no início do app
# subir_banco_github()   # Chame ao finalizar ou após alterações
