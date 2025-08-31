"""
Gerencia fotos:
- Diretório por VRP: uploads/VRP_{site_id}/CK_{checklist_id}/arquivo.ext
- save_photo_bytes(): salva local + (opcionalmente) Google Drive, e registra no DB
- list_photos(checklist_id), list_photos_by_vrp(vrp_site_id) (tolerantes ao esquema)
- update_photo_flags(), delete_photo()
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import os
from uuid import uuid4

from backend.VRP_SERVICE.export_paths import UPLOADS_DIR
from backend.VRP_DATABASE.database import get_conn

# ---- Integração opcional com Google Drive (se o módulo existir) ----
_HAS_DRIVE = False
_drive = None
try:
    from backend.VRP_SERVICE import service_google_drive as _drive  # type: ignore
    _HAS_DRIVE = True
except Exception:
    _HAS_DRIVE = False
    _drive = None


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

def _ensure_drive_column():
    """Garante a existência da coluna drive_file_id em photos (se não existir)."""
    conn = get_conn()
    try:
        cols = conn.execute("PRAGMA table_info(photos)").fetchall()
        names = {c["name"] for c in cols}
        if "drive_file_id" not in names:
            conn.execute("ALTER TABLE photos ADD COLUMN drive_file_id TEXT")
            conn.commit()
    finally:
        conn.close()

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
    Salva bytes como arquivo local (sempre, para uso no DOCX) e, se disponível,
    envia também ao Google Drive. Grava entrada em 'photos' e retorna o id da foto.
    """
    if not data:
        raise ValueError("Nenhum dado de imagem recebido.")

    # 1) Caminho local (sempre)
    folder = _vrp_ck_dir(vrp_site_id, checklist_id)
    filename = _safe_name(original_name, order)
    local_path = folder / filename
    try:
        local_path.write_bytes(data)  # salva local SEM depender de PIL
    except Exception as e:
        # falha em disco precisa ser explícita
        raise RuntimeError(f"Falha ao salvar arquivo local '{local_path}': {e}")

    # 2) (Opcional) Google Drive — dentro do root_folder_id (se configurado) ou Shared Drive
    drive_file_id: Optional[str] = None
    if _HAS_DRIVE and _drive is not None:
        try:
            # tenta usar root_folder do secrets; senão cai para create_folder em Shared Drive
            base_parent = None
            if hasattr(_drive, "get_root_folder_id"):
                base_parent = _drive.get_root_folder_id()
            if not base_parent and hasattr(_drive, "get_shared_drive_id"):
                # não usamos diretamente a Shared Drive como pai sem pasta; create_folder cuida disso
                base_parent = _drive.get_shared_drive_id()

            # cria/obtém pasta "VRP_Fotos" no parent configurado
            if base_parent and hasattr(_drive, "create_subfolder"):
                main_folder_id = _drive.create_subfolder(base_parent, "VRP_Fotos")
            else:
                # fallback: procura/cria "VRP_Fotos" no escopo padrão
                main_folder_id = _drive.create_folder("VRP_Fotos")

            # subpasta específica da coleta
            sub_folder_name = f"VRP_{vrp_site_id}_CK_{checklist_id}"
            if hasattr(_drive, "create_subfolder"):
                sub_folder_id = _drive.create_subfolder(main_folder_id, sub_folder_name)
            else:
                sub_folder_id = main_folder_id  # melhor do que falhar

            # upload do binário
            link_or_id = _drive.upload_bytes_to_drive(data, filename, sub_folder_id)
            drive_file_id = str(link_or_id) if link_or_id else None
        except Exception:
            # não quebra o fluxo: seguimos só com o local_path
            drive_file_id = None

    # 3) Garantir coluna drive_file_id (bancos antigos)
    _ensure_drive_column()

    # 4) Inserir no DB
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO photos (vrp_site_id, checklist_id, file_path, label, caption, include_in_report, display_order, drive_file_id)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                vrp_site_id,
                checklist_id,
                str(local_path),
                label,
                caption,
                int(bool(include)),
                int(order),
                drive_file_id,
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
    Remove o registro do banco, tenta excluir o arquivo local
    e (se houver) tenta excluir no Google Drive.
    """
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT file_path, drive_file_id FROM photos WHERE id=?",
            (photo_id,),
        ).fetchone()

        if row:
            # Remove arquivo local
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass

            # (Opcional) exclui do Drive
            drive_id = None
            # sqlite3.Row tem .keys(); se faltar a coluna em DB antigo, tratamos como None
            try:
                if "drive_file_id" in row.keys():
                    drive_id = row["drive_file_id"]
            except Exception:
                drive_id = row["drive_file_id"] if "drive_file_id" in row else None

            if _HAS_DRIVE and _drive is not None and drive_id:
                try:
                    if hasattr(_drive, "delete_from_drive"):
                        _drive.delete_from_drive(drive_id)
                except Exception:
                    pass

        conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
        conn.commit()
        return True
    finally:
        conn.close()
