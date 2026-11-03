from pathlib import Path
from typing import List, Optional
import csv

from entidades import EstruturaDadosEducacional, RegistroMatricula, normalizar_texto

DIRETORIOS_CSV_PADRAO = [
    Path(__file__).resolve().parent.parent / "data" / "csv_matriculas",
]


def converter_inteiro(valor: str | int | None) -> int:
    if valor is None:
        return 0
    texto = str(valor).strip()
    if not texto:
        return 0
    try:
        return int(float(texto.replace(",", ".")))
    except ValueError:
        return 0


def localizar_arquivos_csv(diretorio_customizado: Optional[str | Path] = None) -> List[Path]:
    candidatos: List[Path] = []
    if diretorio_customizado:
        candidatos.append(Path(diretorio_customizado))
    candidatos.extend(DIRETORIOS_CSV_PADRAO)

    for pasta in candidatos:
        if pasta.exists() and pasta.is_dir():
            arquivos = sorted(pasta.glob("matriculas-por-unidade-escolar-*.csv"))
            if arquivos:
                return arquivos
    return []


def ler_arquivo_csv(caminho_csv: Path) -> List[RegistroMatricula]:
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    conteudo_linhas = None

    for enc in encodings:
        try:
            with open(caminho_csv, mode="r", encoding=enc, newline="") as f:
                conteudo_linhas = list(csv.DictReader(f))
                break
        except UnicodeDecodeError:
            continue

    if conteudo_linhas is None:
        raise RuntimeError(f"Não foi possível decodificar o arquivo CSV: {caminho_csv}")

    registros: List[RegistroMatricula] = []
    for linha in conteudo_linhas:
        if not linha:
            continue
        nome_mun = normalizar_texto(linha.get("NomeMunicipio", ""))
        nome_esc = normalizar_texto(linha.get("NomeUnidadeEscolar", ""))
        ano = converter_inteiro(linha.get("AnoReferencia"))

        if not nome_mun or not nome_esc or ano <= 0:
            continue

        registros.append(
            RegistroMatricula(
                id_csv=converter_inteiro(linha.get("_id")),
                ano_referencia=ano,
                nome_municipio=nome_mun,
                nome_unidade_escolar=nome_esc,
                matriculas_total=converter_inteiro(linha.get("MatriculasTotal")),
                matricula_inicial=converter_inteiro(linha.get("MatriculaInicial")),
                matricula_apos_censo=converter_inteiro(linha.get("MatriculaAposCenso")),
                transferidos=converter_inteiro(linha.get("Transferidos")),
                cancelados=converter_inteiro(linha.get("Cancelados")),
                falecido=converter_inteiro(linha.get("Falecido")),
                abandono=converter_inteiro(linha.get("Abandono")),
                aprovados=converter_inteiro(linha.get("Aprovados")),
                reprovados=converter_inteiro(linha.get("Reprovados")),
                cursando=converter_inteiro(linha.get("Cursando")),
                outras_situacoes=converter_inteiro(linha.get("OutrasSituacoes")),
            )
        )
    return registros


def carregar_em_memoria(diretorio_csv: Optional[str | Path] = None) -> EstruturaDadosEducacional:
    arquivos = localizar_arquivos_csv(diretorio_csv)
    estrutura = EstruturaDadosEducacional()
    for arq in arquivos:
        for reg in ler_arquivo_csv(arq):
            estrutura.inserir_registro(reg)
    return estrutura