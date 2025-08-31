"""
Serviço para integração com Google Drive (import-safe).

- Evita falhas no import (sem globais mutáveis).
- Usa st.secrets apenas dentro das funções.
- Se features.enable_drive = false ou faltarem libs/segredos, retorna None de forma amigável.
- Suporta raiz: `google_drive_root_folder_id` OU `google_drive_shared_drive_id`.
"""

from __future__ import annotations
from typing import Optional, Dict, Any
import os
import io
import tempfile

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# ---------------- helpers locais ----------------
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

def _feature_enabled(st) -> bool:
    """Lê st.secrets['features']['enable_drive'] (default=False)."""
    try:
        return bool(st.secrets.get("features", {}).get("enable_drive", False))
    except Exception:
        return False

def _sanitize_id(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip()
    # Suporta IDs colados com <...>
    if v.startswith("<") and v.endswith(">"):
        v = v[1:-1].strip()
    return v or None

def _drive_root_ids(st) -> Dict[str, Optional[str]]:
    """Retorna ids saneados (podem ser None):
       - root_folder_id (pasta raiz onde salvar)
       - shared_drive_id (id da unidade compartilhada, p/ listagens)"""
    root_folder_id = _sanitize_id(st.secrets.get("google_drive_root_folder_id"))
    shared_drive_id = _sanitize_id(st.secrets.get("google_drive_shared_drive_id"))
    return {"root_folder_id": root_folder_id, "shared_drive_id": shared_drive_id}

def _detect_mime_from_name(name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")

# --------------- núcleo: criar serviço ---------------
def get_google_drive_service():
    """Cria o client do Drive. Retorna None se indisponível."""
    st = _require_streamlit()
    libs = _require_google_libs()
    if st is None or libs is None:
        return None
    if not _feature_enabled(st):
        # recurso desligado por config
        return None
    if "google_drive_service_account" not in st.secrets:
        # Sem credenciais
        if hasattr(st, "error"):
            st.error("⚠️ 'google_drive_service_account' não configurado em st.secrets.")
        return None
    Credentials = libs["Credentials"]
    build = libs["build"]
    try:
        credentials_json = dict(st.secrets["google_drive_service_account"])
        creds = Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        if hasattr(st, "error"):
            st.error(f"Falha ao inicializar Google Drive: {e}")
        return None

# --------------- operações de pasta/arquivo ---------------
def create_folder(folder_name: str) -> Optional[str]:
    """Cria (ou retorna) pasta pelo NOME dentro da raiz definida em secrets.
       Se não houver raiz, cria no Meu Drive do service account (pode falhar por quota)."""
    st = _require_streamlit()
    libs = _require_google_libs()
    service = get_google_drive_service()
    if st is None or libs is None or service is None:
        return None

    ids = _drive_root_ids(st)
    root_folder_id = ids["root_folder_id"]
    shared_drive_id = ids["shared_drive_id"]

    # Busca por nome dentro da raiz (se houver) ou globalmente
    if root_folder_id:
        query = (
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false "
            f"and '{root_folder_id}' in parents"
        )
    else:
        # sem raiz definida: busca geral (pode encontrar no Meu Drive)
        query = (
            f"name = '{folder_name}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )

    params: Dict[str, Any] = {"q": query, "fields": "files(id,name)", "supportsAllDrives": True}
    if shared_drive_id:
        params.update({"driveId": shared_drive_id, "corpora": "drive", "includeItemsFromAllDrives": True})

    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    # Criar pasta: se root_folder_id existir, colocamos como parent
    metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if root_folder_id:
        metadata["parents"] = [root_folder_id]

    folder = service.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder.get("id")

def create_subfolder(parent_folder_id: str, subfolder_name: str) -> Optional[str]:
    st = _require_streamlit()
    libs = _require_google_libs()
    service = get_google_drive_service()
    if st is None or libs is None or service is None:
        return None

    query = (
        f"name = '{subfolder_name}' and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false and '{parent_folder_id}' in parents"
    )
    params = {"q": query, "fields": "files(id, name)", "supportsAllDrives": True, "includeItemsFromAllDrives": True}
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id],
    }
    folder = service.files().create(
        body=metadata, fields="id", supportsAllDrives=True
    ).execute()
    return folder.get("id")

def upload_file_to_drive(file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
    """Upload de arquivo do disco. Coloca na pasta informada; se None, usa a raiz configurada."""
    st = _require_streamlit()
    libs = _require_google_libs()
    service = get_google_drive_service()
    if st is None or libs is None or service is None:
        return None

    ids = _drive_root_ids(st)
    root_folder_id = ids["root_folder_id"]

    file_metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    elif root_folder_id:
        file_metadata["parents"] = [root_folder_id]

    MediaFileUpload = libs["MediaFileUpload"]
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = service.files().create(
            body=file_metadata, media_body=media,
            fields="id, webViewLink", supportsAllDrives=True
        ).execute()
        return file.get("webViewLink")
    except Exception as e:
        if hasattr(st, "error"):
            st.error(f"Erro ao fazer upload para o Google Drive: {e}")
        return None

def upload_bytes_to_drive(data_bytes: bytes, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
    """Upload direto de bytes. Coloca na pasta informada; se None, usa raiz configurada."""
    st = _require_streamlit()
    libs = _require_google_libs()
    service = get_google_drive_service()
    if st is None or libs is None or service is None:
        return None

    ids = _drive_root_ids(st)
    root_folder_id = ids["root_folder_id"]

    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    elif root_folder_id:
        file_metadata["parents"] = [root_folder_id]

    MediaIoBaseUpload = libs["MediaIoBaseUpload"]
    mimetype = _detect_mime_from_name(filename)

    try:
        media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype=mimetype, resumable=True)
    except Exception:
        # fallback via arquivo temporário
        MediaFileUpload = libs["MediaFileUpload"]
        tmpdir = tempfile.gettempdir()
        tmp_path = os.path.join(tmpdir, filename)
        with open(tmp_path, "wb") as f:
            f.write(data_bytes)
        media = MediaFileUpload(tmp_path, resumable=True)

    try:
        file = service.files().create(
            body=file_metadata, media_body=media,
            fields="id, webViewLink", supportsAllDrives=True
        ).execute()
        return file.get("webViewLink")
    except Exception as e:
        # tenta detalhar erro de quota/unidade
        try:
            HttpError = libs["HttpError"]
            if isinstance(e, HttpError) and hasattr(st, "error"):
                st.error(f"Erro ao fazer upload para o Google Drive: {e}\nDetalhes: {getattr(e, 'content', '')}")
        except Exception:
            if hasattr(st, "error"):
                st.error(f"Erro inesperado ao fazer upload para o Google Drive: {e}")
        return None

def delete_from_drive(file_id: str) -> bool:
    """Remove um arquivo do Drive (retorna True/False, não lança)."""
    st = _require_streamlit()
    service = get_google_drive_service()
    if service is None:
        if hasattr(st, "warning"):
            st.warning("Google Drive não configurado; não foi possível excluir no Drive.")
        return False
    try:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return True
    except Exception as e:
        if hasattr(st, "error"):
            st.error(f"Falha ao excluir arquivo no Drive: {e}")
        return False
