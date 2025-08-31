# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_SERVICE\ai_service.py
"""
Narrativa técnica com GROQ (Llama-3.3-70B-Versatile).
- Usa observações como CONTEXTO, mas NÃO as reproduz.
- Saída em PT-BR, termos de VRP e unidades em mca.
Docs oficiais: models e chat completions. 
"""
import os
from textwrap import dedent
from dotenv import load_dotenv
from backend.VRP_DATABASE.database import get_conn

load_dotenv()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def _collect_context(checklist_id: int) -> dict:
    conn = get_conn()
    ck = conn.execute("SELECT * FROM checklists WHERE id=?", (checklist_id,)).fetchone()
    site = None
    if ck and ck["vrp_site_id"]:
        site = conn.execute("SELECT * FROM vrp_sites WHERE id=?", (ck["vrp_site_id"],)).fetchone()
    photos = conn.execute("""
        SELECT label, caption FROM photos
        WHERE checklist_id=? AND include_in_report=1
        ORDER BY display_order,id
    """, (checklist_id,)).fetchall()
    conn.close()
    return {"ck": dict(ck) if ck else {}, "site": dict(site) if site else {}, "photos": [dict(p) for p in photos]}

def _offline_template(ctx: dict) -> str:
    ck, site = ctx["ck"], ctx["site"]
    return dedent(f"""
    ## Análise Técnica
    Foi executada intervenção na VRP localizada em {site.get('place','-')} ({site.get('city','-')}), do tipo {site.get('type','-')} e DN {site.get('dn','-')} mm.
    A inspeção incluiu verificação de registros a montante/jusante e bypass, limpeza, ajustes e testes operacionais.
    Pressões medidas (mca): montante {ck.get('p_up_before','-')}→{ck.get('p_up_after','-')} | jusante {ck.get('p_down_before','-')}→{ck.get('p_down_after','-')}.
    Resultado: operação estabilizada e condizente com o objetivo de controle de pressão para a área atendida.
    Recomendações: manter rotina de inspeção, reaperto e validação pós-intervenção.
    """).strip()

def generate_ai_summary(checklist_id: int) -> str:
    ctx = _collect_context(checklist_id)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _offline_template(ctx)
    try:
        from groq import Groq  # SDK oficial
        client = Groq(api_key=api_key)

        system = dedent("""
        Você é engenheiro especialista em válvulas redutoras de pressão (VRP).
        Gere uma ANÁLISE TÉCNICA concisa em PT-BR, com foco em condições encontradas,
        procedimentos executados, aferições (mca) e recomendações.
        Use as observações fornecidas APENAS como insumo; NÃO cite, copie ou revele as frases originais.
        Não invente números. Unidades de pressão: mca.
        Seja efetivo, não seja redundante.
        Estruture com pequenos e médios parágrafos e listas quando adequado.
        """)

        user_payload = {
            "checklist": {k:v for k,v in ctx["ck"].items() if k not in ("notes_hydraulics","observations_general")},
            "site": ctx["site"],
            # Observações das fotos entram como insumo, mas não devem aparecer textualmente
            "observations_from_images": [p.get("caption","") for p in ctx["photos"] if p.get("caption")],
        }

        chat = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Elabore a análise técnica a partir destes dados:\n{user_payload}"}
            ],
        )
        return chat.choices[0].message.content.strip()
    except Exception:
        return _offline_template(ctx)
