# file: backend/VRP_SERVICE/storage_service.py
from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
from uuid import uuid4

import streamlit as st  # <— usamos para recuperar a sessão
from backend.VRP_SERVICE.export_paths import SESSION_UPLOADS_DIR
from backend.VRP_DATABASE.database import get_conn

def _session_key() -> str:
    if "_session_key" not in st.session_state:
        st.session_state["_session_key"] = uuid4().hex[:12]
    return st.session_state["_session_key"]

def _base_session_dir() -> Path:
    d = SESSION_UPLOADS_DIR / f"_{_session_key()}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _vrp_ck_dir(vrp_site_id: int, checklist_id: int) -> Path:
    """Pasta temporária por sessão."""
    d = _base_session_dir() / f"VRP_{vrp_site_id}" / f"CK_{checklist_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _safe_name(original_name: str, order: int) -> str:
    base = os.path.basename(original_name).strip().replace(" ", "_")
    name, ext = os.path.splitext(base)
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"
    h = uuid4().hex[:8]
    return f"{order:03d}_{(name or 'img')[:40]}_{h}{ext.lower()}"

def save_photo_bytes(
    vrp_site_id: int,
    checklist_id: int,
    original_name: str,
    data: bytes,
    label: str,
    caption: str,
    include: bool,
    order: int = 1,
) -> int:
    if not data:
        raise ValueError("Nenhum dado de imagem recebido.")

    folder = _vrp_ck_dir(vrp_site_id, checklist_id)
    filename = _safe_name(original_name, order)
    local_path = folder / filename
    local_path.write_bytes(data)

    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO photos (vrp_site_id, checklist_id, file_path, label, caption,
                                include_in_report, display_order, drive_file_id, ephemeral)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                vrp_site_id,
                checklist_id,
                str(local_path),
                label,
                caption,
                int(bool(include)),
                int(order),
                None,   # drive_file_id sempre None
                1,      # EFÊMERO
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def list_photos(checklist_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, vrp_site_id, checklist_id, file_path, label, caption,
                   include_in_report, display_order, drive_file_id, ephemeral
            FROM photos
            WHERE checklist_id = ?
            ORDER BY display_order, id
            """,
            (checklist_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def list_photos_by_vrp(vrp_site_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, vrp_site_id, checklist_id, file_path, label, caption,
                   include_in_report, display_order, drive_file_id, ephemeral
            FROM photos
            WHERE vrp_site_id = ?
            ORDER BY checklist_id DESC, display_order, id
            """,
            (vrp_site_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def update_photo_flags(photo_id: int, include: bool, order: int, caption: str, label: Optional[str] = None) -> None:
    conn = get_conn()
    try:
        if label is None:
            conn.execute(
                "UPDATE photos SET include_in_report=?, display_order=?, caption=? WHERE id=?",
                (int(bool(include)), int(order), caption, photo_id),
            )
        else:
            conn.execute(
                "UPDATE photos SET include_in_report=?, display_order=?, caption=?, label=? WHERE id=?",
                (int(bool(include)), int(order), caption, label, photo_id),
            )
        conn.commit()
    finally:
        conn.close()

def delete_photo(photo_id: int) -> bool:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT file_path FROM photos WHERE id=?",
            (photo_id,),
        ).fetchone()

        if row:
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass

        conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def purge_session_photos(checklist_id: Optional[int] = None) -> dict:
    """
    Remove TODAS as fotos efêmeras da sessão atual (ou apenas de um checklist).
    Apaga arquivos e registros (ephemeral=1) sob SESSION_UPLOADS_DIR/_<session_key>/...
    """
    base = _base_session_dir()
    conn = get_conn()
    deleted = 0
    files = 0
    try:
        if checklist_id is None:
            rows = conn.execute(
                "SELECT id, file_path FROM photos WHERE ephemeral=1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, file_path FROM photos WHERE ephemeral=1 AND checklist_id=?",
                (checklist_id,),
            ).fetchall()

        for r in rows:
            try:
                Path(r["file_path"]).unlink(missing_ok=True); files += 1
            except Exception:
                pass
            conn.execute("DELETE FROM photos WHERE id=?", (r["id"],))
            deleted += 1
        conn.commit()
    finally:
        conn.close()

    # tenta remover a pasta da sessão (só se vazia)
    try:
        for p in sorted(base.rglob("*"), reverse=True):
            if p.is_file(): 
                continue
            try: p.rmdir()
            except Exception: pass
        base.rmdir()
    except Exception:
        pass

    return {"rows_deleted": deleted, "files_deleted": files, "session_dir": str(base)}
