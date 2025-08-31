"""
Tela de Mapa VRP: visualização geográfica de todas as válvulas redutoras.
Usa streamlit-folium para exibir mapa interativo com marcadores das VRPs.
"""
import streamlit as st
import folium
from streamlit_folium import folium_static
from ..VRP_DATABASE.database import get_conn
from ..VRP_STYLES.layout import page_setup, app_header, section_card, pill

def _get_vrp_locations():
    """Busca todas as VRPs com coordenadas válidas."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT vs.id, vs.municipality, vs.city, vs.place, vs.brand, vs.type, vs.dn,
               vs.latitude, vs.longitude, vs.access_install,
               vs.network_depth_cm, vs.has_automation,
               COUNT(c.id) as checklist_count
        FROM vrp_sites vs
        LEFT JOIN checklists c ON c.vrp_site_id = vs.id
        WHERE vs.latitude IS NOT NULL AND vs.longitude IS NOT NULL
        GROUP BY vs.id
        ORDER BY vs.municipality, vs.city, vs.place
    """).fetchall()
    conn.close()
    return rows

def _create_map(vrp_locations):
    """Cria mapa Folium com marcadores das VRPs."""
    if not vrp_locations:
        return None
    
    # Calcular centro do mapa (média das coordenadas)
    lats = [r['latitude'] for r in vrp_locations]
    lngs = [r['longitude'] for r in vrp_locations]
    center_lat = sum(lats) / len(lats)
    center_lng = sum(lngs) / len(lngs)
    
    # Criar mapa base
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Adicionar marcadores para cada VRP
    for vrp in vrp_locations:
        # Cor baseada no tipo de VRP
        color_map = {
            'Ação Direta': 'red',
            'Auto-Regulada': 'blue', 
            'Pilotada': 'green'
        }
        color = color_map.get(vrp['type'], 'gray')
        
        # Popup com informações da VRP (incluindo novos campos)
        popup_html = f"""
        <div style="width: 250px;">
            <h4>VRP #{vrp['id']}</h4>
            <p><strong>Município:</strong> {vrp['municipality']}</p>
            <p><strong>Local DMC:</strong> {vrp['city']}</p>
            <p><strong>Complemento:</strong> {vrp['place'] or 'Não informado'}</p>
            <p><strong>Marca:</strong> {vrp['brand']}</p>
            <p><strong>Tipo:</strong> {vrp['type']}</p>
            <p><strong>DN:</strong> {vrp['dn']} mm</p>
            <p><strong>Acesso:</strong> {vrp['access_install']}</p>
            <p><strong>Profundidade:</strong> {vrp['network_depth_cm'] or 'Não informado'} cm</p>
            <p><strong>Automação:</strong> {'Sim' if vrp['has_automation'] else 'Não'}</p>
            <p><strong>Checklists:</strong> {vrp['checklist_count']}</p>
        </div>
        """
        
        folium.Marker(
            location=[vrp['latitude'], vrp['longitude']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"VRP #{vrp['id']} - {vrp['city']}",
            icon=folium.Icon(color=color, icon='info-sign')
        ).add_to(m)
    
    return m

def render():
    page_setup("VRP • Mapa", icon="🗺️")
    app_header("Mapa de Localização das VRPs", "Visualização geográfica de todas as válvulas redutoras cadastradas.")

    # Estatísticas rápidas
    vrp_locations = _get_vrp_locations()
    
    if not vrp_locations:
        st.warning("Nenhuma VRP com coordenadas geográficas cadastrada.")
        st.info("💡 Adicione coordenadas no formulário de Checklist para visualizar no mapa.")
        return
    
    # Resumo estatístico
    with section_card("Resumo"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total de VRPs", len(vrp_locations))
        with col2:
            dmc_locations = len(set(r['city'] for r in vrp_locations))
            st.metric("Locais DMC", dmc_locations)
        with col3:
            total_checklists = sum(r['checklist_count'] for r in vrp_locations)
            st.metric("Checklists", total_checklists)
        with col4:
            avg_checklists = total_checklists / len(vrp_locations) if vrp_locations else 0
            st.metric("Média por VRP", f"{avg_checklists:.1f}")

    # Filtros
    with section_card("Filtros"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            municipalities = sorted(list(set(r['municipality'] for r in vrp_locations)))
            selected_municipality = st.selectbox("Município", ["Todos"] + municipalities)
        
        with col2:
            dmc_locations = sorted(list(set(r['city'] for r in vrp_locations)))
            selected_dmc = st.selectbox("Local DMC", ["Todos"] + dmc_locations)
        
        with col3:
            vrp_types = sorted(list(set(r['type'] for r in vrp_locations)))
            selected_type = st.selectbox("Tipo de VRP", ["Todos"] + vrp_types)
        
        with col4:
            dns = sorted(list(set(r['dn'] for r in vrp_locations)))
            selected_dn = st.selectbox("DN (mm)", ["Todos"] + [str(dn) for dn in dns])

        # Aplicar filtros
        filtered_locations = vrp_locations
        if selected_municipality != "Todos":
            filtered_locations = [r for r in filtered_locations if r['municipality'] == selected_municipality]
        if selected_dmc != "Todos":
            filtered_locations = [r for r in filtered_locations if r['city'] == selected_dmc]
        if selected_type != "Todos":
            filtered_locations = [r for r in filtered_locations if r['type'] == selected_type]
        if selected_dn != "Todos":
            selected_dn_int = int(selected_dn)
            filtered_locations = [r for r in filtered_locations if r['dn'] == selected_dn_int]

        st.caption(f"Mostrando {len(filtered_locations)} de {len(vrp_locations)} VRPs")

    # Mapa
    with section_card("Mapa Interativo"):
        if filtered_locations:
            map_obj = _create_map(filtered_locations)
            if map_obj:
                folium_static(map_obj, width=700, height=500)
            else:
                st.error("Erro ao gerar mapa.")
        else:
            st.info("Nenhuma VRP encontrada com os filtros selecionados.")

    # Lista detalhada
    with section_card("Lista Detalhada"):
        if filtered_locations:
            for vrp in filtered_locations:
                with st.expander(f"VRP #{vrp['id']} - {vrp['municipality']} ({vrp['city']})", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Município:** {vrp['municipality']}")
                        st.write(f"**Local DMC:** {vrp['city']}")
                        st.write(f"**Complemento:** {vrp['place'] or 'Não informado'}")
                        st.write(f"**Marca:** {vrp['brand']}")
                        st.write(f"**Tipo:** {vrp['type']}")
                        st.write(f"**DN:** {vrp['dn']} mm")
                        st.write(f"**Acesso:** {vrp['access_install']}")
                        st.write(f"**Profundidade:** {vrp['network_depth_cm'] or 'Não informado'} cm")
                        st.write(f"**Automação:** {'Sim' if vrp['has_automation'] else 'Não'}")
                    with col2:
                        st.write(f"**Coordenadas:**")
                        st.code(f"Lat: {vrp['latitude']:.6f}")
                        st.code(f"Lng: {vrp['longitude']:.6f}")
                        st.write(f"**Checklists:** {vrp['checklist_count']}")
        else:
            st.info("Nenhuma VRP para exibir.")

    # Legenda
    with section_card("Legenda"):
        st.markdown("""
        **Cores dos marcadores:**
        - 🔴 **Vermelho:** VRP Ação Direta
        - 🔵 **Azul:** VRP Auto-Regulada  
        - 🟢 **Verde:** VRP Pilotada
        - ⚪ **Cinza:** Tipo não especificado
        """)
        
        st.caption("💡 **Dica:** Clique nos marcadores para ver detalhes da VRP. Use os filtros para focar em locais ou tipos específicos.")
