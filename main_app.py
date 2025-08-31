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
from frontend.VRP_SCREENS import Screen_Login
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
    "Login": Screen_Login.render,
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

def is_user_logged_in():
    """Verifica se o usuário está logado de forma robusta"""
    # Verifica se as chaves existem e não são None
    has_usuario = "usuario" in st.session_state and st.session_state["usuario"] is not None
    has_tipo = "tipo_usuario" in st.session_state and st.session_state["tipo_usuario"] is not None
    is_authenticated = st.session_state.get("authenticated", False)
    
    # Debug: mostra o estado atual (remover em produção)
    # st.write(f"Debug - usuario: {has_usuario}, tipo: {has_tipo}, auth: {is_authenticated}")
    
    return has_usuario and has_tipo and is_authenticated

# Verifica se o usuário está logado
if not is_user_logged_in():
    st.sidebar.image(logo_path(), width='stretch')
    st.sidebar.title("VRP")
    # Força a tela de login
    st.session_state["nav_radio"] = "Login"
    PAGES["Login"]()
    st.stop()

# Garante que o usuário autenticado não seja redirecionado para login
if is_user_logged_in() and st.session_state.get("nav_radio") == "Login":
    # Redireciona para a primeira tela disponível
    tipo = st.session_state["tipo_usuario"].lower()
    telas_ope = ["Checklist", "Fotos", "Histórico", "Galeria VRP", "Mapa VRP", "Tutorial VRP"]
    if tipo == "ope":
        st.session_state["nav_radio"] = telas_ope[0]
    else:
        menu_disponivel = [k for k in PAGES.keys() if k != "Login"]
        st.session_state["nav_radio"] = menu_disponivel[0]
    st.rerun()

# Usuário está logado, prossegue com a aplicação
tipo = st.session_state["tipo_usuario"].lower()
# Telas permitidas para OPE
telas_ope = ["Checklist", "Fotos", "Histórico", "Galeria VRP", "Mapa VRP", "Tutorial VRP"]
if tipo == "ope":
    menu = telas_ope
else:
    menu = [k for k in PAGES.keys() if k != "Login"]

st.sidebar.image(logo_path(), width='stretch')
st.sidebar.title(f"VRP ({st.session_state['usuario']})")

# Garante que o usuário não fique na tela de login após fazer login
current = st.session_state.get("nav_radio", menu[0])

# Se o usuário está na tela de login, redireciona para a primeira tela disponível
if current == "Login":
    current = menu[0]
    st.session_state["nav_radio"] = current

# Se a tela atual não está no menu permitido, redireciona para a primeira disponível
if current not in menu:
    current = menu[0]
    st.session_state["nav_radio"] = current

# Processa navegação programática
if st.session_state.get("nav_to") in PAGES:
    current = st.session_state.pop("nav_to")
    if current not in menu:
        current = menu[0]
    st.session_state["nav_radio"] = current

# Corrige o valor do radio se não estiver no menu
if st.session_state.get("nav_radio") not in menu:
    st.session_state["nav_radio"] = menu[0]
    current = menu[0]
st.sidebar.radio("Navegar", menu, index=menu.index(current), key="nav_radio")
# Botão logout
if st.sidebar.button("Logout"):
    Screen_Login.logout()
    st.stop()
# render
PAGES[st.session_state["nav_radio"]]()
st.sidebar.markdown("---")
st.sidebar.write("Checklist atual:", st.session_state.get("current_checklist_id","—"))
# Subir banco para o GitHub ao finalizar (pode ser ajustado para eventos específicos)
import atexit
atexit.register(subir_banco_github)
