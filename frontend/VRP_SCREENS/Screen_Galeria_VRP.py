"""
Galeria por VRP: escolha a VRP e veja todas as imagens associadas (qualquer checklist).
UI padronizada com header/logo, cards e paleta.
"""
import streamlit as st
from ..VRP_DATABASE.database import get_conn
from backend.VRP_SERVICE.storage_service import list_photos_by_vrp
from frontend.VRP_STYLES.layout import page_setup, app_header, section_card, pill

def render():
    page_setup("VRP • Galeria", icon="🖼️")
    app_header("Galeria por VRP", "Visualize as imagens anexadas por VRP.")

    # Busca VRPs e converte para tipos nativos (dict)
    conn = get_conn()
    rows = conn.execute("SELECT id, place, city, brand, dn FROM vrp_sites ORDER BY id DESC").fetchall()
    conn.close()
    sites = [dict(r) for r in rows]

    if not sites:
        st.info("Sem VRPs cadastradas.")
        return

    id_options = [s["id"] for s in sites]
    labels = { s["id"]: f"#{s['id']} • {s['place']} - {s['city']} • {s['brand']} DN{s.get('dn','')}" for s in sites }

    with section_card("Filtro"):
        sel_id = st.selectbox("Selecione a VRP", options=id_options, format_func=lambda _id: labels.get(_id, f"VRP #{_id}"))
        pill(f"Total: {len(list_photos_by_vrp(sel_id))} imagens")

    fotos = list_photos_by_vrp(sel_id)
    if not fotos:
        st.info("Esta VRP não possui imagens.")
        return

    with section_card("Imagens"):
        cols = st.columns(3)
        for i, r in enumerate(fotos):
            with cols[i % 3]:
                st.image(r["file_path"], use_container_width=True, caption=f"CK {r['checklist_id']} • {r['label']}")
