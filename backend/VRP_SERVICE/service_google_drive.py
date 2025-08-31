# -*- coding: utf-8 -*-
"""
Serviço para integração com Google Drive.

Principais pontos:
- Usa SEMPRE `google_drive_root_folder_id` como pasta-RAIZ onde tudo será criado.
  (Esse ID deve ser de uma PASTA dentro de uma Unidade Compartilhada; compartilhe a pasta com o service account.)
- Opções de Shared Drive (google_drive_shared_drive_id) são opcionais.
- Imports opcionais e mensagens de erro amigáveis.
"""
from __future__ import annotations

from typing import Optional
import os, io, tempfile

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

def _require_streamlit():
    try:
        import streamlit as st
        return st
    except Exception:
        return None

def _require_google_libs():
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
        from googleapiclient.errors import HttpError
        return {
            "Credentials": Credentials,
            "build": build,
            "MediaFileUpload": MediaFileUpload,
            "MediaIoBaseUpload": MediaIoBaseUpload,
            "HttpError": HttpError,
        }
    except Exception:
        return None

def _secrets_get(key: str, default=None):
    st = _require_streamlit()
    if st is None:
        return default
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def get_root_folder_id() -> Optional[str]:
    """ID da PASTA onde tudo será criado (precisa estar numa Unidade Compartilhada)."""
    return _secrets_get("google_drive_root_folder_id")

def get_shared_drive_id() -> Optional[str]:
    """Opcional, ajuda em listagens; não usado como 'parent'."""
    return _secrets_get("google_drive_shared_drive_id")

def get_google_drive_service():
    st = _require_streamlit()
    libs = _require_google_libs()
    if libs is None or st is None:
        return None
    if "google_drive_service_account" not in st.secrets:
        st.error("⚠️ Segredo 'google_drive_service_account' não configurado em st.secrets.")
        return None
    Credentials = libs["Credentials"]; build = libs["build"]
    try:
        credentials_json = dict(st.secrets["google_drive_service_account"])
        creds = Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        st.error(f"Falha ao inicializar Google Drive: {e}")
        return None

def _detect_mime_from_name(name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")

def create_folder(folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
    """
    Cria (ou reaproveita) uma pasta chamada `folder_name` dentro de `parent_id` (ou root_folder_id).
    Retorna o ID da pasta.
    """
    st = _require_streamlit(); libs = _require_google_libs()
    service = get_google_drive_service()
    if service is None or libs is None:
        if st: st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None

    parent = parent_id or get_root_folder_id()
    if not parent:
        if st: st.error("⚠️ 'google_drive_root_folder_id' ausente em secrets. Configure o ID de uma PASTA em Unidade Compartilhada.")
        return None

    # Busca por nome apenas dentro do parent
    query = (
        f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false and '{parent}' in parents"
    )
    params = {
        "q": query,
        "fields": "files(id, name)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent],
    }
    folder = service.files().create(
        body=file_metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder.get("id")

def create_subfolder(parent_folder_id: str, subfolder_name: str) -> Optional[str]:
    """Cria (ou reaproveita) subpasta dentro de `parent_folder_id`."""
    st = _require_streamlit(); libs = _require_google_libs()
    service = get_google_drive_service()
    if service is None or libs is None:
        if st: st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None

    query = (
        f"name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false and '{parent_folder_id}' in parents"
    )
    params = {"q": query, "fields": "files(id, name)", "supportsAllDrives": True, "includeItemsFromAllDrives": True}
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    file_metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    folder = service.files().create(
        body=file_metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder.get("id")

def upload_file_to_drive(file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
    """Faz upload de um arquivo do disco para a pasta indicada (ou root_folder_id). Retorna webViewLink."""
    st = _require_streamlit(); libs = _require_google_libs()
    service = get_google_drive_service()
    if service is None or libs is None:
        if st: st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None

    parent = folder_id or get_root_folder_id()
    if not parent:
        if st: st.error("⚠️ 'google_drive_root_folder_id' ausente em secrets.")
        return None

    file_metadata = {"name": os.path.basename(file_path), "parents": [parent]}
    MediaFileUpload = libs["MediaFileUpload"]
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = service.files().create(
            body=file_metadata, media_body=media,
            fields="id, webViewLink", supportsAllDrives=True
        ).execute()
        return file.get("webViewLink")
    except Exception as e:
        _pretty_drive_error(e)
        return None

def upload_bytes_to_drive(data_bytes: bytes, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
    """Upload de bytes diretamente; retorna webViewLink."""
    st = _require_streamlit(); libs = _require_google_libs()
    service = get_google_drive_service()
    if service is None or libs is None:
        if st: st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None

    parent = folder_id or get_root_folder_id()
    if not parent:
        if st: st.error("⚠️ 'google_drive_root_folder_id' ausente em secrets.")
        return None

    file_metadata = {"name": filename, "parents": [parent]}
    MediaIoBaseUpload = libs["MediaIoBaseUpload"]
    mimetype = _detect_mime_from_name(filename)
    try:
        media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype=mimetype, resumable=True)
    except Exception:
        try:
            MediaFileUpload = libs["MediaFileUpload"]
            tmpdir = tempfile.gettempdir()
            tmp_path = os.path.join(tmpdir, filename)
            with open(tmp_path, "wb") as f:
                f.write(data_bytes)
            media = MediaFileUpload(tmp_path, resumable=True)
        except Exception as e:
            if st: st.error(f"Não foi possível preparar mídia para upload: {e}")
            return None

    try:
        file = service.files().create(
            body=file_metadata, media_body=media,
            fields="id, webViewLink", supportsAllDrives=True
        ).execute()
        return file.get("webViewLink")
    except Exception as e:
        _pretty_drive_error(e)
        return None

def delete_from_drive(file_id: str) -> bool:
    """Remove um arquivo no Drive (retorna True/False)."""
    st = _require_streamlit()
    service = get_google_drive_service()
    if service is None:
        if st: st.warning("Google Drive não configurado; não foi possível excluir no Drive.")
        return False
    try:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return True
    except Exception as e:
        _pretty_drive_error(e)
        return False

def _pretty_drive_error(e: Exception) -> None:
    """Erros mais amigáveis para quota/unidade compartilhada."""
    st = _require_streamlit()
    libs = _require_google_libs()
    msg = str(e)
    if st is None:
        return
    try:
        HttpError = libs["HttpError"] if libs else None
    except Exception:
        HttpError = None
    if HttpError and isinstance(e, HttpError):
        content = getattr(e, "content", b"") or b""
        # Caso clássico: service account sem quota → precisa de Shared Drive
        if b"storageQuotaExceeded" in content or "storageQuotaExceeded" in msg:
            st.error("🚫 Drive: Service Account sem quota. Use uma **Unidade Compartilhada** e configure "
                     "`google_drive_root_folder_id` com o ID de uma **PASTA** dessa Unidade, compartilhada "
                     "com o Service Account (permissão 'Colaborador de conteúdo').")
        else:
            st.error(f"Erro do Drive: {e}\nDetalhes: {content}")
    else:
        st.error(f"Erro inesperado do Drive: {msg}")
