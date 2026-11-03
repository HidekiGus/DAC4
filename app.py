from database import DatabaseManager
from ler_csv import CAMINHO_DB_PADRAO, executar_pipeline_etl

def main() -> None:
    if not CAMINHO_DB_PADRAO.exists():
        executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
    db = DatabaseManager(CAMINHO_DB_PADRAO)
    df_evolucao = db.evolucao_anual_agregada()
    print("=== EVOLUÇÃO ANUAL ===")
    print(df_evolucao[["ano_referencia", "matriculas_total", "taxa_aprovacao_concluintes", "taxa_abandono_total"]])

if __name__ == "__main__":
    main()