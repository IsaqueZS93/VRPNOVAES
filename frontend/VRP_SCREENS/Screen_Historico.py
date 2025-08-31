"""
Lista checklists, permite selecionar um como 'corrente' e EXCLUIR com limpeza de arquivos.
UI padronizada (header, cards, etc).
"""
import streamlit as st
from ..VRP_DATABASE.database import get_conn
from ..VRP_SERVICE.history_service import delete_checklist
from ..VRP_STYLES.layout import page_setup, app_header, section_card, pill

def render():
    page_setup("VRP • Histórico", icon="🧾")
    app_header("Histórico de Checklists", "Selecione um checklist para gerar relatório ou exclua registros.")

    conn = get_conn()
    rows = conn.execute("""
        SELECT c.id, c.date, c.service_type, c.vrp_site_id, vs.municipality, vs.city, vs.place, vs.brand, vs.dn
        FROM checklists c
        LEFT JOIN vrp_sites vs ON vs.id = c.vrp_site_id
        ORDER BY c.id DESC
    """).fetchall()
    conn.close()

    if not rows:
        st.info("Sem registros.")
        return

    with section_card("Registros"):
        for r in rows:
            col1, col2, col3, col4 = st.columns([2, 4, 2, 3])
            with col1:
                st.markdown(f"**ID {r['id']}**")
                st.caption(f"{r['date']}")
            with col2:
                st.write(f"{r['service_type']}")
                st.caption(f"{r['place']} – {r['municipality']} ({r['city']})  •  {r['brand']} DN{r['dn'] or ''}")
            with col3:
                if st.button("Selecionar", key=f"sel_{r['id']}"):
                    st.session_state["current_checklist_id"] = r["id"]
                    st.success(f"Checklist {r['id']} selecionado. Abra a tela **Relatório**.")
            with col4:
                with st.expander("Excluir este checklist", expanded=False):
                    st.warning("⚠️ Remove checklist, fotos e relatórios gerados (DOCX/PDF).")
                    confirm = st.checkbox(f"Confirmo excluir o checklist #{r['id']}", key=f"conf_{r['id']}")
                    del_orphan_vrp = st.checkbox("Excluir também a VRP se ficar sem checklists", key=f"vrp_{r['id']}")
                    if st.button("Excluir definitivamente", key=f"del_{r['id']}", type="secondary", disabled=not confirm):
                        res = delete_checklist(r["id"], delete_vrp_if_orphan=del_orphan_vrp)
                        if res["ok"]:
                            st.success(
                                f"Checklist #{r['id']} excluído. "
                                f"Arquivos removidos: {res['files_deleted']}. "
                                f"Exports apagados: {res['exports_deleted']}. "
                                f"VRP apagada: {res['vrp_deleted']}."
                            )
                            st.rerun()
                        else:
                            st.error(f"Falha ao excluir: {res.get('reason','Erro desconhecido')}")
