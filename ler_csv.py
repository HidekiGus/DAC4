from pathlib import Path
import csv


def converter_inteiro(valor: str | int | None) -> int:
    # Converte um valor textual do CSV para inteiro, tratando casos de valores ausentes ou inválidos.
    if valor is None:
        return 0
    texto = str(valor).strip()
    if not texto:
        return 0
    try:
        return int(float(texto.replace(",", ".")))
    except ValueError:
        return 0


def ler_csv_bruto(caminho_csv: Path) -> list[dict]:
    """Lê um arquivo CSV anual testando encodings comuns e retorna lista de dicionários."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    linhas = None

    for encoding in encodings:
        try:
            with open(caminho_csv, mode="r", encoding=encoding, newline="") as f:
                linhas = list(csv.DictReader(f))
                break
        except UnicodeDecodeError:
            continue

    if linhas is None:
        raise RuntimeError(f"Não foi possível decodificar o arquivo CSV: {caminho_csv}")

    registros = []
    for linha in linhas:
        if not linha:
            continue
        registros.append({
            "ano": converter_inteiro(linha.get("AnoReferencia")),
            "municipio": str(linha.get("NomeMunicipio", "")).strip(),
            "escola": str(linha.get("NomeUnidadeEscolar", "")).strip(),
            "matriculas_total": converter_inteiro(linha.get("MatriculasTotal")),
            "aprovados": converter_inteiro(linha.get("Aprovados")),
            "reprovados": converter_inteiro(linha.get("Reprovados")),
            "abandono": converter_inteiro(linha.get("Abandono")),
        })
    return registros