# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_SERVICE\storage_service.py
"""
Gerencia fotos:
- Diretório por VRP: uploads/VRP_{site_id}/CK_{checklist_id}/arquivo.jpg
- save_photo_bytes(): salva + registra (com vrp_site_id e checklist_id)
- list_photos(checklist_id), list_photos_by_vrp(vrp_site_id)
- update_photo_flags(), delete_photo()
"""
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image
from io import BytesIO
from uuid import uuid4

from .export_paths import UPLOADS_DIR
from backend.VRP_DATABASE.database import get_conn

def _vrp_ck_dir(vrp_site_id: int, checklist_id: int) -> Path:
    d = UPLOADS_DIR / f"VRP_{vrp_site_id}" / f"CK_{checklist_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_photo_bytes(
    vrp_site_id: int,
    checklist_id: int,
    original_name: str,
    data: bytes,
    label: str,
    caption: str,
    include: bool,
    order: int = 1,
) -> str:
    """Salva bytes como JPG único e grava em 'photos'. Retorna caminho salvo."""
    folder = _vrp_ck_dir(vrp_site_id, checklist_id)
    # nome único: ordem_label_uuid.jpg
    base = f"{order:03d}_{uuid4().hex[:8]}.jpg"
    p = folder / base
    Image.open(BytesIO(data)).convert("RGB").save(p, "JPEG", quality=90)

    conn = get_conn()
    conn.execute(
        """INSERT INTO photos (vrp_site_id, checklist_id, label, file_path, caption, include_in_report, display_order)
           VALUES (?,?,?,?,?,?,?)""",
        (vrp_site_id, checklist_id, label, str(p), caption, int(include), order),
    )
    conn.commit(); conn.close()
    return str(p)

def list_photos(checklist_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM photos WHERE checklist_id=? ORDER BY display_order, id",
        (checklist_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def list_photos_by_vrp(vrp_site_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.execute(
        "SELECT * FROM photos WHERE vrp_site_id=? ORDER BY checklist_id, display_order, id",
        (vrp_site_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def update_photo_flags(photo_id: int, include: bool, order: int, caption: str, label: str | None = None):
    conn = get_conn()
    if label is None:
        conn.execute(
            "UPDATE photos SET include_in_report=?, display_order=?, caption=? WHERE id=?",
            (int(include), order, caption, photo_id),
        )
    else:
        conn.execute(
            "UPDATE photos SET include_in_report=?, display_order=?, caption=?, label=? WHERE id=?",
            (int(include), order, caption, label, photo_id),
        )
    conn.commit(); conn.close()

def delete_photo(photo_id: int):
    """Remove do disco e do banco."""
    conn = get_conn()
    row = conn.execute("SELECT file_path FROM photos WHERE id=?", (photo_id,)).fetchone()
    if row:
        try:
            Path(row["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit(); conn.close()
