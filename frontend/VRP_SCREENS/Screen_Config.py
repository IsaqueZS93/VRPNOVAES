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

    with section_card("👥 Gerenciar Destinatários de Email"):
        st.write("Adicione ou remova emails que receberão os relatórios automaticamente.")
        from backend.VRP_DATABASE.database import add_destinatario, remove_destinatario, listar_destinatarios
        col1, col2 = st.columns([3, 1])
        with col1:
            new_email = st.text_input("Novo email:", placeholder="exemplo@empresa.com", key="new_email_input")
        with col2:
            if st.button("➕ Adicionar", key="add_email_btn"):
                if new_email and "@" in new_email:
                    add_destinatario(new_email)
                    st.success(f"Email {new_email} adicionado!")
                    st.rerun()
                else:
                    st.error("Email inválido!")
        emails = listar_destinatarios()
        if emails:
            st.write("**Emails configurados:**")
            for email in emails:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📧 {email}")
                with col2:
                    if st.button("🗑️", key=f"remove_{email}"):
                        remove_destinatario(email)
                        st.success(f"Email {email} removido!")
                        st.rerun()
        else:
            st.info("Nenhum email configurado. Adicione emails para receber relatórios automaticamente.")
        
        # Teste de email
        if emails and config_status["configured"]:
            st.markdown("---")
            if st.button("🧪 Testar Configuração de Email", type="secondary"):
                with st.spinner("Enviando email de teste..."):
                    # Enviar email de teste
                    test_success = email_service.send_report_email(
                        checklist_id=999,
                        report_path="",
                        photos_paths=[],
                        recipients=emails
                    )
                    if test_success:
                        st.success("✅ Email de teste enviado com sucesso!")
                    else:
                        st.error("❌ Falha ao enviar email de teste. Verifique as configurações.")
