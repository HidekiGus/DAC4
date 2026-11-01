from pathlib import Path
from ler_csv import ler_arquivo_csv


def main() -> None:
    caminho = Path("data/matriculas-por-unidade-escolar-2018.csv")
    registros = ler_arquivo_csv(caminho)

    primeiro = registros[0]
    print(f"Escola: {primeiro.nome_unidade_escolar} ({primeiro.nome_municipio})")
    print(f"Matrículas: {primeiro.matriculas_total}")
    print(f"Taxa de Aprovação (Concluintes): {primeiro.taxa_aprovacao_concluintes}%")
    print(f"Taxa de Abandono (Total): {primeiro.taxa_abandono_total}%")

    """for registro in registros:
        print(f"Escola: {registro.nome_unidade_escolar} ({registro.nome_municipio})")
        print(f"Matrículas: {registro.matriculas_total}")
        print(f"Taxa de Aprovação (Concluintes): {registro.taxa_aprovacao_concluintes}%")
        print(f"Taxa de Abandono (Total): {registro.taxa_abandono_total}%")"""

if __name__ == "__main__":
    main()