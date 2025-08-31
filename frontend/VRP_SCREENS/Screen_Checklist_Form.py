"""
Formulário do checklist (cabeçalho + VRP + hidráulica + pressões).
Ao salvar, cria registros em vrp_sites (se necessário) e checklists.
Guarda o checklist_id em st.session_state['current_checklist_id'].
"""
import streamlit as st
from datetime import date as _date
from backend.VRP_DATABASE.database import get_conn
from backend.VRP_MODEL.schemas import VRPSite, Checklist, DMC_LOCATIONS
from frontend.VRP_STYLES.layout import (
    page_setup, app_header, toolbar, section_card, two_col, three_col, pill
)

SERVICE_TYPES = ['Manutenção Preventiva','Manutenção Preditiva','Manutenção Corretiva','Ajuste e Aferição']
VRP_TYPES = ['Ação Direta','Auto-Regulada','Pilotada']
DNs = [50,60,85,100,150,200,250,300,350]

def _insert_vrp_site(site: VRPSite) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO vrp_sites (
            municipality, city, place, brand, type, dn, access_install, traffic, lids, notes_access,
            latitude, longitude, network_depth_cm, has_automation
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        site.municipality, site.city, site.place, site.brand, site.type, site.dn, 
        site.access_install, site.traffic, site.lids, site.notes_access,
        site.latitude, site.longitude, site.network_depth_cm, int(site.has_automation)
    ))
    conn.commit()
    site_id = cur.lastrowid
    conn.close()
    return site_id

def _insert_checklist(ck: Checklist) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO checklists (
            date, service_type, contractor_id, contracted_id, team_id, vrp_site_id,
            has_reg_upstream, has_reg_downstream, has_bypass, notes_hydraulics,
            p_up_before, p_down_before, p_up_after, p_down_after, observations_general
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (ck.date, ck.service_type, ck.contractor_id, ck.contracted_id, ck.team_id, ck.vrp_site_id,
          int(ck.has_reg_upstream), int(ck.has_reg_downstream), int(ck.has_bypass), ck.notes_hydraulics,
          ck.p_up_before, ck.p_down_before, ck.p_up_after, ck.p_down_after, ck.observations_general))
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid

def _required_ok(municipality, city, place, date_str, service_type, brand):
    if not municipality:
        st.warning("⚠️ **Município obrigatório**: Preencha o **Município** onde a VRP está localizada.")
        return False
    if not city or city == "Selecione o local DMC...":
        st.warning("⚠️ **Local DMC obrigatório**: Selecione o **Local DMC** (nome do ativo) da VRP.")
        return False
    if not place:
        st.warning("⚠️ **Local obrigatório**: Preencha o **Local (complemento)** com informações adicionais (rua, bairro, referência).")
        return False
    if not date_str:
        st.warning("⚠️ **Data obrigatória**: Selecione a **Data** do serviço.")
        return False
    if not service_type:
        st.warning("⚠️ **Tipo de serviço obrigatório**: Selecione o **Tipo de Serviço**.")
        return False
    if not brand:
        st.warning("⚠️ **Marca obrigatória**: Informe a **Marca da VRP**.")
        return False
    return True

def render():
    # ========== padrão de página ==========
    page_setup("VRP • Checklist", icon="📝")
    app_header("Novo Checklist VRP", "Preencha os dados e salve para anexar fotos e gerar o relatório.")

    # Barra de ações comum
    actions = toolbar(["Salvar Checklist", "Ir para Fotos", "Ir para Relatório"])
    go_photos = actions["Ir para Fotos"]
    go_report = actions["Ir para Relatório"]

    # ======= Identificação =======
    with section_card("Identificação do Serviço", "Dados das empresas, local e equipe."):
        colA,colB = two_col()
        with colA:
            contractor = st.text_input("Nome da Empresa (Contratante)")
            # Campo Município (campo de texto livre)
            municipality = st.text_input(
                "Município", 
                help="Nome do município onde a VRP está localizada (ex: Maceió, Pilar, Marechal Deodoro)"
            )
            # Local DMC como combobox (nome do ativo)
            st.markdown("**Local DMC (Nome do Ativo)**")
            city = st.selectbox(
                "Selecione o local DMC da VRP", 
                ["Selecione o local DMC..."] + DMC_LOCATIONS, 
                index=0,
                help="Selecione o nome do ativo/local DMC da VRP"
            )
            st.caption("💡 O município e local DMC são obrigatórios para identificar a localização da VRP")
            # Data padrão: hoje
            _d = st.date_input("Data", value=_date.today())
            date = _d.strftime("%Y-%m-%d")
        with colB:
            contracted = st.text_input("Nome da Empresa (Contratada)")
            place = st.text_input(
                "Local (complemento)", 
                help="Informação adicional sobre o local (ex: rua, bairro, referência)"
            )
            team = st.text_input("Equipe Executora")

        with section_card("Início das Atividades"):
            service_type = st.selectbox("Tipo de Serviço", SERVICE_TYPES, index=0)

    # ======= Dados da VRP =======
    with section_card("Dados da VRP", "Informações técnicas do equipamento."):
        col1,col2,col3 = three_col()
        brand = col1.text_input("Marca da VRP")
        vtype = col2.selectbox("Tipo", VRP_TYPES, index=2)
        dn = col3.selectbox("DN da VRP (mm)", DNs, index=5)

        # Novos campos de características
        col_depth, col_auto = two_col()
        with col_depth:
            network_depth_cm = st.number_input(
                "Profundidade da Rede (cm)", 
                min_value=0.0, 
                max_value=1000.0, 
                value=None,
                step=1.0,
                help="Profundidade da rede em centímetros"
            )
        with col_auto:
            has_automation = st.checkbox("VRP possui automação/telemetria", value=False)

        st.caption("Acesso (selecione as opções)")
        c1,c2,c3 = three_col()
        access_install = c1.selectbox("Instalação", ["passeio","rua"], index=0)
        traffic = c2.selectbox("Tráfego", ["alto","baixo"], index=1)
        lids = c3.selectbox("Tampas", ["visiveis","cobertas"], index=1)

        notes_access = st.text_area(
            "Observações de acesso (usadas pela IA para análise, não aparecem no relatório)",
            height=80, placeholder="Ex.: dificuldade de acesso, tampas cobertas, necessidade de sinalização..."
        )

        # ======= Localização Geográfica =======
        with section_card("Localização Geográfica", "Coordenadas para mapeamento e localização da VRP."):
            st.info("💡 **Dica**: Use o Google Maps para obter as coordenadas. Clique com botão direito no local e selecione 'O que há aqui?' para ver lat/lng.")
            
            col_lat, col_lng = st.columns(2)
            with col_lat:
                latitude = st.number_input(
                    "Latitude", 
                    min_value=-90.0, 
                    max_value=90.0, 
                    value=None,
                    step=0.000001,
                    format="%.6f",
                    help="Latitude em graus decimais (-90 a 90)"
                )
            with col_lng:
                longitude = st.number_input(
                    "Longitude", 
                    min_value=-180.0, 
                    max_value=180.0, 
                    value=None,
                    step=0.000001,
                    format="%.6f",
                    help="Longitude em graus decimais (-180 a 180)"
                )
            
            # Botão para abrir Google Maps
            if st.button("📍 Abrir Google Maps para obter coordenadas"):
                st.markdown(f"""
                <a href="https://www.google.com/maps" target="_blank">
                    🔗 Abrir Google Maps em nova aba
                </a>
                """, unsafe_allow_html=True)

    # ======= Hidráulica =======
    with section_card("Análise Hidráulica da Rede", "Registros e bypass."):
        u1,u2,u3 = three_col()
        reg_up = u1.checkbox("c/ registro montante", value=True)
        reg_down = u2.checkbox("c/ registro jusante", value=True)
        bypass = u3.checkbox("c/ bypass", value=True)
        notes_h = st.text_area(
            "Observações hidráulicas (usadas pela IA, não aparecem no relatório)",
            height=80, placeholder="Ex.: registro de jusante com manopla danificada; bypass inoperante..."
        )

    # ======= Pressões (mca) =======
    with section_card("Análise de Pressão (mca)", "Informe antes e depois para montante e jusante."):
        p1,p2,p3,p4 = st.columns(4)
        p_up_b = p1.number_input("Montante (antes)", value=0.0, step=0.1, min_value=0.0)
        p_down_b = p2.number_input("Jusante (antes)", value=0.0, step=0.1, min_value=0.0)
        p_up_a = p3.number_input("Montante (depois)", value=0.0, step=0.1, min_value=0.0)
        p_down_a = p4.number_input("Jusante (depois)", value=0.0, step=0.1, min_value=0.0)

        # Feedback rápido (pílulas)
        try:
            delta_up = p_up_a - p_up_b
            delta_dn = p_down_a - p_down_b
            st.write("Resultados:")
            pill(f"Δ Montante: {delta_up:+.1f} mca", "primary")
            pill(f"Δ Jusante: {delta_dn:+.1f} mca", "primary")
        except Exception:
            pass

    # ======= Observações gerais =======
    with section_card("Observações gerais (IA)", "Usadas pela IA para a narrativa técnica; não aparecem no documento."):
        obs_general = st.text_area("Anotações livres", height=100)

    # ======= Fluxo: Salvar / Navegar =======
    if actions["Salvar Checklist"]:
        if not _required_ok(municipality, city, place, date, service_type, brand):
            st.stop()

        # salva empresas e equipe como 'free text'
        conn = get_conn()
        contractor_id = contracted_id = team_id = None
        if contractor:
            conn.execute("INSERT INTO companies (name,type) VALUES (?,?)",(contractor,'CONTRATANTE'))
            contractor_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if contracted:
            conn.execute("INSERT INTO companies (name,type) VALUES (?,?)",(contracted,'CONTRATADA'))
            contracted_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        if team:
            conn.execute("INSERT INTO teams (name) VALUES (?)",(team,))
            team_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit(); conn.close()

        site = VRPSite(
            municipality=municipality, city=city, place=place, brand=brand, type=vtype, dn=dn,
            access_install=access_install, traffic=traffic, lids=lids, notes_access=notes_access,
            latitude=latitude, longitude=longitude, network_depth_cm=network_depth_cm, 
            has_automation=has_automation
        )
        site_id = _insert_vrp_site(site)

        ck = Checklist(
            date=date, service_type=service_type, contractor_id=contractor_id, contracted_id=contracted_id,
            team_id=team_id, vrp_site_id=site_id, has_reg_upstream=reg_up, has_reg_downstream=reg_down,
            has_bypass=bypass, notes_hydraulics=notes_h, p_up_before=p_up_b, p_down_before=p_down_b,
            p_up_after=p_up_a, p_down_after=p_down_a, observations_general=obs_general
        )
        cid = _insert_checklist(ck)
        st.session_state["current_checklist_id"] = cid
        st.success(f"Checklist salvo (ID {cid}). Use a barra acima para ir às **Fotos** ou ao **Relatório**.")

    # Navegação rápida:
    if go_photos:
        st.session_state["nav_to"] = "Fotos"; st.rerun()
    if go_report:
        st.session_state["nav_to"] = "Relatório"; st.rerun()
