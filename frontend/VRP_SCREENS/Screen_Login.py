"""
Tela de login para o sistema VRP.
Valida usuário e senha usando st.secrets.
Salva usuário e tipo na sessão.
"""
import streamlit as st

def get_login_data():
    # Busca dados do secrets
    logins = st.secrets["infologin"]["LOGIN"].replace(" ","").split(",")
    tipos = st.secrets["infotipo"]["TIPO"].replace(" ","").split(",")
    senhas = st.secrets["infosenha"]["SENHA"].replace(" ","").split(",")
    return logins, tipos, senhas

def render():
    st.title("Login VRP")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    logins, tipos, senhas = get_login_data()
    if st.button("Entrar"):
        if usuario in logins:
            idx = logins.index(usuario)
            if senha == senhas[idx]:
                st.session_state["usuario"] = usuario
                st.session_state["tipo_usuario"] = tipos[idx]
                st.session_state["authenticated"] = True  # Flag de autenticação
                # Após login, direciona para tela inicial do menu
                tipo = tipos[idx].lower()
                telas_ope = ["Checklist", "Fotos", "Histórico", "Galeria VRP", "Mapa VRP", "Tutorial VRP"]
                if tipo == "ope":
                    st.session_state["nav_radio"] = telas_ope[0]
                else:
                    # Define a primeira tela disponível para usuários não-OPE
                    telas_disponiveis = ["Checklist", "Fotos", "Histórico", "Relatório", "Galeria VRP", "Mapa VRP", "Tutorial VRP", "Config", "Enviar E-mail"]
                    st.session_state["nav_radio"] = telas_disponiveis[0]
                st.success(f"Bem-vindo, {usuario}!")
                st.rerun()
            else:
                st.error("Senha incorreta.")
        else:
            st.error("Usuário não encontrado.")

# Para logout, basta limpar a sessão

def logout():
    # Limpa todas as variáveis de sessão relacionadas ao login
    st.session_state.pop("usuario", None)
    st.session_state.pop("tipo_usuario", None)
    st.session_state.pop("authenticated", None)
    st.session_state.pop("nav_radio", None)
    st.session_state.pop("nav_to", None)
    # Força o redirecionamento para a tela de login
    st.session_state["nav_radio"] = "Login"
    st.rerun()
