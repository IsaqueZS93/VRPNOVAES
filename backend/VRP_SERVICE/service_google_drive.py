import io
from googleapiclient.http import MediaIoBaseUpload
def upload_bytes_to_drive(data_bytes, filename, folder_id=None):
    service = get_google_drive_service()
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaIoBaseUpload(io.BytesIO(data_bytes), mimetype="image/jpeg", resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
        return file.get("webViewLink")
    except Exception as e:
        import streamlit as st
        st.error(f"Erro ao fazer upload para o Google Drive: {e}")
        return None
import os
import streamlit as st
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]

def get_shared_drive_id():
    # O ID do Shared Drive deve estar em st.secrets["google_drive_shared_drive_id"]
    return st.secrets.get("google_drive_shared_drive_id", None)

def get_google_drive_service():
    credentials_json = dict(st.secrets["google_drive_service_account"])
    creds = Credentials.from_service_account_info(credentials_json, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def create_folder(folder_name):
    service = get_google_drive_service()
    drive_id = get_shared_drive_id()
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    params = {"q": query, "fields": "files(id, name)"}
    if drive_id:
        params["driveId"] = drive_id
        params["corpora"] = "drive"
        params["includeItemsFromAllDrives"] = True
        params["supportsAllDrives"] = True
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    if drive_id:
        file_metadata["driveId"] = drive_id
    folder = service.files().create(body=file_metadata, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def create_subfolder(parent_folder_id, subfolder_name):
    service = get_google_drive_service()
    drive_id = get_shared_drive_id()
    query = f"name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false and '{parent_folder_id}' in parents"
    params = {"q": query, "fields": "files(id, name)"}
    if drive_id:
        params["driveId"] = drive_id
        params["corpora"] = "drive"
        params["includeItemsFromAllDrives"] = True
        params["supportsAllDrives"] = True
    results = service.files().list(**params).execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    file_metadata = {
        "name": subfolder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_folder_id]
    }
    if drive_id:
        file_metadata["driveId"] = drive_id
    folder = service.files().create(body=file_metadata, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def upload_file_to_drive(file_path, folder_id=None):
    service = get_google_drive_service()
    drive_id = get_shared_drive_id()
    file_metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    if drive_id:
        file_metadata["driveId"] = drive_id
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True
        ).execute()
        return file.get("webViewLink")
    except Exception as e:
        import traceback
        try:
            from googleapiclient.errors import HttpError
            if isinstance(e, HttpError):
                st.error(f"Erro ao fazer upload para o Google Drive: {e}\n\nDetalhes: {e.content}")
            else:
                st.error(f"Erro inesperado ao fazer upload para o Google Drive: {e}\n\n{traceback.format_exc()}")
        except ImportError:
            st.error(f"Erro inesperado ao fazer upload para o Google Drive: {e}\n\n{traceback.format_exc()}")
        return None
