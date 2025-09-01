# file: backend/VRP_SERVICE/history_service.py
"""
Rotinas de histórico:
- delete_checklist(): apaga checklist, fotos (arquivos e DB), relatórios (arquivos e DB)
  e, opcionalmente, a VRP se ficar órfã.

Independente de export_paths (usa fallback de caminhos).
Retorno:
  { ok: bool, files_deleted: int, exports_deleted: int, vrp_deleted: bool, reason?: str }
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, Any

from backend.VRP_DATABASE.database import get_conn

# ---------------- Paths robustos (sem depender de export_paths) ----------------
try:
    # Tenta usar export_paths se disponível
    from backend.VRP_SERVICE.export_paths import UPLOADS_DIR as _U, EXPORTS_DIR as _E  # type: ignore
    UPLOADS_DIR = Path(_U)
    EXPORTS_DIR = Path(_E)
except Exception:
    # Fallback: calcula a partir da raiz do repo
    ROOT = Path(__file__).resolve().parents[2]  # .../backend/VRP_SERVICE/ -> repo root
    UPLOADS_DIR = ROOT / "frontend" / "assets" / "uploads"
    EXPORTS_DIR = ROOT / "frontend" / "assets" / "exports"
    for _p in (UPLOADS_DIR, EXPORTS_DIR):
        _p.mkdir(parents=True, exist_ok=True)


def _safe_unlink(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _safe_rmtree(path: Path) -> bool:
    try:
        shutil.rmtree(path, ignore_errors=True)
        return True
    except Exception:
        return False


def delete_checklist(checklist_id: int, delete_vrp_if_orphan: bool = False) -> Dict[str, Any]:
    """
    Exclui:
      - fotos do checklist (arquivos e registros)
      - pasta CK_{checklist} dentro de uploads/VRP_{site}
      - relatório (docx/pdf) e pasta exports/{checklist} quando existir
      - o próprio checklist
      - opcionalmente a VRP se ficar sem checklists
    """
    files_deleted = 0
    exports_deleted = 0
    vrp_deleted = False

    conn = get_conn()
    try:
        # Qual VRP?
        row_ck = conn.execute(
            "SELECT vrp_site_id FROM checklists WHERE id=?",
            (checklist_id,),
        ).fetchone()
        if not row_ck:
            return {"ok": False, "files_deleted": 0, "exports_deleted": 0, "vrp_deleted": False, "reason": "Checklist inexistente"}

        vrp_site_id = row_ck["vrp_site_id"]

        # --- Fotos: remove arquivos e registros
        rows_ph = conn.execute(
            "SELECT id, file_path FROM photos WHERE checklist_id=?",
            (checklist_id,),
        ).fetchall()

        for r in rows_ph:
            if r["file_path"]:
                p = Path(r["file_path"])
                if p.exists():
                    if _safe_unlink(p):
                        files_deleted += 1

        conn.execute("DELETE FROM photos WHERE checklist_id=?", (checklist_id,))
        conn.commit()

        # Remove a pasta CK_{checklist}
        ck_dir = UPLOADS_DIR / f"VRP_{vrp_site_id}" / f"CK_{checklist_id}"
        if ck_dir.exists():
            if _safe_rmtree(ck_dir):
                exports_deleted += 1

        # --- Relatórios
        row_rep = conn.execute(
            "SELECT docx_path, pdf_path FROM reports WHERE checklist_id=?",
            (checklist_id,),
        ).fetchone()
        if row_rep:
            for col in ("docx_path", "pdf_path"):
                p = Path(row_rep[col]) if row_rep[col] else None
                if p and p.exists():
                    if _safe_unlink(p):
                        exports_deleted += 1

            # Tenta apagar pasta padrão exports/{checklist}
            exp_dir = EXPORTS_DIR / f"{checklist_id}"
            if exp_dir.exists():
                _safe_rmtree(exp_dir)

            conn.execute("DELETE FROM reports WHERE checklist_id=?", (checklist_id,))
            conn.commit()

        # --- Remove o checklist
        conn.execute("DELETE FROM checklists WHERE id=?", (checklist_id,))
        conn.commit()

        # --- Opcional: remove a VRP se ficar órfã
        if delete_vrp_if_orphan and vrp_site_id:
            n = conn.execute(
                "SELECT COUNT(1) AS n FROM checklists WHERE vrp_site_id=?",
                (vrp_site_id,),
            ).fetchone()["n"]
            if n == 0:
                vrp_dir = UPLOADS_DIR / f"VRP_{vrp_site_id}"
                if vrp_dir.exists():
                    _safe_rmtree(vrp_dir)
                conn.execute("DELETE FROM vrp_sites WHERE id=?", (vrp_site_id,))
                conn.commit()
                vrp_deleted = True

        return {
            "ok": True,
            "files_deleted": files_deleted,
            "exports_deleted": exports_deleted,
            "vrp_deleted": vrp_deleted,
        }

    except Exception as e:
        return {
            "ok": False,
            "files_deleted": files_deleted,
            "exports_deleted": exports_deleted,
            "vrp_deleted": vrp_deleted,
            "reason": str(e),
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
