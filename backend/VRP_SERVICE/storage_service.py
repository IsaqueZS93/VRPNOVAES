"""
Gerencia fotos:
- Diretório por VRP: uploads/VRP_{site_id}/CK_{checklist_id}/arquivo.ext
- save_photo_bytes(): salva local + (opcionalmente) Google Drive, e registra no DB
- list_photos(checklist_id), list_photos_by_vrp(vrp_site_id)
- update_photo_flags(), delete_photo()
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import hashlib
from uuid import uuid4

from backend.VRP_SERVICE.export_paths import UPLOADS_DIR
from backend.VRP_DATABASE.database import get_conn

# ---- Integração opcional com Google Drive (se o módulo existir) ----
_HAS_DRIVE = False
_drive = None
try:
    # O módulo é opcional. Só usamos se existir.
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
        ext = ".jpg"  # fallback de extensão
    h = uuid4().hex[:8]
    return f"{order:03d}_{name or 'img'}_{h}{ext.lower()}"

def _ensure_drive_column():
    """Garante a existência da coluna drive_file_id em photos (se não existir)."""
    conn = get_conn()
    cols = conn.execute("PRAGMA table_info(photos)").fetchall()
    names = {c["name"] for c in cols}
    if "drive_file_id" not in names:
        conn.execute("ALTER TABLE photos ADD COLUMN drive_file_id TEXT")
        conn.commit()
    conn.close()


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

    # 1) Caminho local
    folder = _vrp_ck_dir(vrp_site_id, checklist_id)
    filename = _safe_name(original_name, order)
    local_path = folder / filename
    local_path.write_bytes(data)  # salva local SEM depender de PIL

    # 2) (Opcional) Google Drive
    drive_file_id: Optional[str] = None
    if _HAS_DRIVE and _drive is not None:
        try:
            main_folder_id = _drive.create_folder("VRP_Fotos")
            sub_folder_id = _drive.create_subfolder(main_folder_id, f"VRP_{vrp_site_id}_CK_{checklist_id}")
            # up no mesmo nome do arquivo local
            link_or_id = _drive.upload_bytes_to_drive(data, filename, sub_folder_id)
            # guardar o que o serviço retornar (id/link)
            drive_file_id = str(link_or_id) if link_or_id else None
        except Exception:
            # Não falhar o fluxo: seguimos só com local
            drive_file_id = None

    # 3) Garantir coluna drive_file_id
    _ensure_drive_column()

    # 4) Inserir no DB
    conn = get_conn()
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
    pid = cur.lastrowid
    conn.close()
    return pid


def list_photos(checklist_id: int) -> List[Dict[str, Any]]:
    """Lista as fotos de um checklist (ordem + id)."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, vrp_site_id, checklist_id, file_path, label, caption, include_in_report, display_order, drive_file_id
        FROM photos
        WHERE checklist_id = ?
        ORDER BY display_order, id
        """,
        (checklist_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_photos_by_vrp(vrp_site_id: int) -> List[Dict[str, Any]]:
    """Lista todas as fotos de uma VRP (todas as coletas), mais novo checklist primeiro."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, vrp_site_id, checklist_id, file_path, label, caption, include_in_report, display_order, drive_file_id
        FROM photos
        WHERE vrp_site_id = ?
        ORDER BY checklist_id DESC, display_order, id
        """,
        (vrp_site_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_photo_flags(photo_id: int, include: bool, order: int, caption: str, label: Optional[str] = None) -> None:
    conn = get_conn()
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
    conn.close()


def delete_photo(photo_id: int) -> bool:
    """
    Remove o registro do banco, tenta excluir o arquivo local
    e (se houver) tenta excluir no Google Drive.
    """
    conn = get_conn()
    row = conn.execute(
        "SELECT file_path, drive_file_id FROM photos WHERE id=?",
        (photo_id,),
    ).fetchone()

    if row:
        # Remove arquivo local (se existir)
        try:
            p = Path(row["file_path"])
            p.unlink(missing_ok=True)
        except Exception:
            pass

        # (Opcional) exclui do Drive se suportado e se houver id
        drive_id = row["drive_file_id"]
        if _HAS_DRIVE and _drive is not None and drive_id:
            try:
                # Só chama se o serviço tiver essa função
                if hasattr(_drive, "delete_from_drive"):
                    _drive.delete_from_drive(drive_id)
            except Exception:
                pass

    conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()
    return True
