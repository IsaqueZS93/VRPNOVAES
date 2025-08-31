# file: C:\Users\Novaes Engenharia\github - deploy\VRP\frontend\VRP_STYLES\style.py
import streamlit as st
from .brand import COLORS

def inject_global_css():
    if st.session_state.get("_nv_css_injected"):
        return
    css = f"""
    <style>
      :root{{
        --brand-primary: {COLORS['primary']};
        --brand-primary-600: {COLORS['primary_600']};
        --brand-primary-100: {COLORS['primary_100']};
        --brand-bg: {COLORS['bg']};
        --brand-bg2: {COLORS['bg2']};
        --brand-text: {COLORS['text']};
        --brand-muted: {COLORS['muted']};
        --brand-border: {COLORS['border']};
        --brand-success: {COLORS['success']};
        --brand-warning: {COLORS['warning']};
        --brand-danger: {COLORS['danger']};
      }}

      /* base */
      .stApp {{ background: var(--brand-bg) !important; color: var(--brand-text); }}
      a, a:visited {{ color: var(--brand-primary-600); }}

      /* sidebar */
      [data-testid="stSidebar"] > div:first-child {{ background: var(--brand-bg2); }}

      /* botões padrão - azul claro */
      div[data-testid="stButton"] > button {{
        background: var(--brand-primary-100);
        color: var(--brand-primary-600);
        border: 1px solid var(--brand-primary);
        border-radius: 12px;
        padding: .55rem 1.1rem;
        box-shadow: 0 1px 2px rgba(2,132,199,.15);
        transition: transform .02s ease-in-out, background .15s ease, color .15s ease, box-shadow .15s ease;
      }}
      div[data-testid="stButton"] > button:hover {{
        background: var(--brand-primary);
        color: #fff;
        box-shadow: 0 2px 8px rgba(2,132,199,.25);
      }}
      div[data-testid="stButton"] > button:active {{
        transform: translateY(1px);
        box-shadow: 0 1px 3px rgba(2,132,199,.2);
      }}

      /* inputs */
      .stTextInput > div > div > input,
      .stNumberInput input,
      .stTextArea textarea,
      .stSelectbox div[data-baseweb="select"] > div {{
        border-radius: 10px !important;
      }}

      /* labels em negrito */
      .stTextInput label,
      .stNumberInput label,
      .stTextArea label,
      .stSelectbox label,
      .stRadio label,
      .stCheckbox > label,
      .stFileUploader label {{
        font-weight: 700 !important;
        color: var(--brand-text) !important;
      }}

      /* upload */
      [data-testid="stFileUploaderDropzone"] {{
        border: 2px dashed var(--brand-border);
        background: var(--brand-bg2);
        border-radius: 12px;
      }}

      /* expander */
      [data-testid="stExpander"] > details > summary {{
        background: var(--brand-primary-100);
        border-radius: 10px;
        color: var(--brand-text);
      }}

      /* tabs */
      .stTabs [data-baseweb="tab-list"] button {{
        border-bottom: 2px solid transparent;
      }}
      .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-color: var(--brand-primary);
        color: var(--brand-primary-600);
      }}

      /* cards reutilizáveis */
      .nv-card {{
        background: var(--brand-bg2);
        border: 1px solid var(--brand-border);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(2,132,199,.08);
        margin-bottom: 14px;
      }}
      .nv-card h3 {{
        margin-top: 0; margin-bottom: 6px;
      }}
      .nv-section-title {{
        font-weight: 700; margin: 4px 0 8px 0;
        color: var(--brand-text);
      }}
      .nv-help {{
        font-size: 0.9rem; color: var(--brand-muted); margin-bottom: 8px;
      }}

      /* “pílulas” de status */
      .nv-pill {{
        display:inline-block; padding:.2rem .5rem; border-radius:999px;
        border:1px solid var(--brand-border); background:#fff; color:var(--brand-muted);
        font-size:.85rem; margin-right:.5rem;
      }}
      .nv-pill.primary {{ border-color: var(--brand-primary-600); color: var(--brand-primary-600); }}
      .nv-pill.success {{ border-color: var(--brand-success); color: var(--brand-success); }}
      .nv-pill.warning {{ border-color: var(--brand-warning); color: var(--brand-warning); }}
      .nv-pill.danger  {{ border-color: var(--brand-danger);  color: var(--brand-danger);  }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.session_state["_nv_css_injected"] = True
