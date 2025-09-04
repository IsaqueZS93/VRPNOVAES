# file: backend/VRP_SERVICE/storage_service.py
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Iterable, Dict, Any
import os
import shutil
import uuid

from backend.VRP_DATABASE.database import get_conn
from backend.VRP_SERVICE.export_paths import SESSION_UPLOADS_DIR

# --------------------- util ---------------------
def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _sanitize_filename(name: str) -> str:
    # Remove separadores/pastas e caracteres problemáticos
    base = os.path.basename(name)
    return "".join(ch for ch in base if ch.isalnum() or ch in (".", "_", "-", " ")).strip() or "file"

def _ensure_tables():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            checklist_id     INTEGER NOT NULL,
            vrp_site_id      INTEGER NOT NULL,
            file_path        TEXT NOT NULL,        -- caminho absoluto ou relativo
            include_in_report INTEGER NOT NULL DEFAULT 1,
            display_order    INTEGER NOT NULL DEFAULT 1,
            label            TEXT,
            caption          TEXT,
            ephemeral        INTEGER NOT NULL DEFAULT 1,  -- 1=session temp, 0=permanente
            created_at       TEXT NOT NULL
        );
    """)
    # Índices úteis
    conn.execute("CREATE INDEX IF NOT EXISTS idx_photos_checklist ON photos(checklist_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_photos_vrp ON photos(vrp_site_id)")
    conn.commit()
    conn.close()

_ensure_tables()

def _session_dir_for(checklist_id: int) -> Path:
    d = SESSION_UPLOADS_DIR / f"ck_{checklist_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def save_photo_bytes(
    vrp_site_id: int,
    checklist_id: int,
    original_name: str,
    data: bytes,
    label: str = "",
    caption: str = "",
    include: bool = True,
    order: int = 1,
) -> int:
    """
    Salva bytes da imagem em pasta de sessão por checklist e registra no DB.
    Retorna o id do registro em `photos`.
    """
    if not data:
        raise ValueError("Dados de imagem vazios.")

    # Gera nome único preservando extensão
    sanitized = _sanitize_filename(original_name or "image")
    ext = "." + sanitized.split(".")[-1].lower() if "." in sanitized else ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex}{ext}"

    out_dir = _session_dir_for(checklist_id)
    out_path = (out_dir / filename).resolve()

    with open(out_path, "wb") as f:
        f.write(data)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO photos (
            checklist_id, vrp_site_id, file_path,
            include_in_report, display_order, label, caption,
            ephemeral, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            int(checklist_id),
            int(vrp_site_id),
            str(out_path),
            1 if include else 0,
            int(order),
            label or "",
            caption or "",
            _now_iso(),
        ),
    )
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return int(pid)

def list_photos(checklist_id: int) -> Iterable[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, checklist_id, vrp_site_id, file_path, include_in_report,
               display_order, label, caption, ephemeral, created_at
        FROM photos
        WHERE checklist_id = ?
        ORDER BY display_order ASC, id ASC
        """,
        (checklist_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def list_photos_by_vrp(vrp_site_id: int) -> Iterable[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, checklist_id, vrp_site_id, file_path, include_in_report,
               display_order, label, caption, ephemeral, created_at
        FROM photos
        WHERE vrp_site_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (vrp_site_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_photo_flags(photo_id: int, include: bool, order: int, caption: str, label: str) -> None:
    conn = get_conn()
    conn.execute(
        """
        UPDATE photos
           SET include_in_report = ?,
               display_order     = ?,
               caption           = ?,
               label             = ?
         WHERE id = ?
        """,
        (1 if include else 0, int(order), caption or "", label or "", int(photo_id)),
    )
    conn.commit()
    conn.close()

def _safe_delete_file(path_str: str) -> bool:
    """
    Deleta o arquivo apenas se estiver dentro de SESSION_UPLOADS_DIR (segurança).
    Retorna True se deletou, False caso contrário.
    """
    try:
        p = Path(path_str).resolve()
        base = SESSION_UPLOADS_DIR.resolve()
        if base in p.parents or p == base:
            if p.exists():
                p.unlink()
                # Se o diretório ck_xxx ficou vazio, remove para manter limpo
                if p.parent.exists() and not any(p.parent.iterdir()):
                    shutil.rmtree(p.parent, ignore_errors=True)
                return True
    except Exception:
        pass
    return False

def delete_photo(photo_id: int) -> None:
    conn = get_conn()
    row = conn.execute("SELECT file_path FROM photos WHERE id = ?", (photo_id,)).fetchone()
    if row:
        _safe_delete_file(row["file_path"])
        conn.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        conn.commit()
    conn.close()

def purge_session_photos(checklist_id: int) -> Dict[str, int]:
    """
    Remove todos os registros 'ephemeral=1' deste checklist e apaga
    os arquivos correspondentes, apenas se estiverem em SESSION_UPLOADS_DIR.
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, file_path FROM photos WHERE checklist_id = ? AND ephemeral = 1",
        (checklist_id,),
    ).fetchall()

    files_deleted = 0
    for r in rows:
        if _safe_delete_file(r["file_path"]):
            files_deleted += 1

    conn.execute("DELETE FROM photos WHERE checklist_id = ? AND ephemeral = 1", (checklist_id,))
    conn.commit()

    # Remove a pasta ck_<id> se existir
    ck_dir = _session_dir_for(checklist_id)
    if ck_dir.exists():
        try:
            shutil.rmtree(ck_dir, ignore_errors=True)
        except Exception:
            pass

    rows_deleted = len(rows)
    conn.close()
    return {"rows_deleted": rows_deleted, "files_deleted": files_deleted}
