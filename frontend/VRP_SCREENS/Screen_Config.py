# file: frontend/VRP_SCREENS/Screen_Config.py
"""
Tela de Configurações: mostra caminhos e flags simples.
"""
import streamlit as st

# Imports robustos
try:
    from backend.VRP_SERVICE.export_paths import DB_PATH, UPLOADS_DIR, EXPORTS_DIR, LOGOS_DIR
except Exception:
    # Fallback seguro para ambientes sem resolução de pacote
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[2]
    DB_PATH = ROOT / "backend" / "VRP_DATABASE" / "vrp.db"
    UPLOADS_DIR = ROOT / "frontend" / "assets" / "uploads"
    EXPORTS_DIR = ROOT / "frontend" / "assets" / "exports"
    LOGOS_DIR = ROOT / "frontend" / "assets" / "logos"

from backend.VRP_SERVICE.email_service import email_service
from frontend.VRP_STYLES.layout import page_setup, app_header, section_card, pill


def _bool_emoji(v: bool) -> str:
    return "✅" if v else "⚠️"

def render():
    page_setup("VRP • Configurações", icon="⚙️")
    app_header("Configurações", "Caminhos da aplicação e envio de relatórios por e-mail.")

    # --- Caminhos e diretórios ---
    with section_card("📂 Caminhos do sistema"):
        cols = st.columns(2)
        with cols[0]:
            st.code(f"DB: {DB_PATH}")
            st.code(f"Uploads: {UPLOADS_DIR}")
        with cols[1]:
            st.code(f"Exports: {EXPORTS_DIR}")
            st.code(f"Logos: {LOGOS_DIR}")

        # Verificações rápidas
        try:
            st.write(f"{_bool_emoji(DB_PATH.exists())} Arquivo de banco existe")
        except Exception:
            st.write("⚠️ Não foi possível verificar o arquivo de banco.")
        st.write(f"{_bool_emoji(UPLOADS_DIR.exists())} Pasta de uploads pronta")
        st.write(f"{_bool_emoji(EXPORTS_DIR.exists())} Pasta de exports pronta")
        st.write(f"{_bool_emoji(LOGOS_DIR.exists())} Pasta de logos pronta")

    # --- E-mail: status de configuração ---
    with section_card("📧 Configurações de Email"):
        try:
            config_status = email_service.get_config_status()
        except Exception as e:
            st.error(f"Falha ao obter configuração de e-mail: {e}")
            config_status = {"configured": False}

        if not config_status.get("configured"):
            st.warning("⚠️ Configurações de e-mail não encontradas ou incompletas.")
        else:
            st.success("✅ Configurações de e-mail detectadas!")
            st.write(f"**Servidor:** {config_status.get('host','?')}:{config_status.get('port','?')}")
            st.write(f"**TLS:** {'Sim' if config_status.get('use_tls') else 'Não'}")
            st.write(f"**Usuário:** {config_status.get('user','—')}")
            st.write(f"**De:** {config_status.get('email','—')}")

    # --- E-mails válidos (secrets) ---
    with section_card("👥 Destinatários permitidos (secrets: [infoemails])"):
        infoemails = st.secrets.get("infoemails", {})
        emails_raw = infoemails.get("EMAILS", "")
        emails = [e for e in emails_raw.replace(" ", "").split(",") if e]

        if emails:
            st.write("**Emails disponíveis:**")
            for email in emails:
                st.write(f"📧 {email}")
        else:
            st.info("Nenhum e-mail disponível. Configure `infoemails.EMAILS` no `secrets.toml`.")
