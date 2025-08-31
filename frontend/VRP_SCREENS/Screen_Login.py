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
                st.success(f"Bem-vindo, {usuario}!")
                st.experimental_rerun()
            else:
                st.error("Senha incorreta.")
        else:
            st.error("Usuário não encontrado.")

# Para logout, basta limpar a sessão

def logout():
    st.session_state.pop("usuario", None)
    st.session_state.pop("tipo_usuario", None)
    st.experimental_rerun()
