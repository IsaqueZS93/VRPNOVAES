# file: backend/VRP_SERVICE/storage_service.py
"""
Gerencia fotos (somente armazenamento local):
- Diretório por VRP: uploads/VRP_{site_id}/CK_{checklist_id}/arquivo.ext
- save_photo_bytes(): salva local e registra no DB
- list_photos(checklist_id), list_photos_by_vrp(vrp_site_id) (tolerantes ao esquema)
- update_photo_flags(), delete_photo()
- purge_photos_older_than(days): limpeza opcional por retenção
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import os
from uuid import uuid4
from datetime import datetime, timedelta

from backend.VRP_SERVICE.export_paths import UPLOADS_DIR
from backend.VRP_DATABASE.database import get_conn


# ----------------------- Utils de caminho/DB -----------------------
def _vrp_ck_dir(vrp_site_id: int, checklist_id: int) -> Path:
    """Pasta padrão para armazenar as fotos localmente."""
    d = UPLOADS_DIR / f"VRP_{vrp_site_id}" / f"CK_{checklist_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(original_name: str, order: int) -> str:
    """Gera um nome seguro e único, preservando extensão quando possível."""
    base = os.path.basename(original_name).strip().replace(" ", "_")
    name, ext = os.path.splitext(base)
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"  # fallback
    h = uuid4().hex[:8]
    return f"{order:03d}_{(name or 'img')[:40]}_{h}{ext.lower()}"


def _has_column(conn, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c["name"] == column for c in cols)


# ------------------------------ API ------------------------------
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
    """
    Salva bytes como arquivo local (para uso no DOCX) e grava a entrada em 'photos'.
    Retorna o id da foto.
    """
    if not data:
        raise ValueError("Nenhum dado de imagem recebido.")

    # 1) Caminho local (sempre)
    folder = _vrp_ck_dir(vrp_site_id, checklist_id)
    filename = _safe_name(original_name, order)
    local_path = folder / filename
    try:
        local_path.write_bytes(data)
    except Exception as e:
        raise RuntimeError(f"Falha ao salvar arquivo local '{local_path}': {e}")

    # 2) Inserir no DB
    conn = get_conn()
    try:
        # drive_file_id fica sempre NULL (não usamos nuvem)
        cur = conn.execute(
            """
            INSERT INTO photos (
                vrp_site_id, checklist_id, file_path, label, caption,
                include_in_report, display_order, drive_file_id
            ) VALUES (?,?,?,?,?,?,?,NULL)
            """,
            (
                vrp_site_id,
                checklist_id,
                str(local_path),
                label,
                caption,
                int(bool(include)),
                int(order),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_photos(checklist_id: int) -> List[Dict[str, Any]]:
    """Lista as fotos de um checklist (ordem + id). Tolerante à ausência de drive_file_id."""
    conn = get_conn()
    try:
        has_drive = _has_column(conn, "photos", "drive_file_id")
        select_sql = (
            "SELECT id, vrp_site_id, checklist_id, file_path, label, caption, "
            "include_in_report, display_order"
            + (", drive_file_id " if has_drive else ", NULL AS drive_file_id ")
            + "FROM photos WHERE checklist_id=? ORDER BY display_order, id"
        )
        rows = conn.execute(select_sql, (checklist_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_photos_by_vrp(vrp_site_id: int) -> List[Dict[str, Any]]:
    """Lista todas as fotos de uma VRP (todas as coletas), mais novo checklist primeiro. Tolerante ao esquema."""
    conn = get_conn()
    try:
        has_drive = _has_column(conn, "photos", "drive_file_id")
        select_sql = (
            "SELECT id, vrp_site_id, checklist_id, file_path, label, caption, "
            "include_in_report, display_order"
            + (", drive_file_id " if has_drive else ", NULL AS drive_file_id ")
            + "FROM photos WHERE vrp_site_id=? ORDER BY checklist_id DESC, display_order, id"
        )
        rows = conn.execute(select_sql, (vrp_site_id,)).fetchall()
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
    """
    Remove o registro do banco e tenta excluir o arquivo local.
    (Sem integração com nuvem.)
    """
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


# ------------------------------ Limpeza opcional ------------------------------
def purge_photos_older_than(days: int) -> Dict[str, int]:
    """
    Apaga **arquivos locais** e **registros** de fotos com created_at mais antigo do que N dias.
    Útil para manter apenas por um tempo até baixar os relatórios.

    Retorna {"deleted_rows": X, "deleted_files": Y}.
    """
    cutoff = datetime.utcnow() - timedelta(days=max(0, days))
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    try:
        # Seleciona as fotos que serão apagadas
        has_created = _has_column(conn, "photos", "created_at")
        if not has_created:
            # se o DB for muito antigo, não arriscar — não apaga nada
            return {"deleted_rows": 0, "deleted_files": 0}

        rows = conn.execute(
            "SELECT id, file_path FROM photos WHERE created_at < ?",
            (cutoff_str,),
        ).fetchall()

        deleted_files = 0
        for r in rows:
            try:
                Path(r["file_path"]).unlink(missing_ok=True)
                deleted_files += 1
            except Exception:
                pass

        conn.execute("DELETE FROM photos WHERE created_at < ?", (cutoff_str,))
        conn.commit()
        return {"deleted_rows": len(rows), "deleted_files": deleted_files}
    finally:
        conn.close()
