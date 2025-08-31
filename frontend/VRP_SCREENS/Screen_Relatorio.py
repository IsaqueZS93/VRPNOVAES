"""
Gera narrativa com IA (ou offline) e exporta DOCX/PDF.
UI padronizada com header/logo, toolbar e cards.
"""
import streamlit as st
from backend.VRP_SERVICE.ai_service import generate_ai_summary
from backend.VRP_SERVICE.report_service import generate_full_report
from backend.VRP_SERVICE.email_service import email_service
from backend.VRP_DATABASE.database import get_conn
from frontend.VRP_STYLES.layout import page_setup, app_header, toolbar, section_card, pill

def _get_saved_ai_text(checklist_id: int) -> str | None:
    conn = get_conn()
    row = conn.execute("""
        SELECT ai_summary FROM reports WHERE checklist_id=?
    """, (checklist_id,)).fetchone()
    conn.close()
    return row["ai_summary"] if row and row["ai_summary"] else None

def _vrp_label_from_ck(cid: int) -> str:
    conn = get_conn()
    r = conn.execute("""
        SELECT vs.place, vs.municipality, vs.city, vs.brand, vs.dn
        FROM vrp_sites vs
        INNER JOIN checklists c ON c.vrp_site_id = vs.id
        WHERE c.id = ?
    """, (cid,)).fetchone()
    conn.close()
    if not r: return "—"
    return f"{r['place']} – {r['municipality']} ({r['city']}) • {r['brand']} DN{r['dn'] or ''}"

def _get_photos_paths(checklist_id: int) -> list:
    """Obtém caminhos das fotos associadas ao checklist."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT file_path FROM photos 
        WHERE checklist_id = ? AND include_in_report = 1
        ORDER BY display_order
    """, (checklist_id,)).fetchall()
    conn.close()
    return [row["file_path"] for row in rows]

def render():
    page_setup("VRP • Relatório", icon="📄")
    app_header("Gerar Relatório", "Revise a narrativa técnica e exporte o documento.")

    cid = st.session_state.get("current_checklist_id", None)
    if not cid:
        st.warning("Selecione um checklist no **Histórico**.")
        return

    # toolbar
    actions = toolbar(["Voltar às Fotos", "Gerar Narrativa (IA)", "Exportar DOCX/PDF"])
    if actions["Voltar às Fotos"]:
        st.session_state["nav_to"] = "Fotos"; st.rerun()

    # header pills
    pill(f"Checklist #{cid}")
    st.caption(_vrp_label_from_ck(cid))

    # narrativa
    with section_card("Narrativa técnica (IA)", "Gerada a partir das observações; o texto abaixo é o que irá para o DOCX."):
        if actions["Gerar Narrativa (IA)"]:
            ai_text = generate_ai_summary(cid)
            st.session_state["ai_text"] = ai_text
            st.success("Narrativa gerada.")
        ai_text = st.session_state.get("ai_text") or _get_saved_ai_text(cid)
        st.text_area("Prévia", value=ai_text or "", height=320)

    # export
    with section_card("Exportação"):
        if actions["Exportar DOCX/PDF"]:
            ai_text = (st.session_state.get("ai_text") or _get_saved_ai_text(cid) or generate_ai_summary(cid))
            docx, pdf = generate_full_report(cid, ai_text)
            st.success("Relatório exportado.")
            st.markdown(f"**DOCX:**  `{docx}`")
            if pdf:
                st.markdown(f"**PDF:**   `{pdf}`")
            else:
                st.warning("PDF não gerado. O PDF depende do Microsoft Word + biblioteca `docx2pdf` instalados no Windows.")

        st.caption("Dica: Abra o DOCX no Word e pressione **F9** para atualizar **Sumário** e **Lista de Figuras**.")

    # Envio por Email
    with section_card("📧 Enviar por Email"):
        # Verificar se há emails configurados
        recipients = email_service.get_emails_from_session()
        config_status = email_service.get_config_status()
        
        if not config_status["configured"]:
            st.warning("⚠️ Configurações de email não encontradas!")
            st.info("Configure o email na tela **Configurações** para enviar relatórios automaticamente.")
        elif not recipients:
            st.info("ℹ️ Nenhum destinatário configurado.")
            st.info("Adicione emails na tela **Configurações** para receber relatórios automaticamente.")
        else:
            st.success(f"✅ {len(recipients)} destinatário(s) configurado(s)")
            
            # Mostrar destinatários
            st.write("**Destinatários:**")
            for email in recipients:
                st.write(f"📧 {email}")
            
            # Botão para enviar
            if st.button("📤 Enviar Relatório por Email", type="primary"):
                with st.spinner("Enviando relatório por email..."):
                    # Obter caminhos dos arquivos
                    docx_path = ""
                    pdf_path = ""
                    
                    # Buscar relatórios existentes
                    conn = get_conn()
                    report_row = conn.execute("""
                        SELECT docx_path, pdf_path FROM reports WHERE checklist_id = ?
                    """, (cid,)).fetchone()
                    conn.close()
                    
                    if report_row:
                        docx_path = report_row["docx_path"] or ""
                        pdf_path = report_row["pdf_path"] or ""
                    
                    # Se não há relatório, gerar primeiro
                    if not docx_path:
                        ai_text = (st.session_state.get("ai_text") or _get_saved_ai_text(cid) or generate_ai_summary(cid))
                        docx_path, pdf_path = generate_full_report(cid, ai_text)
                        st.success("Relatório gerado automaticamente para envio.")
                    
                    # Obter fotos
                    photos_paths = _get_photos_paths(cid)
                    
                    # Enviar email
                    success = email_service.send_report_email(
                        checklist_id=cid,
                        report_path=docx_path,
                        photos_paths=photos_paths,
                        recipients=recipients
                    )
                    
                    if success:
                        st.success("✅ Relatório enviado com sucesso!")
                        st.info(f"📧 Enviado para {len(recipients)} destinatário(s)")
                    else:
                        st.error("❌ Falha ao enviar relatório. Verifique as configurações de email.")
