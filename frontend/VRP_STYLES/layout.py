# file: C:\Users\Novaes Engenharia\github - deploy\VRP\frontend\VRP_STYLES\layout.py
import streamlit as st
from contextlib import contextmanager
from .style import inject_global_css

def page_setup(title: str, icon: str = "🛠️", wide: bool = True):
    """Config base por página + CSS global (idempotente)."""
    if not st.session_state.get("_page_configured", False):
        st.set_page_config(page_title=title, page_icon=icon, layout="wide" if wide else "centered")
        st.session_state["_page_configured"] = True
    inject_global_css()

def app_header(title: str, subtitle: str = ""):
    """Cabeçalho sem logo (apenas título e subtítulo)."""
    st.markdown(f"### {title}")
    if subtitle:
        st.markdown(f"<div class='nv-help'>{subtitle}</div>", unsafe_allow_html=True)

def toolbar(buttons: list[str]) -> dict:
    """
    Barra de ações no topo. Retorna dict {label: clicked_bool}
    Ex.: state = toolbar(['Novo', 'Salvar', 'Gerar Relatório'])
    """
    cols = st.columns(len(buttons))
    out = {}
    for c, label in zip(cols, buttons):
        with c:
            out[label] = st.button(label)
    return out

@contextmanager
def section_card(title: str, help_text: str | None = None):
    """Container padrão de seção (card)."""
    st.markdown("<div class='nv-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='nv-section-title'>{title}</div>", unsafe_allow_html=True)
    if help_text:
        st.markdown(f"<div class='nv-help'>{help_text}</div>", unsafe_allow_html=True)
    yield
    st.markdown("</div>", unsafe_allow_html=True)

def two_col() -> tuple:
    """Grid 2 colunas padrão (2:1)."""
    return st.columns([2, 1])

def three_col() -> tuple:
    """Grid 3 colunas equilibradas."""
    return st.columns(3)

def pill(text: str, kind: str = "primary"):
    st.markdown(f"<span class='nv-pill {kind}'>{text}</span>", unsafe_allow_html=True)
