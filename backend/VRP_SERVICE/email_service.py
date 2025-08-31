"""
Serviço de email para envio de relatórios VRP.
Gerencia configurações de email e envio de relatórios com anexos.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from pathlib import Path
from typing import List, Optional
import streamlit as st

from .export_paths import EXPORTS_DIR, UPLOADS_DIR

class EmailService:
    def __init__(self):
        # Não carregar variáveis no __init__, carregar dinamicamente
        pass
        
    def _get_config(self):
        """Obtém configurações de email dinamicamente."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return {
            'host': os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            'port': int(os.getenv("EMAIL_SMTP_PORT", "587")),
            'use_tls': True,  # Sempre usar TLS para Gmail
            'user': os.getenv("EMAIL_ADDRESS", ""),
            'password': os.getenv("EMAIL_PASSWORD", ""),
            'from_email': os.getenv("GESTOR_EMAIL", "")
        }
        
    def is_configured(self) -> bool:
        """Verifica se as configurações de email estão completas."""
        config = self._get_config()
        return all([config['user'], config['password'], config['from_email']])
    
    def get_emails_from_session(self) -> List[str]:
        """Obtém lista de emails da sessão do Streamlit."""
        return st.session_state.get("email_recipients", [])
    
    def add_email_recipient(self, email: str) -> bool:
        """Adiciona um email à lista de destinatários."""
        if not email or "@" not in email:
            return False
            
        emails = self.get_emails_from_session()
        if email not in emails:
            emails.append(email)
            st.session_state["email_recipients"] = emails
        return True
    
    def remove_email_recipient(self, email: str) -> bool:
        """Remove um email da lista de destinatários."""
        emails = self.get_emails_from_session()
        if email in emails:
            emails.remove(email)
            st.session_state["email_recipients"] = emails
            return True
        return False
    
    def send_report_email(self, checklist_id: int, report_path: str, 
                         photos_paths: List[str], recipients: List[str]) -> bool:
        """
        Envia relatório por email com anexos.
        
        Args:
            checklist_id: ID do checklist
            report_path: Caminho para o arquivo do relatório
            photos_paths: Lista de caminhos para as fotos
            recipients: Lista de emails destinatários
            
        Returns:
            bool: True se enviado com sucesso
        """
        if not self.is_configured():
            st.error("Configurações de email não encontradas. Configure no arquivo .env")
            return False
            
        if not recipients:
            st.error("Nenhum destinatário configurado")
            return False
            
        try:
            config = self._get_config()
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = config['from_email']
            msg['To'] = ", ".join(recipients)
            msg['Subject'] = f"Relatório VRP - Checklist #{checklist_id}"
            
            # Corpo do email
            body = f"""
            Prezados,
            
            Segue em anexo o relatório técnico do Checklist #{checklist_id}.
            
            Este relatório foi gerado automaticamente pelo sistema VRP da NOVAES Engenharia.
            
            Atenciosamente,
            Sistema VRP
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Anexar relatório
            if Path(report_path).exists():
                with open(report_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                filename = Path(report_path).name
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {filename}'
                )
                msg.attach(part)
            
            # Anexar fotos
            for photo_path in photos_paths:
                if Path(photo_path).exists():
                    try:
                        with open(photo_path, "rb") as img:
                            img_part = MIMEImage(img.read())
                            filename = Path(photo_path).name
                            img_part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {filename}'
                            )
                            msg.attach(img_part)
                    except Exception as e:
                        st.warning(f"Erro ao anexar foto {filename}: {e}")
            
            # Enviar email
            with smtplib.SMTP(config['host'], config['port']) as server:
                if config['use_tls']:
                    server.starttls()
                server.login(config['user'], config['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            st.error(f"Erro ao enviar email: {e}")
            return False
    
    def get_config_status(self) -> dict:
        """Retorna status das configurações de email."""
        config = self._get_config()
        return {
            "host": config['host'],
            "port": config['port'],
            "use_tls": config['use_tls'],
            "user": config['user'] if config['user'] else "Não configurado",
            "email": config['from_email'] if config['from_email'] else "Não configurado",
            "configured": self.is_configured()
        }

# Instância global
email_service = EmailService()
