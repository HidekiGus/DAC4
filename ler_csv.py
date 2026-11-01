from pathlib import Path
from typing import List
import csv

from entidades import RegistroMatricula, normalizar_texto


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


def ler_arquivo_csv(caminho_csv: Path) -> List[RegistroMatricula]:
    #Converte cada linha válida de um arquivo CSV em um objeto RegistroMatricula
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