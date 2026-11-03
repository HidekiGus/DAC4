import streamlit as st

from src.database import DatabaseManager
from src.etl import CAMINHO_DB_PADRAO, executar_pipeline_etl

st.set_page_config(page_title="Protótipo DAC ODS 4 — Educação MS", layout="wide")


@st.cache_resource(show_spinner=False)
def inicializar_sistema():
    db_manager = DatabaseManager(CAMINHO_DB_PADRAO)
    if not CAMINHO_DB_PADRAO.exists():
        estrutura, _ = executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
    else:
        estrutura = db_manager.carregar_estrutura_do_banco()
    return db_manager, estrutura


def main() -> None:
    db_manager, estrutura = inicializar_sistema()

    st.title("Painel ODS 4 — Educação Pública em MS (Protótipo Inicial)")

    with st.sidebar:
        st.header("Filtros")
        anos_opcoes = sorted(estrutura.anos_disponiveis)
        anos_sel = st.multiselect("Anos:", options=anos_opcoes, default=anos_opcoes)

        mun_opcoes = sorted(m.nome for m in estrutura.municipios.values())
        mun_sel = st.multiselect("Municípios:", options=mun_opcoes, default=[])

    if not anos_sel:
        st.warning("Selecione pelo menos um ano.")
        return

    df = db_manager.consultar_dataframe(
        anos=anos_sel,
        municipios=mun_sel if mun_sel else None,
    )

    total_mat = int(df["matriculas_total"].sum())
    total_aprov = int(df["aprovados"].sum())
    total_aband = int(df["abandono"].sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Matrículas Totais", f"{total_mat:,}".replace(",", "."))
    c2.metric("Total de Aprovados", f"{total_aprov:,}".replace(",", "."))
    c3.metric("Total de Abandonos", f"{total_aband:,}".replace(",", "."))

    st.subheader("Registros Filtrados")
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()