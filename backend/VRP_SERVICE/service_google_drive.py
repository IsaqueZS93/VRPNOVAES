"""Serviço para integração com Google Drive.

Observações de robustez:
- Evita import-time ImportError movendo imports opcionais para dentro das funções.
- Ao faltar dependências, as funções retornam None e exibem mensagem instruindo instalação.
"""
from typing import Optional
import os
import io

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

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

def get_shared_drive_id() -> Optional[str]:
    st = _require_streamlit()
    if st is None:
        return None
    return st.secrets.get("google_drive_shared_drive_id")

def get_google_drive_service():
    st = _require_streamlit()
    libs = _require_google_libs()
    if libs is None or st is None:
        # Não levanta ImportError aqui para não quebrar import-time; caller deve checar o retorno
        return None
    Credentials = libs["Credentials"]
    build = libs["build"]
    credentials_json = dict(st.secrets["google_drive_service_account"])
    creds = Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def create_folder(folder_name: str) -> Optional[str]:
    service = get_google_drive_service()
    st = _require_streamlit()
    libs = _require_google_libs()
    if service is None or libs is None:
        if st:
            st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None
    drive_id = get_shared_drive_id()
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    params = {"q": query, "fields": "files(id, name)"}
    if drive_id:
        params.update({"driveId": drive_id, "corpora": "drive", "includeItemsFromAllDrives": True, "supportsAllDrives": True})
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    file_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if drive_id:
        file_metadata["driveId"] = drive_id
    folder = service.files().create(body=file_metadata, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def create_subfolder(parent_folder_id: str, subfolder_name: str) -> Optional[str]:
    service = get_google_drive_service()
    st = _require_streamlit()
    libs = _require_google_libs()
    if service is None or libs is None:
        if st:
            st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None
    drive_id = get_shared_drive_id()
    query = f"name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{parent_folder_id}' in parents"
    params = {"q": query, "fields": "files(id, name)"}
    if drive_id:
        params.update({"driveId": drive_id, "corpora": "drive", "includeItemsFromAllDrives": True, "supportsAllDrives": True})
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    file_metadata = {"name": subfolder_name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_folder_id]}
    if drive_id:
        file_metadata["driveId"] = drive_id
    folder = service.files().create(body=file_metadata, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def upload_file_to_drive(file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
    service = get_google_drive_service()
    st = _require_streamlit()
    libs = _require_google_libs()
    if service is None or libs is None:
        if st:
            st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None
    drive_id = get_shared_drive_id()
    file_metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    if drive_id:
        file_metadata["driveId"] = drive_id
    MediaFileUpload = libs["MediaFileUpload"]
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink", supportsAllDrives=True).execute()
        return file.get("webViewLink")
    except Exception as e:
        if st:
            st.error(f"Erro ao fazer upload para o Google Drive: {e}")
        return None

def upload_bytes_to_drive(data_bytes: bytes, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
    service = get_google_drive_service()
    st = _require_streamlit()
    libs = _require_google_libs()
    if service is None or libs is None:
        if st:
            st.error("Bibliotecas do Google Drive não estão instaladas ou credenciais faltando.")
        return None
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    MediaIoBaseUpload = libs["MediaIoBaseUpload"]
    try:
        media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype="image/jpeg", resumable=True)
    except Exception:
        # fallback to simple upload via MediaFileUpload if needed
        try:
            MediaFileUpload = libs["MediaFileUpload"]
            temp_path = f"/tmp/{filename}"
            with open(temp_path, "wb") as f:
                f.write(data_bytes)
            media = MediaFileUpload(temp_path, resumable=True)
        except Exception as e:
            if st:
                st.error(f"Não foi possível preparar mídia para upload: {e}")
            return None
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink", supportsAllDrives=True).execute()
        return file.get("webViewLink")
    except Exception as e:
        if st:
            try:
                from googleapiclient.errors import HttpError
                if isinstance(e, HttpError):
                    st.error(f"Erro ao fazer upload para o Google Drive: {e}\nDetalhes: {getattr(e, 'content', '')}")
                else:
                    st.error(f"Erro inesperado ao fazer upload para o Google Drive: {e}")
            except Exception:
                st.error(f"Erro inesperado ao fazer upload para o Google Drive: {e}")
        return None
