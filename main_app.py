"""
Aplicação Streamlit principal.
Navegação por sidebar: Checklist, Fotos, Histórico, Relatório, Config e Galeria VRP.
Cria o banco (init_db). Suporta navegação programática via st.session_state["nav_to"].
"""
import streamlit as st
import os
from dotenv import load_dotenv
from backend.VRP_DATABASE.database import init_db
from backend.VRP_DATABASE.github_db_sync import baixar_banco_github, subir_banco_github
from frontend.VRP_SCREENS import (
    Screen_Checklist_Form, Screen_Photos, Screen_Historico, Screen_Galeria_VRP, Screen_Relatorio, Screen_Config
)
from frontend.VRP_SCREENS import Screen_Enviar_Email
from frontend.VRP_SCREENS.SCREEN_VRP_TUTORIAL import render as Screen_VRP_Tutorial
from frontend.VRP_SCREENS.Screen_Mapa_VRP import render as Screen_Mapa_VRP
from frontend.VRP_STYLES.brand import logo_path


# Carregar variáveis de ambiente
load_dotenv()


# Baixar banco do GitHub ao iniciar
baixar_banco_github()

# Garante que as tabelas existem após baixar o banco
init_db()

st.set_page_config(page_title="VRP - Relatórios", layout="wide")

PAGES = {
    "Checklist":  Screen_Checklist_Form.render,
    "Fotos":      Screen_Photos.render,
    "Histórico":  Screen_Historico.render,
    "Relatório":  Screen_Relatorio.render,
    "Galeria VRP":Screen_Galeria_VRP.render,
    "Mapa VRP":   Screen_Mapa_VRP,
    "Tutorial VRP": Screen_VRP_Tutorial,
    "Config":     Screen_Config.render,
    "Enviar E-mail": Screen_Enviar_Email.render if hasattr(Screen_Enviar_Email, "render") else Screen_Enviar_Email,
}

# Sidebar com logo e nav
st.sidebar.image(logo_path(), use_container_width=True)
st.sidebar.title("VRP")

# suporta "programmatic nav"
page_names = list(PAGES.keys())
current = st.session_state.get("nav_radio", page_names[0])
if st.session_state.get("nav_to") in PAGES:
    current = st.session_state.pop("nav_to")
st.sidebar.radio("Navegar", page_names, index=page_names.index(current), key="nav_radio")


PAGES[st.session_state["nav_radio"]]()
st.sidebar.markdown("---")
st.sidebar.write("Checklist atual:", st.session_state.get("current_checklist_id","—"))

# Subir banco para o GitHub ao finalizar (pode ser ajustado para eventos específicos)
import atexit
atexit.register(subir_banco_github)
