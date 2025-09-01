# file: frontend/VRP_SCREENS/Screen_Photos.py
"""
Upload de fotos (multi) com metadados por arquivo.
Salva em uploads/VRP_{site}/CK_{checklist}/ e grava vrp_site_id no DB.
Lista para edição (incluir/ordem/legenda/rótulo) e exclusão.
UI padronizada com header/logo, toolbar e cards + LOGS/DIAGNÓSTICO na própria tela.
(Drive desativado: armazenamento apenas local e temporário por sessão)
"""
from __future__ import annotations
from datetime import datetime

import streamlit as st
from backend.VRP_DATABASE.database import get_conn
from backend.VRP_SERVICE.storage_service import (
    save_photo_bytes, list_photos, list_photos_by_vrp,
    update_photo_flags, delete_photo, purge_session_photos,   # <- NOVO
)
from backend.VRP_SERVICE.export_paths import SESSION_UPLOADS_DIR  # <- TROCA: era UPLOADS_DIR
from frontend.VRP_STYLES.layout import (
    page_setup, app_header, toolbar, section_card, pill
)

DEFAULT_LABELS = [
    "Local da execução","Sinalização da área","Tripé de resgate","Tampa de acesso",
    "VRP (antes da manutenção)","Execução do serviço (1)","Execução do serviço (2)","Execução do serviço (3)","Execução do serviço (4)",
    "VRP (antes da execução)","VRP (após execução)","Piloto (antes)","Piloto (após)",
    "Conexões (antes)","Conexões (após)","Fechamento de registros","Abertura de registros","Personalizado"
]

# ------------------------ helpers de log ------------------------
def _init_log():
    st.session_state.setdefault("photo_logs", [])

def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _log(msg: str):
    _init_log()
    st.session_state["photo_logs"].append(f"[{_now()}] {msg}")

# ------------------------ helpers de dados ------------------------
def _get_vrp_site_id(checklist_id: int) -> int | None:
    conn = get_conn()
    row = conn.execute("SELECT vrp_site_id FROM checklists WHERE id=?", (checklist_id,)).fetchone()
    conn.close()
    return row["vrp_site_id"] if row else None

def _get_vrp_label(site_id: int) -> str:
    conn = get_conn()
    r = conn.execute("SELECT place, city, brand, dn FROM vrp_sites WHERE id=?", (site_id,)).fetchone()
    conn.close()
    if not r:
        return f"VRP #{site_id}"
    return f"{r['place']} – {r['city']} • {r['brand']} DN{r['dn'] or ''}"

# ------------------------------ UI ------------------------------
def render():
    _init_log()
    page_setup("VRP • Fotos", icon="📷")
    app_header("Fotos do Checklist", "Envie, organize e selecione as imagens que irão para o relatório.")

    # AVISO: armazenamento temporário por sessão
    st.info("🗂️ **Armazenamento temporário nesta sessão** — as imagens ficam disponíveis apenas até você finalizar/baixar os relatórios ou limpar a sessão.")

    # checklist atual
    cid = st.session_state.get("current_checklist_id")
    if not cid:
        st.warning("Crie/Selecione um checklist primeiro (menu **Histórico**).")
        _log("Abortado: sem checklist atual.")
        return

    site_id = _get_vrp_site_id(cid)
    if not site_id:
        st.error("Checklist sem VRP vinculado.")
        _log(f"Abortado: checklist {cid} sem vrp_site_id.")
        return

    # toolbar (Drive removido) + limpeza de sessão
    actions = toolbar(["Ir para Checklist", "Ir para Relatório", "Limpar fotos desta sessão"])  # <- NOVO item
    if actions["Ir para Checklist"]:
        st.session_state["nav_to"] = "Checklist"; st.rerun()
    if actions["Ir para Relatório"]:
        st.session_state["nav_to"] = "Relatório"; st.rerun()
    if actions["Limpar fotos desta sessão"]:
        with st.expander("Confirmar limpeza das fotos EFÊMERAS desta sessão (apenas deste checklist)", expanded=True):
            ok = st.checkbox("Confirmo remover todas as fotos temporárias **deste checklist**.")
            if st.button("Remover agora", type="secondary", disabled=not ok):
                res = purge_session_photos(checklist_id=cid)
                st.success(f"Limpeza concluída. Registros: {res['rows_deleted']} | Arquivos: {res['files_deleted']}")
                _log(f"Purga de sessão (checklist {cid}): {res}")
                st.rerun()

    # header pills
    pill(f"Checklist #{cid}")
    pill(f"VRP #{site_id}", "success")
    st.caption(_get_vrp_label(site_id))
    _log(f"Tela carregada: checklist_id={cid}, vrp_site_id={site_id}, session_uploads_dir={SESSION_UPLOADS_DIR}")

    # ===== Upload =====
    with section_card("Upload de imagens", "Selecione múltiplos arquivos e defina metadados por imagem."):
        files = st.file_uploader("Selecione imagens", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)

        if files:
            st.write("Defina os metadados **por imagem** e clique em **Salvar todas**.")
            with st.form("form_upload_multi", clear_on_submit=True):
                meta = []
                default_include = st.checkbox("Marcar **Incluir** para todas", value=True)
                for i, f in enumerate(files):
                    with st.expander(f"[{i+1}] {f.name}", expanded=True):
                        c1, c2, c3, c4 = st.columns([2,2,1,1])
                        label_choice = c1.selectbox("Rótulo sugerido", DEFAULT_LABELS, key=f"label_{i}")
                        label = c2.text_input(
                            "Ou rótulo personalizado",
                            value="" if label_choice != "Personalizado" else "",
                            key=f"custom_{i}"
                        )
                        caption = st.text_area(
                            "Observação (para IA — não aparece no relatório)",
                            key=f"cap_{i}", height=80
                        )
                        include = c3.checkbox("Incluir", value=default_include, key=f"inc_{i}")
                        order = c4.number_input("Ordem", 1, 999, value=i+1, step=1, key=f"ord_{i}")
                        meta.append(dict(
                            file=f,
                            label=(label or label_choice),
                            caption=caption,
                            include=include,
                            order=int(order),
                        ))
                submitted = st.form_submit_button("Salvar todas", type="primary")

            if submitted:
                saved = 0
                failed = 0
                with st.status("Salvando imagens...", expanded=True) as status:
                    for m in meta:
                        try:
                            data = m["file"].getvalue()
                            if not data:
                                msg = f"⚠️ {m['file'].name}: arquivo vazio/corrompido (ignorado)."
                                st.warning(msg); _log(msg)
                                failed += 1
                                continue

                            pid = save_photo_bytes(
                                vrp_site_id=site_id,
                                checklist_id=cid,
                                original_name=m["file"].name,
                                data=data,
                                label=m["label"],
                                caption=m["caption"],
                                include=m["include"],
                                order=m["order"],
                            )

                            # Buscar o caminho salvo para log (opcional)
                            conn = get_conn()
                            row = conn.execute("SELECT file_path FROM photos WHERE id=?", (pid,)).fetchone()
                            conn.close()
                            local_path = row["file_path"] if row else "?"

                            st.write(f"✓ {m['file'].name} salvo (id={pid}).")
                            _log(
                                f"Foto salva: id={pid}, ordem={m['order']}, label='{m['label']}', "
                                f"include={m['include']}, local='{local_path}'"
                            )
                            saved += 1
                        except Exception as e:
                            failed += 1
                            st.exception(e)
                            _log(f"ERRO ao salvar '{m['file'].name}': {e}")

                    if failed == 0:
                        status.update(state="complete", label=f"{saved} imagem(ns) salva(s).")
                    else:
                        status.update(
                            state="error",
                            label=f"{saved} salva(s), {failed} falha(s). Ver mensagens acima."
                        )
                st.rerun()
        else:
            st.caption("Dica: você pode arrastar e soltar os arquivos aqui.")

    # ===== Lista / edição do checklist =====
    with section_card("Fotos deste checklist", "Edite ordem, rótulo e inclusão; exclua se necessário."):
        rows = list_photos(cid)
        if not rows:
            st.info("Nenhuma foto neste checklist.")
        else:
            for r in rows:
                with st.expander(f"#{r['id']} • {r['label']}  • ordem {r['display_order']}", expanded=False):
                    st.image(r["file_path"], use_container_width=True, caption=None)
                    if r.get("ephemeral", 1):
                        st.caption("⏳ Armazenamento temporário (sessão atual)")
                    col1, col2, col3, col4 = st.columns([1,1,3,1])
                    include = col1.checkbox("Incluir", value=bool(r["include_in_report"]), key=f"inc_{r['id']}")
                    order = col2.number_input("Ordem", 1, 999, value=int(r["display_order"]), key=f"ord_{r['id']}")
                    label = col3.text_input(
                        "Rótulo (aparece na legenda)",
                        value=r["label"] or "",
                        key=f"lab_{r['id']}"
                    )
                    caption = st.text_area(
                        "Observação (para IA — não aparece no relatório)",
                        value=r["caption"] or "",
                        key=f"cap_{r['id']}", height=80
                    )
                    cA, cB = st.columns(2)
                    if cA.button("Atualizar", key=f"upd_{r['id']}"):
                        try:
                            update_photo_flags(r["id"], include, int(order), caption, label)
                            st.success("Atualizado ✓")
                            _log(f"Foto {r['id']} atualizada: include={include}, order={order}, label='{label}'")
                        except Exception as e:
                            st.exception(e)
                            _log(f"ERRO ao atualizar foto {r['id']}: {e}")
                    if cB.button("Excluir", key=f"del_{r['id']}", type="secondary"):
                        try:
                            delete_photo(r["id"])
                            st.warning("Excluído.")
                            _log(f"Foto {r['id']} excluída.")
                            st.rerun()
                        except Exception as e:
                            st.exception(e)
                            _log(f"ERRO ao excluir foto {r['id']}: {e}")

    # ===== Galeria geral da VRP =====
    with section_card("Galeria da VRP (todas as coletas)"):
        all_rows = list_photos_by_vrp(site_id)
        if not all_rows:
            st.info("Esta VRP ainda não possui imagens salvas.")
        else:
            cols = st.columns(3)
            for i, r in enumerate(all_rows):
                with cols[i % 3]:
                    st.image(
                        r["file_path"],
                        use_container_width=True,
                        caption=f"CK {r['checklist_id']} • {r['label']}"
                    )

    # ===== Logs =====
    with section_card("Logs", "Registros desta sessão (não persistentes)."):
        colA, colB = st.columns([1,3])
        if colA.button("Limpar logs"):
            st.session_state["photo_logs"] = []

        logs_bytes = ("\n".join(st.session_state.get("photo_logs", []))).encode("utf-8")
        colB.download_button(
            "Baixar logs (.txt)",
            data=logs_bytes,
            file_name=f"logs_fotos_{_now().replace(':','-')}.txt",
            mime="text/plain"
        )

        if st.session_state.get("photo_logs"):
            st.text_area("Saída de logs", value="\n".join(st.session_state["photo_logs"]), height=220)
        else:
            st.caption("Sem logs nesta sessão. As ações realizadas serão registradas aqui.")
