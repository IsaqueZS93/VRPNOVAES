"""
Serviço de email para envio de relatórios VRP.
Gerencia configurações de email e envio de relatórios com anexos.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from pathlib import Path
from typing import List, Optional, Dict, Any
import streamlit as st


class EmailService:
    def __init__(self) -> None:
        # Não carregar variáveis no __init__; ler dinamicamente quando precisar
        pass

    # -------------------- Config --------------------
    def _get_config(self) -> Dict[str, Any]:
        """Obtém configurações de email dinamicamente, compatível com .env e Streamlit Cloud."""
        # Prioriza st.secrets se disponível
        if hasattr(st, "secrets") and "mail" in st.secrets:
            cfg = st.secrets["mail"]
            return {
                "host": cfg.get("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
                "port": int(cfg.get("EMAIL_SMTP_PORT", 587)),
                "use_tls": bool(cfg.get("EMAIL_USE_TLS", True)),
                "user": cfg.get("EMAIL_ADDRESS", ""),
                "password": cfg.get("EMAIL_PASSWORD", ""),
                "from_email": cfg.get("GESTOR_EMAIL", ""),
            }

        # Fallback para .env
        from dotenv import load_dotenv
        load_dotenv()
        return {
            "host": os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com"),
            "port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
            "use_tls": True if os.getenv("EMAIL_USE_TLS", "1") != "0" else False,
            "user": os.getenv("EMAIL_ADDRESS", ""),
            "password": os.getenv("EMAIL_PASSWORD", ""),
            "from_email": os.getenv("GESTOR_EMAIL", ""),
        }

    def is_configured(self) -> bool:
        """Verifica se as configurações de email estão completas."""
        cfg = self._get_config()
        return all([cfg.get("user"), cfg.get("password"), cfg.get("from_email")])

    # -------------------- Sessão --------------------
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

    # -------------------- Envio --------------------
    def send_custom_email(
        self,
        subject: str,
        body: str,
        to: List[str],
        attachments: Optional[List[Dict[str, bytes]]] = None,
    ) -> bool:
        """
        Envia e-mail personalizado com anexos.

        Args:
            subject: Título do e-mail
            body: Corpo do e-mail (texto simples)
            to: Lista de destinatários
            attachments: Lista de dicts {"filename": str, "content": bytes}
        """
        if not self.is_configured():
            st.error("Configurações de email não encontradas. Configure no .env ou em st.secrets['mail'].")
            return False
        if not to:
            st.error("Nenhum destinatário configurado.")
            return False

        try:
            cfg = self._get_config()
            msg = MIMEMultipart()
            msg["From"] = cfg["from_email"]
            msg["To"] = ", ".join(to)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Anexos (bytes)
            for att in attachments or []:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(att["content"])
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={att['filename']}")
                msg.attach(part)

            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
                server.ehlo()
                if cfg["use_tls"]:
                    server.starttls()
                    server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)
            return True

        except Exception as e:
            st.error(f"Erro ao enviar email: {e}")
            return False

    def send_report_email(
        self,
        checklist_id: int,
        report_path: str,
        photos_paths: List[str],
        recipients: List[str],
    ) -> bool:
        """
        Envia relatório por email com anexos.

        Args:
            checklist_id: ID do checklist
            report_path: Caminho para o arquivo do relatório (docx/pdf)
            photos_paths: Lista de caminhos para as fotos
            recipients: Lista de emails destinatários
        """
        if not self.is_configured():
            st.error("Configurações de email não encontradas. Configure no .env ou em st.secrets['mail'].")
            return False
        if not recipients:
            st.error("Nenhum destinatário configurado.")
            return False

        try:
            cfg = self._get_config()

            # Criar mensagem
            msg = MIMEMultipart()
            msg["From"] = cfg["from_email"]
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"Relatório VRP - Checklist #{checklist_id}"

            # Corpo do email
            body = (
                f"Prezados,\n\n"
                f"Segue em anexo o relatório técnico do Checklist #{checklist_id}.\n\n"
                f"Este relatório foi gerado automaticamente pelo sistema VRP da NOVAES Engenharia.\n\n"
                f"Atenciosamente,\n"
                f"Sistema VRP"
            )
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Anexar relatório (se existir)
            rp = Path(report_path)
            if rp.exists():
                with rp.open("rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={rp.name}")
                msg.attach(part)
            else:
                st.warning(f"Arquivo de relatório não encontrado: {rp}")

            # Anexar fotos (best-effort)
            for photo in photos_paths:
                p = Path(photo)
                if not p.exists():
                    st.warning(f"Foto não encontrada: {p}")
                    continue
                try:
                    with p.open("rb") as img:
                        img_part = MIMEImage(img.read())
                    img_part.add_header("Content-Disposition", f"attachment; filename={p.name}")
                    msg.attach(img_part)
                except Exception as e:
                    st.warning(f"Erro ao anexar foto {p.name}: {e}")

            # Enviar
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
                server.ehlo()
                if cfg["use_tls"]:
                    server.starttls()
                    server.ehlo()
                server.login(cfg["user"], cfg["password"])
                server.send_message(msg)

            return True

        except Exception as e:
            st.error(f"Erro ao enviar email: {e}")
            return False

    # -------------------- Status --------------------
    def get_config_status(self) -> dict:
        """Retorna status das configurações de email (para UI)."""
        cfg = self._get_config()
        return {
            "host": cfg["host"],
            "port": cfg["port"],
            "use_tls": cfg["use_tls"],
            "user": cfg["user"] if cfg["user"] else "Não configurado",
            "email": cfg["from_email"] if cfg["from_email"] else "Não configurado",
            "configured": self.is_configured(),
        }


# Instância global
email_service = EmailService()
