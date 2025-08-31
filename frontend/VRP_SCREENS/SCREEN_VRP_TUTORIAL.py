"""
Tela de Tutorial VRP: guia de manutenção e melhores práticas para válvulas redutoras (base Cla-Val 100-01 Hytrol).
Conteúdo resumido do manual técnico (instalação / operação / manutenção) em etapas práticas.
"""
import streamlit as st
from frontend.VRP_STYLES.layout import page_setup, app_header, section_card, pill

def _steps(prefix: str, items: list[str]):
    """Desenha uma lista de passos com checkboxes; prefix evita colisões de chave."""
    cols = st.columns(1)
    done = 0
    for i, txt in enumerate(items):
        if cols[0].checkbox(txt, key=f"{prefix}_{i}"):
            done += 1
    st.caption(f"Concluídos: {done}/{len(items)}")

def render():
    page_setup("VRP • Tutorial", icon="📘")
    app_header(
        "Tutorial de Manutenção da VRP",
        "Procedimento padrão (segurança → instalação → operação → diagnóstico → manutenção)."
    )

    # Contexto / avisos rápidos
    pill("Base técnica: Cla-Val 100-01 Hytrol", "success")
    pill("Atenção: realizar intervenções SEM pressão", "warning")
    st.caption("Este guia resume etapas recomendadas e cautelas do fabricante para válvulas redutoras do tipo pilotada.")

    # 1) Segurança e pré-requisitos
    with section_card("1) Segurança e pré-requisitos"):
        st.write(
            "- Confirme isolamento hidráulico **a montante e a jusante** sempre que houver risco (bloqueio total para manutenção).\n"
            "- Antes de pressurizar: **purgue ar** do tampo e da tubulação de pilotagem nos pontos altos.\n"
            "- Em instalações com **metais dissimilares**, use conexões/dielétricos adequados para evitar ação galvânica.\n"
            "- Garanta área de trabalho livre para ajuste e **desmontagem vertical do tampo** (obrigatório em diâmetros ≥ 8”)."
        )
        _steps("seg", [
            "Bloquear montante e jusante (quando aplicável)",
            "Tagout/Lockout aplicado",
            "Despressurizar válvula (tampo e corpo)",
            "Confirmar ausência de fluxo/pressão residual",
        ])

    # 2) Instalação (visão geral)
    with section_card("2) Instalação (visão geral)"):
        st.write(
            "- **Lave** a linha antes de instalar (remoção de cavacos/escamas).\n"
            "- Instale **válvulas de bloqueio** nos dois lados para manutenção.\n"
            "- Respeite a **direção de fluxo** indicada na plaqueta (normal: “up-and-over” → falha aberta; reversa: “over-and-down” → falha fechada).\n"
            "- Preferencial: tubulação horizontal **com tampo para cima**; outras posições são aceitas, mas evite esforço no conjunto interno."
        )
        _steps("inst", [
            "Linha lavada",
            "Bloqueios previstos (montante/jusante)",
            "Direção de fluxo confirmada na plaqueta",
            "Posição com tampo para cima (se possível)",
        ])

    # 3) Princípios de operação
    with section_card("3) Princípios de operação"):
        st.write(
            "- **Fechamento estanque**: aplica pressão de comando acima do diafragma → o disco veda no assento.\n"
            "- **Abertura total**: alívio da câmara do diafragma para zona de menor pressão → a pressão de linha **abre** a válvula (≥ 5 psi de diferencial).\n"
            "- **Modulação**: piloto varia a pressão na câmara do diafragma conforme a pressão de linha, posicionando a abertura."
        )

    # 4) Partida / comissionamento
    with section_card("4) Partida / comissionamento"):
        st.write(
            "- Com a válvula instalada e o sistema pressurizado, **ventile o ar** da câmara do tampo e da pilotagem (pontos altos).\n"
            "- Verifique estanqueidade em conexões, drenos e tampo; ajuste gradual dos pilotos conforme setpoint de jusante."
        )
        _steps("start", [
            "Venting feito (tubo de pilotagem e tampo)",
            "Checagem de vazamentos",
            "Ajuste inicial do piloto (pressão de saída)",
        ])

    # 5) Ferramentas recomendadas (diagnóstico)
    with section_card("5) Ferramentas recomendadas (diagnóstico)"):
        st.write(
            "- **3 manômetros** (montante, jusante e câmara do tampo) para leitura simultânea.\n"
            "- **Indicador de posição X101** (Cla-Val) para ver o curso sem abrir a válvula.\n"
            "- Ferramental comum: chaves, morsa de mordentes macios, **lixa 400** e água (polimento leve), materiais de limpeza."
        )

    # 6) Manutenção preventiva (sugestão de rotina)
    with section_card("6) Manutenção preventiva (sugestão)"):
        st.write(
            "- A válvula **não requer lubrificação**; inspecione periodicamente efeito das condições de operação.\n"
            "- Planeje inspeções com reparos **fora de pressão**; tenha kit de reparo (diafragma, disco, espaçadores) disponível.\n"
            "- Remoção de incrustações: banho breve em **solução 5% de ácido muriático** (enxaguar bem) ou polimento leve com lixa 400."
        )
        _steps("pm", [
            "Inspeção visual de conexões e pilotagem",
            "Leitura comparada de pressões (mca) montante/jusante",
            "Teste de operação (modulação/estanqueidade)",
            "Plano de reposição de elastômeros",
        ])

    # 7) Diagnóstico rápido (as 3 verificações)
    with section_card("7) Diagnóstico rápido (3 verificações)"):
        st.write("**Problemas típicos** concentram-se no conjunto **diafragma+disco** (peça móvel única):")
        st.markdown(
            "- Válvula **presa** (curso não completo)\n"
            "- **Diafragma danificado** (não fecha)\n"
            "- **Vazamento no assento** (mesmo com curso livre)"
        )
        st.subheader("Verificações (ordem sugerida)")
        st.markdown(
            "1. **Check do diafragma**: tampar câmara aberta à atmosfera, pressurizar levemente o corpo; fluxo contínuo pelo respiro indica dano/folga no diafragma.\n"
            "2. **Liberdade de movimento**: observar curso via X101 ou movimentar manualmente (sem pressão) e comparar com **curso nominal** por porte; remover obstrução/escala se houver.\n"
            "3. **Vedação**: com jusante bloqueado e pressão no tampo, observar se a pressão entre válvulas sobe até a montante (indica passagem pela sede)."
        )
        st.caption("⚠️ Cada verificação pode abrir totalmente a válvula ou elevar rapidamente a pressão a jusante — avaliar risco e isolar conforme a instalação.")

    # 8) Desmontagem (sem retirar da linha)
    with section_card("8) Desmontagem (sem retirar da linha)"):
        st.write(
            "- **Sempre sem pressão** no corpo e tampo; aliviar pressão da pilotagem.\n"
            "- Remover tampo **verticalmente** (atenção ao rolamento/guia do eixo). Em diâmetros maiores, usar olhal/elevador.\n"
            "- Retirar o conjunto **diafragma+disco+guia**; inspecionar, limpar, substituir elastômeros se necessário.\n"
            "- Evitar danos ao **haste/rolamentos**; riscos geram travamento."
        )
        _steps("disasm", [
            "Isolamento e despressurização confirmados",
            "Pilotagem aliviada e desconectada (marcar posições)",
            "Tampo removido com cuidado",
            "Conjunto retirado e inspecionado",
        ])

    # 9) Remontagem e torque
    with section_card("9) Remontagem e torque"):
        st.write(
            "- Montar disco com **leve compressão** (arruelas espaçadoras corretas) e **apertar a porca da haste com golpes firmes** (evita que o diafragma gire/escape sob pressão).\n"
            "- Assentar o tampo e **apertar em padrão “estrela” (cross-over)** em **3 estágios** (≈10%, ≈75% e final). Reapertar após 24h em ensaios ≥ 375 psi.\n"
            "- Reinstalar a pilotagem, sangrar ar em pontos altos e conferir estanqueidade do tampo."
        )
        _steps("asm", [
            "Diafragma/Disco/Arruelas conferidos",
            "Porca da haste travada (golpes curtos na chave)",
            "Tampo torqueado em estrela (3 estágios)",
            "Pilotagem reinstalada e purgada",
        ])

    # 10) Testes pós-montagem
    with section_card("10) Testes pós-montagem"):
        st.write(
            "- **Curso livre**: elevar/baixar diafragma (sem pressão) ou observar via X101; curso aproximado depende do diâmetro nominal.\n"
            "- **Fechamento estanque**: conduzir pressão do inlet para o tampo; a válvula deve **fechar sem gotejamento**, mesmo a pressões baixas (≈10 psi)."
        )
        _steps("tests", [
            "Curso nominal verificado",
            "Estanqueidade verificada (sem gotejamento)",
            "Checagem final de vazamentos externos",
            "Setpoint do piloto conferido",
        ])

    st.caption("Observação: valores e cautelas de cada etapa devem respeitar características locais da rede (pressões em mca) e o porte do equipamento.")
