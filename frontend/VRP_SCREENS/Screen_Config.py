"""
Tela de Configurações: mostra caminhos e flags simples.
"""
import streamlit as st
from backend.VRP_SERVICE.export_paths import DB_PATH, UPLOADS_DIR, EXPORTS_DIR
from backend.VRP_SERVICE.email_service import email_service
from ..VRP_STYLES.layout import page_setup, app_header, section_card, pill

def render():
    page_setup("VRP • Configurações", icon="⚙️")
    app_header("Configurações de Email", "Gerencie o envio de relatórios por e-mail.")

    with section_card("📧 Configurações de Email"):
        config_status = email_service.get_config_status()
        if not config_status["configured"]:
            st.warning("⚠️ Configurações de email não encontradas!")
        else:
            st.success("✅ Configurações de email configuradas!")
            st.write(f"**Servidor:** {config_status['host']}:{config_status['port']}")
            st.write(f"**TLS:** {'Sim' if config_status['use_tls'] else 'Não'}")
            st.write(f"**Usuário:** {config_status['user']}")
            st.write(f"**De:** {config_status['email']}")

    with section_card("👥 Emails válidos para envio de relatórios"):
        st.write("Os emails abaixo estão disponíveis para envio de relatórios. Configure no [infoemails] do secrets.")
        emails = st.secrets["infoemails"]["EMAILS"].replace(" ","").split(",")
        if emails:
            st.write("**Emails disponíveis:**")
            for email in emails:
                st.write(f"📧 {email}")
        else:
            st.info("Nenhum email disponível. Configure no secrets.")
