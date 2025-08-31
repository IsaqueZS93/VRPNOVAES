"""
Aplicação Streamlit principal.
Navegação por sidebar: Checklist, Fotos, Histórico, Relatório, Config, Galeria VRP e Mapa.
Login é renderizado fora do PAGES (não polui nav_radio).
"""
import os
import atexit
import streamlit as st
from dotenv import load_dotenv

from backend.VRP_DATABASE.database import init_db
from backend.VRP_DATABASE.github_db_sync import baixar_banco_github, subir_banco_github

# TELAS
from frontend.VRP_SCREENS import (
    Screen_Checklist_Form, Screen_Photos, Screen_Historico, Screen_Galeria_VRP,
    Screen_Relatorio, Screen_Config, Screen_Login, Screen_Enviar_Email
)
from frontend.VRP_SCREENS.Screen_Tutorial_VRP import render as Screen_VRP_Tutorial
from frontend.VRP_SCREENS.Screen_Mapa_VRP import render as Screen_Mapa_VRP
from frontend.VRP_STYLES.brand import logo_path

# ----------------- Setup base -----------------
st.set_page_config(page_title="VRP - Relatórios", layout="wide")
load_dotenv()
baixar_banco_github()
init_db()

# ----------------- Helpers -----------------
def is_user_logged_in() -> bool:
    """Verifica autenticação sem depender de nav_radio."""
    return bool(st.session_state.get("authenticated")) \
        and st.session_state.get("usuario") not in (None, "") \
        and st.session_state.get("tipo_usuario") not in (None, "")

def telas_para_usuario(tipo: str) -> list[str]:
    tipo = (tipo or "").lower()
    # OPE com menu reduzido
    if tipo == "ope":
        return ["Checklist", "Fotos", "Histórico", "Galeria VRP", "Mapa VRP", "Tutorial VRP"]
    # Demais perfis: todas as telas (exceto Login, que não entra em PAGES)
    return ["Checklist", "Fotos", "Histórico", "Relatório", "Galeria VRP", "Mapa VRP", "Tutorial VRP", "Config", "Enviar E-mail"]

# ----------------- GATE de Login -----------------
if not is_user_logged_in():
    # Cabeçalho lateral “limpo”
    st.sidebar.image(logo_path(), use_container_width=True)
    st.sidebar.title("VRP")
    # Renderiza a tela de Login e encerra este ciclo (sem mexer no nav_radio!)
    Screen_Login.render()
    st.stop()

# ----------------- Páginas (sem Login) -----------------
PAGES = {
    "Checklist":         Screen_Checklist_Form.render,
    "Fotos":             Screen_Photos.render,
    "Histórico":         Screen_Historico.render,
    "Relatório":         Screen_Relatorio.render,
    "Galeria VRP":       Screen_Galeria_VRP.render,
    "Mapa VRP":          Screen_Mapa_VRP,
    "Tutorial VRP":      Screen_VRP_Tutorial,
    "Config":            Screen_Config.render,
    "Enviar E-mail":     (Screen_Enviar_Email.render if hasattr(Screen_Enviar_Email, "render") else Screen_Enviar_Email),
}

# ----------------- Menu permitido -----------------
tipo = st.session_state.get("tipo_usuario", "").lower()
menu = [k for k in telas_para_usuario(tipo) if k in PAGES]

# Sidebar com logo e usuário
st.sidebar.image(logo_path(), use_container_width=True)
st.sidebar.title(f"VRP ({st.session_state.get('usuario','')})")

# Navegação programática primeiro
if st.session_state.get("nav_to") in PAGES:
    target = st.session_state.pop("nav_to")
    if target in menu:
        st.session_state["nav_radio"] = target

# Inicializa nav atual se faltar ou inválida
current = st.session_state.get("nav_radio", None)
if current not in menu:
    current = menu[0]
    st.session_state["nav_radio"] = current

# Radio efetivo
st.sidebar.radio("Navegar", menu, index=menu.index(st.session_state["nav_radio"]), key="nav_radio")

# Logout
if st.sidebar.button("Logout"):
    Screen_Login.logout()  # deve limpar authenticated/usuario/tipo_usuario
    st.rerun()

# Render da página atual
PAGES[st.session_state["nav_radio"]]()  # chama a função adequada

st.sidebar.markdown("---")
st.sidebar.write("Checklist atual:", st.session_state.get("current_checklist_id","—"))

# Push do banco ao sair
atexit.register(subir_banco_github)
