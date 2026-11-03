"""
Interface Analítica e Dashboard Interativo em Streamlit (DAC - ODS 4: Educação de Qualidade).

Apresenta a série histórica (2018-2026) da rede pública de ensino de Mato Grosso do Sul,
conectando a camada de Persistência Relacional (SQLite) e a Estrutura de Dados
Orientada a Objetos em memória (`EstruturaDadosEducacional`).
"""

from __future__ import annotations
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

from database import DatabaseManager
from ler_csv import CAMINHO_DB_PADRAO, executar_pipeline_etl


st.set_page_config(
    page_title="DAC ODS 4 — Educação Pública em MS (2018-2026)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def inicializar_sistema():
    """Garante que o banco SQLite está populado e carrega a estrutura OO em memória."""
    db_manager = DatabaseManager(CAMINHO_DB_PADRAO)
    if not CAMINHO_DB_PADRAO.exists():
        estrutura, relatorio = executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
    else:
        estrutura = db_manager.carregar_estrutura_do_banco()
        if not estrutura.todos_registros:
            estrutura, relatorio = executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
        else:
            relatorio = estrutura.resumo_estatistico()
    return db_manager, estrutura, relatorio


def main() -> None:
    db_manager, estrutura, relatorio = inicializar_sistema()

    # Cabeçalho principal
    st.title("📊 Painel Analítico ODS 4 — Educação de Qualidade em MS (2018–2026)")
    st.markdown(
        "**Desafio de Articulação de Competências (DAC) — UCDB** | "
        "Análise da série histórica de matrículas, aprovação, reprovação e abandono escolar "
        "na rede estadual de Mato Grosso do Sul."
    )

    # Barra lateral de filtros dinâmicos
    with st.sidebar:
        st.header("🔍 Filtros Dinâmicos")

        anos_disponiveis = sorted(estrutura.anos_disponiveis)
        anos_selecionados = st.multiselect(
            "Anos de Referência:",
            options=anos_disponiveis,
            default=anos_disponiveis,
            help="Selecione um ou mais anos da série histórica (2018 a 2026).",
        )

        lista_municipios = sorted(m.nome for m in estrutura.municipios.values())
        municipios_selecionados = st.multiselect(
            "Municípios (MS):",
            options=lista_municipios,
            default=[],
            placeholder="Todos os 79 municípios",
            help="Deixe em branco para analisar todo o estado de Mato Grosso do Sul.",
        )

        busca_escola = st.text_input(
            "Filtrar por Unidade Escolar:",
            value="",
            placeholder="Ex.: EZEQUIEL, CEEJA, CEEP...",
        )

        min_matriculas_ranking = st.slider(
            "Mínimo de matrículas para Rankings:",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
        )

        st.divider()
        if st.button("🔄 Recarregar CSVs (Executar ETL)", use_container_width=True):
            st.cache_resource.clear()
            executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
            st.success("Base SQLite e estruturas em memória atualizadas com sucesso!")
            st.rerun()

        st.caption(
            f"**Status do Sistema:**\n"
            f"- Municípios mapeados: **{len(estrutura.municipios)}**\n"
            f"- Escolas catalogadas: **{relatorio.get('total_escolas', 0)}**\n"
            f"- Registros históricos: **{len(estrutura.todos_registros):,}**"
        )

    if not anos_selecionados:
        st.warning("Selecione pelo menos um Ano de Referência na barra lateral.")
        return

    # Consulta parametrizada no SQLite
    df_filtrado = db_manager.consultar_dataframe(
        anos=anos_selecionados,
        municipios=municipios_selecionados if municipios_selecionados else None,
        busca_escola=busca_escola,
    )

    if df_filtrado.empty:
        st.info("Nenhum registro encontrado para a combinação de filtros selecionada.")
        return

    # Cálculo das métricas consolidadas (KPIs ODS 4)
    total_matriculas = int(df_filtrado["matriculas_total"].sum())
    total_aprovados = int(df_filtrado["aprovados"].sum())
    total_reprovados = int(df_filtrado["reprovados"].sum())
    total_abandono = int(df_filtrado["abandono"].sum())
    total_cursando = int(df_filtrado["cursando"].sum())
    total_desfechos = total_aprovados + total_reprovados + total_abandono

    taxa_aprov_concluintes = (total_aprovados / total_desfechos * 100.0) if total_desfechos > 0 else 0.0
    taxa_abandono_geral = (total_abandono / total_matriculas * 100.0) if total_matriculas > 0 else 0.0
    taxa_reprov_concluintes = (total_reprovados / total_desfechos * 100.0) if total_desfechos > 0 else 0.0
    escolas_unicas = int(df_filtrado["unidade_escolar_id"].nunique())
    municipios_unicos = int(df_filtrado["municipio_id"].nunique())

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Matrículas Totais", f"{total_matriculas:,}".replace(",", "."))
    col2.metric(
        "Taxa de Aprovação (Concluintes)",
        f"{taxa_aprov_concluintes:.2f}%",
        help="Aprovados / (Aprovados + Reprovados + Abandono)",
    )
    col3.metric(
        "Taxa de Abandono (Evasão)",
        f"{taxa_abandono_geral:.2f}%",
        delta=f"{total_abandono:,} alunos".replace(",", "."),
        delta_color="inverse",
        help="Total de abandonos sobre o total de matrículas no recorte.",
    )
    col4.metric(
        "Taxa de Reprovação (Concluintes)",
        f"{taxa_reprov_concluintes:.2f}%",
        help="Reprovados / (Aprovados + Reprovados + Abandono)",
    )
    col5.metric(
        "Escolas / Municípios",
        f"{escolas_unicas} / {municipios_unicos}",
        help="Quantidade de unidades escolares e municípios presentes no filtro atual.",
    )

    st.divider()

    aba_evolucao, aba_rankings, aba_dados = st.tabs([
        "📈 Evolução Histórica (2018–2026)",
        "🏆 Rankings e Diagnóstico por Município / Escola",
        "🗄️ Explorador SQL & Estruturas OO",
    ])

    with aba_evolucao:
        df_evolucao = (
            df_filtrado.groupby("ano_referencia", as_index=False)
            .agg(
                matriculas_total=("matriculas_total", "sum"),
                aprovados=("aprovados", "sum"),
                reprovados=("reprovados", "sum"),
                abandono=("abandono", "sum"),
                cursando=("cursando", "sum"),
                transferidos=("transferidos", "sum"),
                cancelados=("cancelados", "sum"),
            )
            .sort_values("ano_referencia")
        )
        df_evolucao["desfechos"] = (
            df_evolucao["aprovados"] + df_evolucao["reprovados"] + df_evolucao["abandono"]
        )
        df_evolucao["Taxa de Aprovação (%)"] = df_evolucao.apply(
            lambda r: round((r["aprovados"] / r["desfechos"]) * 100.0, 2) if r["desfechos"] > 0 else 0.0,
            axis=1,
        )
        df_evolucao["Taxa de Abandono (%)"] = df_evolucao.apply(
            lambda r: round((r["abandono"] / r["matriculas_total"]) * 100.0, 2)
            if r["matriculas_total"] > 0
            else 0.0,
            axis=1,
        )
        df_evolucao["Taxa de Reprovação (%)"] = df_evolucao.apply(
            lambda r: round((r["reprovados"] / r["desfechos"]) * 100.0, 2) if r["desfechos"] > 0 else 0.0,
            axis=1,
        )

        c_graf1, c_graf2 = st.columns(2)

        with c_graf1:
            st.subheader("Evolução das Taxas de Aprovação, Reprovação e Abandono (%)")
            df_taxas_long = df_evolucao.melt(
                id_vars=["ano_referencia"],
                value_vars=["Taxa de Aprovação (%)", "Taxa de Reprovação (%)", "Taxa de Abandono (%)"],
                var_name="Indicador",
                value_name="Percentual",
            )
            chart_taxas = (
                alt.Chart(df_taxas_long)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("ano_referencia:O", title="Ano de Referência"),
                    y=alt.Y("Percentual:Q", title="Taxa (%)"),
                    color=alt.Color(
                        "Indicador:N",
                        scale=alt.Scale(
                            domain=[
                                "Taxa de Aprovação (%)",
                                "Taxa de Reprovação (%)",
                                "Taxa de Abandono (%)",
                            ],
                            range=["#2e7d32", "#f57c00", "#c62828"],
                        ),
                    ),
                    tooltip=["ano_referencia:O", "Indicador:N", "Percentual:Q"],
                )
                .properties(height=360)
            )
            st.altair_chart(chart_taxas, use_container_width=True)

        with c_graf2:
            st.subheader("Distribuição de Situações de Matrícula por Ano")
            df_vol_long = df_evolucao.melt(
                id_vars=["ano_referencia"],
                value_vars=["aprovados", "reprovados", "abandono", "cursando", "transferidos"],
                var_name="Situação",
                value_name="Quantidade",
            )
            chart_vol = (
                alt.Chart(df_vol_long)
                .mark_bar()
                .encode(
                    x=alt.X("ano_referencia:O", title="Ano de Referência"),
                    y=alt.Y("Quantidade:Q", title="Número de Alunos"),
                    color=alt.Color("Situação:N", title="Situação"),
                    tooltip=["ano_referencia:O", "Situação:N", "Quantidade:Q"],
                )
                .properties(height=360)
            )
            st.altair_chart(chart_vol, use_container_width=True)

        st.markdown("#### Tabela Consolidada Anual")
        st.dataframe(
            df_evolucao[
                [
                    "ano_referencia",
                    "matriculas_total",
                    "aprovados",
                    "reprovados",
                    "abandono",
                    "cursando",
                    "Taxa de Aprovação (%)",
                    "Taxa de Reprovação (%)",
                    "Taxa de Abandono (%)",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with aba_rankings:
        st.subheader("Diagnóstico por Município e Unidade Escolar (Estruturas em Memória)")
        ano_foco = st.selectbox(
            "Selecione um ano específico para o Ranking de Escolas (ou 'Série Completa'):",
            options=["Série Completa"] + sorted(anos_selecionados, reverse=True),
            index=0,
        )
        ano_param = None if ano_foco == "Série Completa" else int(ano_foco)

        top_aprov = estrutura.top_escolas_por_aprovacao(
            n=10, ano=ano_param, min_matriculas=min_matriculas_ranking
        )
        top_aband = estrutura.top_escolas_maior_abandono(
            n=10, ano=ano_param, min_matriculas=min_matriculas_ranking
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("##### 🟢 Top 10 Unidades Escolares — Maior Taxa de Aprovação")
            if top_aprov:
                df_top_aprov = pd.DataFrame([r.to_dict() for r in top_aprov])[
                    [
                        "ano_referencia",
                        "nome_municipio",
                        "nome_unidade_escolar",
                        "matriculas_total",
                        "aprovados",
                        "taxa_aprovacao_concluintes",
                    ]
                ]
                st.dataframe(df_top_aprov, use_container_width=True, hide_index=True)
            else:
                st.info("Sem registros com desfechos concluídos para o critério selecionado.")

        with col_r2:
            st.markdown("##### 🔴 Top 10 Unidades Escolares — Maior Taxa de Abandono (Alerta ODS 4)")
            if top_aband:
                df_top_aband = pd.DataFrame([r.to_dict() for r in top_aband])[
                    [
                        "ano_referencia",
                        "nome_municipio",
                        "nome_unidade_escolar",
                        "matriculas_total",
                        "abandono",
                        "taxa_abandono_total",
                    ]
                ]
                st.dataframe(df_top_aband, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum registro com abandono positivo encontrado para este filtro.")

        st.markdown("##### Comparativo Agregado por Município (Recorte Atual)")
        df_mun = (
            df_filtrado.groupby("nome_municipio", as_index=False)
            .agg(
                escolas=("unidade_escolar_id", "nunique"),
                matriculas_total=("matriculas_total", "sum"),
                aprovados=("aprovados", "sum"),
                reprovados=("reprovados", "sum"),
                abandono=("abandono", "sum"),
                cursando=("cursando", "sum"),
            )
            .sort_values("matriculas_total", ascending=False)
        )
        df_mun["Taxa Aprovação Concluintes (%)"] = df_mun.apply(
            lambda r: round(
                (r["aprovados"] / (r["aprovados"] + r["reprovados"] + r["abandono"])) * 100.0, 2
            )
            if (r["aprovados"] + r["reprovados"] + r["abandono"]) > 0
            else 0.0,
            axis=1,
        )
        df_mun["Taxa Abandono (%)"] = df_mun.apply(
            lambda r: round((r["abandono"] / r["matriculas_total"]) * 100.0, 2)
            if r["matriculas_total"] > 0
            else 0.0,
            axis=1,
        )
        st.dataframe(df_mun, use_container_width=True, hide_index=True)

    with aba_dados:
        st.subheader("Registros Detalhados (View Relacional `vw_serie_historica_completa`)")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        csv_bytes = df_filtrado.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 Exportar Dados Filtrados (.CSV)",
            data=csv_bytes,
            file_name="dados_filtrados_educacao_ms.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()