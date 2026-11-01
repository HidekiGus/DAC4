from pathlib import Path
from ler_csv import ler_csv_bruto


def main() -> None:
    caminho = Path("data/matriculas-por-unidade-escolar-2018.csv")
    dados = ler_csv_bruto(caminho)

    total_matriculas = sum(item["matriculas_total"] for item in dados)
    total_abandono = sum(item["abandono"] for item in dados)

    print(f"Registros lidos: {len(dados)}")
    print(f"Total de matrículas: {total_matriculas}")
    print(f"Total de abandonos: {total_abandono}")
    if (total_matriculas > 0):
        print(f"Taxa de abandono: {total_abandono / total_matriculas:.2%}")
    else:
        print("Taxa de abandono: N/A")
    print(dados[0])


if __name__ == "__main__":
    main()