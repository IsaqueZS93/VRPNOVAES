"""
Tela de Configurações: mostra caminhos e flags simples.
"""
import streamlit as st
from ..VRP_SERVICE.export_paths import DB_PATH, UPLOADS_DIR, EXPORTS_DIR
from ..VRP_SERVICE.email_service import email_service
from ..VRP_STYLES.layout import page_setup, app_header, section_card, pill

def render():
    page_setup("VRP • Configurações", icon="⚙️")
    app_header("Configurações", "Caminhos e informações do ambiente.")

    with section_card("Caminhos"):
        st.code(f"DB: {DB_PATH}")
        st.code(f"Uploads: {UPLOADS_DIR}")
        st.code(f"Exports: {EXPORTS_DIR}")

    with section_card("IA / Ambiente"):
        st.info("As chaves da IA são lidas do arquivo **.env** na raiz do projeto.")
        pill("GROQ", "success")
        st.caption("Modelo padrão: llama-3.3-70b-versatile (configurado no serviço de IA).")

    # Configurações de Email
    with section_card("📧 Configurações de Email"):
        config_status = email_service.get_config_status()
        
        if not config_status["configured"]:
            st.warning("⚠️ Configurações de email não encontradas!")
            st.info("""
            Para configurar o envio de emails, verifique se as seguintes variáveis estão no arquivo **.env**:
            
            ```
            EMAIL_SMTP_SERVER=smtp.gmail.com
            EMAIL_SMTP_PORT=587
            EMAIL_ADDRESS=seu_email@gmail.com
            EMAIL_PASSWORD=sua_senha_de_app
            GESTOR_EMAIL=email_remetente@gmail.com
            ```
            
            **Nota:** Para Gmail, use uma "senha de app" em vez da senha normal.
            """)
        else:
            st.success("✅ Configurações de email configuradas!")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Servidor:** {config_status['host']}:{config_status['port']}")
                st.write(f"**TLS:** {'Sim' if config_status['use_tls'] else 'Não'}")
            with col2:
                st.write(f"**Usuário:** {config_status['user']}")
                st.write(f"**De:** {config_status['email']}")

    # Gerenciamento de Destinatários
    with section_card("👥 Gerenciar Destinatários de Email"):
        st.write("Adicione ou remova emails que receberão os relatórios automaticamente.")
        
        # Adicionar novo email
        col1, col2 = st.columns([3, 1])
        with col1:
            new_email = st.text_input("Novo email:", placeholder="exemplo@empresa.com", key="new_email_input")
        with col2:
            if st.button("➕ Adicionar", key="add_email_btn"):
                if email_service.add_email_recipient(new_email):
                    st.success(f"Email {new_email} adicionado!")
                    st.rerun()
                else:
                    st.error("Email inválido!")
        
        # Lista de emails atuais
        current_emails = email_service.get_emails_from_session()
        if current_emails:
            st.write("**Emails configurados:**")
            for email in current_emails:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📧 {email}")
                with col2:
                    if st.button("🗑️", key=f"remove_{email}"):
                        email_service.remove_email_recipient(email)
                        st.success(f"Email {email} removido!")
                        st.rerun()
        else:
            st.info("Nenhum email configurado. Adicione emails para receber relatórios automaticamente.")
        
        # Teste de email
        if current_emails and config_status["configured"]:
            st.markdown("---")
            if st.button("🧪 Testar Configuração de Email", type="secondary"):
                with st.spinner("Enviando email de teste..."):
                    # Enviar email de teste
                    test_success = email_service.send_report_email(
                        checklist_id=999,
                        report_path="",
                        photos_paths=[],
                        recipients=current_emails
                    )
                    if test_success:
                        st.success("✅ Email de teste enviado com sucesso!")
                    else:
                        st.error("❌ Falha ao enviar email de teste. Verifique as configurações.")
