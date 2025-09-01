# backend/VRP_SERVICE/service_google_drive.py
from __future__ import annotations

import os, io, json, tempfile
from pathlib import Path
from typing import Optional, Tuple

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

# ----------------- helpers de import opcionais -----------------
def _st():
    try:
        import streamlit as st
        return st
    except Exception:
        return None

def _google_core():
    try:
        import google.auth.transport.requests as google_requests
        from google.oauth2.service_account import Credentials as SA
        from google.oauth2.credentials import Credentials as UserCreds
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
        from googleapiclient.errors import HttpError
        return {
            "requests": google_requests,
            "SA": SA,
            "UserCreds": UserCreds,
            "Flow": Flow,
            "build": build,
            "MediaFileUpload": MediaFileUpload,
            "MediaIoBaseUpload": MediaIoBaseUpload,
            "HttpError": HttpError,
        }
    except Exception:
        return None

def _secrets(section: str, key: str, default=None):
    st = _st()
    if not st: return default
    try:
        return st.secrets.get(section, {}).get(key, default) if section else st.secrets.get(key, default)
    except Exception:
        return default

# ----------------- modo e credenciais -----------------
def _token_path() -> Path:
    p = Path(".streamlit") / "gdrive_token.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _build_service_with_service_account():
    g = _google_core(); st = _st()
    if not (g and st): return None, "google-libs faltando"

    svc_info = st.secrets.get("google_drive_service_account", None)
    root_folder = _secrets("features", "google_drive_root_folder_id")
    # Com SA precisamos de uma pasta em Unidade Compartilhada
    if not svc_info or not root_folder:
        return None, "service_account/root_folder ausente"

    try:
        creds = g["SA"].from_service_account_info(dict(svc_info), scopes=SCOPES)
        service = g["build"]("drive", "v3", credentials=creds)
        return service, "service_account"
    except Exception as e:
        return None, f"falha SA: {e}"

def _build_service_with_oauth() -> Tuple[Optional[object], str]:
    g = _google_core(); st = _st()
    if not (g and st): return None, "google-libs faltando"

    client = st.secrets.get("google_drive", None)
    if not client:
        return None, "oauth config ausente"

    # monta client_config in-memory
    client_config = {
        "installed": {
            "client_id": client.get("client_id"),
            "project_id": client.get("project_id"),
            "auth_uri": client.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": client.get("token_uri", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": client.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_secret": client.get("client_secret"),
            "redirect_uris": client.get("redirect_uris", []),
        }
    }

    # 1) tenta carregar token salvo
    tok_path = _token_path()
    if tok_path.exists():
        try:
            creds = g["UserCreds"].from_authorized_user_file(str(tok_path), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                g["requests"].Request()
                creds.refresh(g["requests"].Request())
                tok_path.write_text(creds.to_json())
            service = g["build"]("drive", "v3", credentials=creds)
            return service, "oauth_cached"
        except Exception:
            pass  # cai para o fluxo de autorização

    # 2) fluxo OAuth dentro do Streamlit (code via query params)
    # precisa de uma redirect URI presente em secrets['google_drive']['redirect_uris'][0]
    redirect_uris = client_config["installed"]["redirect_uris"]
    if not redirect_uris:
        return None, "oauth sem redirect_uris"

    redirect_uri = redirect_uris[0]
    Flow = g["Flow"]
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)

    # busca ?code=... na URL
    try:
        qp = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
        code = (qp.get("code") or [None])[0]
    except Exception:
        code = None

    if not code:
        auth_url, _state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        # Renderiza link para o usuário autorizar
        st.warning("Para conectar ao seu Google Drive (Meu Drive), clique abaixo e depois volte para este app:")
        st.link_button("Autorizar Google Drive", auth_url, use_container_width=True)
        st.stop()

    # temos o code => troca por token
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        tok_path.write_text(creds.to_json())
        service = g["build"]("drive", "v3", credentials=creds)
        return service, "oauth_new"
    except Exception as e:
        st.error(f"Falha ao finalizar OAuth: {e}")
        return None, "oauth erro"

def get_google_drive_service():
    """
    Tenta Service Account + Shared Drive; se não conseguir, cai para OAuth do usuário.
    Retorna (service, modo) onde modo ∈ {'service_account','oauth_cached','oauth_new'}.
    """
    # 1) tenta SA
    service, mode = _build_service_with_service_account()
    if service:
        return service, mode

    # 2) fallback OAuth user
    service, mode = _build_service_with_oauth()
    if service:
        return service, mode

    return None, "indisponível"

def get_root_folder_id_for_upload(service, mode: str) -> Optional[str]:
    """
    Decide a pasta pai:
    - SA: usa obrigatoriamente a pasta configurada (Shared Drive).
    - OAuth: usa 'google_drive_root_folder_id' se existir; senão envia pro Meu Drive (sem parents).
    """
    root = _secrets("features", "google_drive_root_folder_id")
    if mode.startswith("service_account"):
        return root  # precisa existir
    # OAuth: opcional
    return root or None

# ----------------- operações -----------------
def create_folder(name: str) -> Optional[str]:
    g = _google_core(); st = _st()
    service, mode = get_google_drive_service()
    if not (g and st and service): return None
    parent = get_root_folder_id_for_upload(service, mode)

    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    params = {"q": q, "fields": "files(id,name)"}
    # supportsAllDrives = True é seguro para ambos os modos
    params.update({"supportsAllDrives": True, "includeItemsFromAllDrives": True})
    if parent:
        q += f" and '{parent}' in parents"
        params["q"] = q

    found = service.files().list(**params).execute().get("files", [])
    if found:
        return found[0]["id"]

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent:
        meta["parents"] = [parent]
    f = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return f.get("id")

def create_subfolder(parent_id: str, name: str) -> Optional[str]:
    service, _mode = get_google_drive_service()
    if not service: return None
    q = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false and '{parent_id}' in parents"
    )
    params = {"q": q, "fields": "files(id,name)", "supportsAllDrives": True, "includeItemsFromAllDrives": True}
    found = service.files().list(**params).execute().get("files", [])
    if found:
        return found[0]["id"]

    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    f = service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return f.get("id")

def _mime_from_name(name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")

def upload_file_to_drive(file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
    g = _google_core(); st = _st()
    service, mode = get_google_drive_service()
    if not (g and st and service): return None

    parent = folder_id or get_root_folder_id_for_upload(service, mode)
    meta = {"name": os.path.basename(file_path)}
    if parent: meta["parents"] = [parent]

    media = g["MediaFileUpload"](file_path, resumable=True)
    try:
        f = service.files().create(body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True).execute()
        return f.get("webViewLink")
    except Exception as e:
        st.error(f"Upload Drive falhou: {e}")
        return None

def upload_bytes_to_drive(data: bytes, filename: str, folder_id: Optional[str] = None) -> Optional[str]:
    g = _google_core(); st = _st()
    service, mode = get_google_drive_service()
    if not (g and st and service): return None

    parent = folder_id or get_root_folder_id_for_upload(service, mode)
    meta = {"name": filename}
    if parent: meta["parents"] = [parent]
    media = g["MediaIoBaseUpload"](io.BytesIO(data), mimetype=_mime_from_name(filename), resumable=True)
    try:
        f = service.files().create(body=meta, media_body=media, fields="id,webViewLink", supportsAllDrives=True).execute()
        return f.get("webViewLink")
    except Exception as e:
        st.error(f"Upload Drive falhou: {e}")
        return None

def delete_from_drive(file_id: str) -> bool:
    st = _st()
    service, _mode = get_google_drive_service()
    if not service:
        if st: st.warning("Drive não configurado; não foi possível excluir.")
        return False
    try:
        service.files().delete(fileId=file_id, supportsAllDrives=True).execute()
        return True
    except Exception as e:
        if st: st.error(f"Falha ao excluir no Drive: {e}")
        return False
