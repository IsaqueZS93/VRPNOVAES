"""
Tela de envio de e-mail com anexo customizado.
Permite ao usuário:
- Definir título do e-mail
- Escrever o corpo do e-mail
- Fazer upload de arquivos para anexar
- Informar os destinatários (múltiplos e-mails)
"""
import streamlit as st
from backend.VRP_SERVICE.email_service import email_service

def render():
    st.title("Enviar E-mail com Anexo")
    with st.form("email_form"):
        titulo = st.text_input("Título do E-mail")
        corpo = st.text_area("Corpo do E-mail", height=150)
        destinatarios = st.text_input("Destinatários (separe por vírgula)", help="Exemplo: email1@dominio.com, email2@dominio.com")
        arquivos = st.file_uploader("Anexar arquivos", accept_multiple_files=True)
        enviar = st.form_submit_button("Enviar E-mail")

    if enviar:
        emails = [e.strip() for e in destinatarios.split(",") if e.strip()]
        if not emails:
            st.error("Informe ao menos um destinatário.")
        elif not titulo:
            st.error("Informe o título do e-mail.")
        elif not corpo:
            st.error("Informe o corpo do e-mail.")
        else:
            anexos = []
            for f in arquivos or []:
                anexos.append({"filename": f.name, "content": f.read()})
            try:
                ok = email_service.send_custom_email(
                    subject=titulo,
                    body=corpo,
                    to=emails,
                    attachments=anexos
                )
                if ok:
                    st.success("E-mail enviado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao enviar e-mail: {e}")
