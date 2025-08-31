# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_SERVICE\history_service.py
"""
Exclusão orquestrada de um checklist:
- Remove arquivos das fotos e exports (DOCX/PDF)
- Remove pasta CK_{checklist} e, se ficar vazia, limpa VRP_{site}
- Exclui registro do checklist (CASCADE remove photos/reports no DB)
- Opcional: exclui a VRP se ficar órfã (sem outros checklists)
"""

from pathlib import Path
import shutil
from typing import Dict, Any

from backend.VRP_DATABASE.database import get_conn
from .export_paths import UPLOADS_DIR, EXPORTS_DIR

def _safe_unlink(path_str: str) -> bool:
    try:
        p = Path(path_str)
        if p.is_file():
            p.unlink(missing_ok=True)
            return True
    except Exception:
        pass
    return False

def _rmtree_if_exists(p: Path) -> bool:
    try:
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            return True
    except Exception:
        pass
    return False

def delete_checklist(checklist_id: int, delete_vrp_if_orphan: bool = False) -> Dict[str, Any]:
    """
    Exclui um checklist e seus artefatos.
    Retorna um resumo com contagens de arquivos e flags de limpeza.
    """
    summary = {
        "ok": False,
        "checklist_id": checklist_id,
        "files_deleted": 0,
        "exports_deleted": False,
        "ck_folder_deleted": False,
        "vrp_folder_deleted": False,
        "vrp_deleted": False,
        "reason": "",
    }

    conn = get_conn()
    ck = conn.execute(
        "SELECT id, vrp_site_id FROM checklists WHERE id=?", (checklist_id,)
    ).fetchone()

    if not ck:
        summary["reason"] = "Checklist não encontrado"
        conn.close()
        return summary

    vrp_site_id = ck["vrp_site_id"]

    # 1) Coletar e remover arquivos de fotos
    photos = conn.execute(
        "SELECT file_path FROM photos WHERE checklist_id=?", (checklist_id,)
    ).fetchall()
    for row in photos:
        if row and row["file_path"]:
            if _safe_unlink(row["file_path"]):
                summary["files_deleted"] += 1

    # 2) Remover arquivos de exports (DOCX/PDF) e pasta de exports do checklist
    rep = conn.execute(
        "SELECT docx_path, pdf_path FROM reports WHERE checklist_id=?", (checklist_id,)
    ).fetchone()
    if rep:
        if rep["docx_path"]:
            _safe_unlink(rep["docx_path"])
        if rep["pdf_path"]:
            _safe_unlink(rep["pdf_path"])

    ck_export_dir = EXPORTS_DIR / f"{checklist_id}"
    summary["exports_deleted"] = _rmtree_if_exists(ck_export_dir)

    # 3) Remover pasta CK específica dentro da VRP
    ck_upload_dir = UPLOADS_DIR / f"VRP_{vrp_site_id}" / f"CK_{checklist_id}"
    summary["ck_folder_deleted"] = _rmtree_if_exists(ck_upload_dir)

    # 4) Excluir checklist (CASCADE remove photos/reports no DB)
    conn.execute("DELETE FROM checklists WHERE id=?", (checklist_id,))
    conn.commit()

    # 5) Se solicitado, excluir VRP se ficou órfã (sem outros checklists)
    if delete_vrp_if_orphan and vrp_site_id:
        other = conn.execute(
            "SELECT COUNT(*) AS n FROM checklists WHERE vrp_site_id=?", (vrp_site_id,)
        ).fetchone()
        if other and other["n"] == 0:
            # Remover possível pasta da VRP (se vazia)
            vrp_dir = UPLOADS_DIR / f"VRP_{vrp_site_id}"
            # Se ainda tiver alguma subpasta residual, rmtree; é seguro pois está sob UPLOADS_DIR
            summary["vrp_folder_deleted"] = _rmtree_if_exists(vrp_dir)

            # Remover a VRP do banco
            conn.execute("DELETE FROM vrp_sites WHERE id=?", (vrp_site_id,))
            conn.commit()
            summary["vrp_deleted"] = True

    conn.close()
    summary["ok"] = True
    return summary
