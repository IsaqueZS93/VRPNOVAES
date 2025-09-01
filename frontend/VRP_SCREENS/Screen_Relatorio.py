# file: frontend/VRP_SCREENS/Screen_Relatorio.py
"""
Gera narrativa com IA (ou offline) e exporta DOCX/PDF.
UI padronizada com header/logo, toolbar e cards.
Sem dependência de Google Drive; suporte a armazenamento temporário por sessão.
"""
from __future__ import annotations

import os
import streamlit as st

from backend.VRP_SERVICE.ai_service import generate_ai_summary
from backend.VRP_SERVICE.report_service import generate_full_report
from backend.VRP_DATABASE.database import get_conn
from frontend.VRP_STYLES.layout import page_setup, app_header, toolbar, section_card, pill

# Opcional: purgar fotos temporárias após exportar (se disponível)
try:
    from backend.VRP_SERVICE.storage_service import purge_session_photos  # type: ignore
except Exception:
    purge_session_photos = None  # fallback silencioso

def _get_saved_ai_text(checklist_id: int) -> str | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT ai_summary FROM reports WHERE checklist_id=?",
        (checklist_id,),
    ).fetchone()
    conn.close()
    return row["ai_summary"] if row and row["ai_summary"] else None

def _vrp_label_from_ck(cid: int) -> str:
    """Rótulo amigável da VRP vinculada ao checklist. (Sem 'municipality' — não existe no schema.)"""
    conn = get_conn()
    r = conn.execute(
        """
        SELECT vs.place, vs.city, vs.brand, vs.dn
        FROM vrp_sites vs
        INNER JOIN checklists c ON c.vrp_site_id = vs.id
        WHERE c.id = ?
        """,
        (cid,),
    ).fetchone()
    conn.close()
    if not r:
        return "—"
    return f"{r['place']} – {r['city']} • {r['brand']} DN{r['dn'] or ''}"

def _get_photos_paths(checklist_id: int) -> list[str]:
    """Caminhos das fotos inclusas no relatório (ordem respeitada)."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT file_path FROM photos
        WHERE checklist_id = ? AND include_in_report = 1
        ORDER BY display_order, id
        """,
        (checklist_id,),
    ).fetchall()
    conn.close()
    return [row["file_path"] for row in rows]

def render():
    page_setup("VRP • Relatório", icon="📄")
    app_header("Gerar Relatório", "Revise a narrativa técnica e exporte o documento.")

    cid = st.session_state.get("current_checklist_id")
    if not cid:
        st.warning("Selecione um checklist no **Histórico**.")
        return

    # Toolbar principal
    actions = toolbar(["Voltar às Fotos", "Gerar Narrativa (IA)", "Exportar DOCX/PDF"])
    if actions["Voltar às Fotos"]:
        st.session_state["nav_to"] = "Fotos"
        st.rerun()

    # Cabeçalho
    pill(f"Checklist #{cid}")
    st.caption(_vrp_label_from_ck(cid))

    # Narrativa
    with section_card(
        "Narrativa técnica (IA)",
        "Gerada a partir das observações; o texto abaixo é o que irá para o DOCX."
    ):
        if actions["Gerar Narrativa (IA)"]:
            ai_text = generate_ai_summary(cid)
            st.session_state["ai_text"] = ai_text
            st.success("Narrativa gerada.")
        ai_text = st.session_state.get("ai_text") or _get_saved_ai_text(cid)
        st.text_area("Prévia", value=ai_text or "", height=320)

    # Exportação
    with section_card("Exportação"):
        # Locais padrão + opção de texto livre (opcional)
        opcoes_pasta = ["frontend/assets/exports", "backend/VRP_DATABASE/exports", "Personalizar..."]
        escolha_pasta = st.selectbox("Escolha o local para salvar os arquivos", opcoes_pasta, index=0)
        if escolha_pasta == "Personalizar...":
            pasta_destino = st.text_input(
                "Informe o caminho completo da pasta de destino:",
                value="frontend/assets/exports"
            ).strip()
        else:
            pasta_destino = escolha_pasta

        # Limpeza automática de fotos temporárias depois da exportação
        limpar_depois = st.checkbox(
            "⏳ Limpar fotos temporárias deste checklist após exportar",
            value=True,
            help="Remove do armazenamento temporário desta sessão para liberar espaço."
        )

        if actions["Exportar DOCX/PDF"]:
            ai_text = st.session_state.get("ai_text") or _get_saved_ai_text(cid) or generate_ai_summary(cid)

            # generate_full_report: compatível com 2 ou 3 parâmetros
            try:
                docx, pdf = generate_full_report(cid, ai_text, pasta_destino)  # type: ignore[arg-type]
            except TypeError:
                # Backward-compat caso sua função aceite só (cid, ai_text)
                docx, pdf = generate_full_report(cid, ai_text)  # type: ignore[misc]

                # Se o usuário definiu uma pasta diferente, tenta mover/copy
                try:
                    os.makedirs(pasta_destino, exist_ok=True)
                    # Copia o DOCX
                    if docx and os.path.isfile(docx):
                        dest_docx = os.path.join(pasta_destino, os.path.basename(docx))
                        if os.path.abspath(dest_docx) != os.path.abspath(docx):
                            with open(docx, "rb") as fr, open(dest_docx, "wb") as fw:
                                fw.write(fr.read())
                            docx = dest_docx
                    # Copia o PDF se houver
                    if pdf and os.path.isfile(pdf):
                        dest_pdf = os.path.join(pasta_destino, os.path.basename(pdf))
                        if os.path.abspath(dest_pdf) != os.path.abspath(pdf):
                            with open(pdf, "rb") as fr, open(dest_pdf, "wb") as fw:
                                fw.write(fr.read())
                            pdf = dest_pdf
                except Exception as e:
                    st.warning(f"⚠️ Não foi possível copiar para a pasta escolhida: {e}")

            st.success("Relatório exportado.")

            # Botões de download (direto do servidor)
            if docx and os.path.isfile(docx):
                with open(docx, "rb") as f:
                    st.download_button(
                        label="Baixar DOCX",
                        data=f.read(),
                        file_name=f"Relatorio_VRP_{cid}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
            else:
                st.error("DOCX não encontrado após exportação.")

            if pdf and os.path.isfile(pdf):
                with open(pdf, "rb") as f:
                    st.download_button(
                        label="Baixar PDF",
                        data=f.read(),
                        file_name=f"Relatorio_VRP_{cid}.pdf",
                        mime="application/pdf",
                    )
            else:
                st.info("PDF não gerado. O PDF depende do Microsoft Word + biblioteca `docx2pdf` no Windows.")

            st.caption("Dica: Abra o DOCX no Word e pressione **F9** para atualizar **Sumário** e **Lista de Figuras**.")

            # Limpeza pós-exportação (se habilitada e disponível)
            if limpar_depois and purge_session_photos:
                try:
                    res = purge_session_photos(checklist_id=cid)
                    st.success(f"Fotos temporárias removidas: registros={res.get('rows_deleted', '?')} • arquivos={res.get('files_deleted', '?')}")
                except Exception as e:
                    st.warning(f"Não foi possível limpar fotos temporárias automaticamente: {e}")

    # Envio por Email (opcional)
    with section_card("📧 Enviar por Email"):
        # Secrets opcionais e robustos
        emails_sect = st.secrets.get("infoemails", {})
        raw = emails_sect.get("EMAILS", "") if isinstance(emails_sect, dict) else ""
        emails_validos = [e for e in (raw.replace(" ", "").split(",") if raw else []) if e]

        if not emails_validos:
            st.info("ℹ️ Nenhum destinatário disponível. Configure os emails em `secrets.toml` (infoemails.EMAILS).")
        else:
            destinatarios = st.multiselect(
                "Selecione os destinatários para envio do relatório:",
                options=emails_validos,
                help="Selecione um ou mais e-mails."
            )
            if not destinatarios:
                st.info("Selecione ao menos um destinatário para enviar o relatório.")
            else:
                st.success(f"✅ {len(destinatarios)} destinatário(s) selecionado(s)")

                # Import tardio para não quebrar a tela se o serviço não existir
                try:
                    from backend.VRP_SERVICE.email_service import email_service  # type: ignore
                except Exception:
                    email_service = None

                if st.button("📤 Enviar Relatório por Email", type="primary"):
                    if not email_service:
                        st.error("Serviço de e-mail indisponível. Verifique `backend/VRP_SERVICE/email_service.py`.")
                    else:
                        with st.spinner("Enviando relatório por email..."):
                            # Busca o reporte salvo no DB
                            conn = get_conn()
                            report_row = conn.execute(
                                "SELECT docx_path, pdf_path FROM reports WHERE checklist_id = ?",
                                (cid,),
                            ).fetchone()
                            conn.close()

                            docx_path = report_row["docx_path"] if report_row and report_row["docx_path"] else ""
                            pdf_path = report_row["pdf_path"] if report_row and report_row["pdf_path"] else ""

                            # Se não há relatório, gera primeiro
                            if not docx_path or not os.path.isfile(docx_path):
                                ai_text = st.session_state.get("ai_text") or _get_saved_ai_text(cid) or generate_ai_summary(cid)
                                try:
                                    docx_path, pdf_path = generate_full_report(cid, ai_text)  # assinatura antiga
                                except TypeError:
                                    docx_path, pdf_path = generate_full_report(cid, ai_text, "frontend/assets/exports")  # assinatura nova

                                st.success("Relatório gerado automaticamente para envio.")

                            # Caminhos das fotos marcadas para o relatório
                            photos_paths = _get_photos_paths(cid)

                            # Dispara o envio
                            success = email_service.send_report_email(
                                checklist_id=cid,
                                report_path=docx_path,
                                photos_paths=photos_paths,
                                recipients=destinatarios
                            )
                            if success:
                                st.success("✅ Relatório enviado com sucesso!")
                                st.info(f"📧 Enviado para {len(destinatarios)} destinatário(s)")
                            else:
                                st.error("❌ Falha ao enviar relatório. Verifique as configurações de email.")
