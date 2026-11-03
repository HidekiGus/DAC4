"""
Módulo ETL (Extract, Transform, Load) para Carga Automática dos CSVs (2018-2026).

Realiza:
1. Descoberta automática de todos os arquivos `matriculas-por-unidade-escolar-*.csv`;
2. Tratamento de encoding (UTF-8 / Latin-1) e limpeza de valores numéricos e nomes;
3. Instanciação dos objetos de domínio (`RegistroMatricula`, `UnidadeEscolar`, `Municipio`)
   dentro da `EstruturaDadosEducacional` em memória;
4. Persistência relacional completa no banco SQLite (`educacao_ms.db`).
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import List, Optional, Tuple

from database import DatabaseManager
from entidades import EstruturaDadosEducacional, RegistroMatricula, normalizar_texto


# Diretórios padrão onde os CSVs podem estar localizados
DIRETORIOS_CSV_PADRAO = [
    Path(__file__).resolve().parent.parent / "data" / "csv_matriculas",
    Path(r"C:\Users\Gus\Documents\DAC4\csv matrículas"),
]

CAMINHO_DB_PADRAO = Path(__file__).resolve().parent.parent / "data" / "educacao_ms.db"


def converter_inteiro(valor: str | int | None) -> int:
    """Converte um valor textual de célula CSV para inteiro com fallback seguro para 0."""
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
    """Localiza todos os arquivos CSV da série histórica (2018-2026)."""
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
    """
    Lê um arquivo CSV anual testando codificações UTF-8 e Latin-1,
    convertendo cada linha válida em um objeto `RegistroMatricula`.
    """
    registros: List[RegistroMatricula] = []
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

    conteudo_linhas = None
    for enc in encodings:
        try:
            with open(caminho_csv, mode="r", encoding=enc, newline="") as f:
                leitor = list(csv.DictReader(f))
                conteudo_linhas = leitor
                break
        except UnicodeDecodeError:
            continue

    if conteudo_linhas is None:
        raise RuntimeError(f"Não foi possível decodificar o arquivo CSV: {caminho_csv}")

    for linha in conteudo_linhas:
        if not linha:
            continue
        nome_mun = normalizar_texto(linha.get("NomeMunicipio", ""))
        nome_esc = normalizar_texto(linha.get("NomeUnidadeEscolar", ""))
        ano = converter_inteiro(linha.get("AnoReferencia"))

        if not nome_mun or not nome_esc or ano <= 0:
            continue

        reg = RegistroMatricula(
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
        registros.append(reg)

    return registros


def executar_pipeline_etl(
    diretorio_csv: Optional[str | Path] = None,
    caminho_db: Optional[str | Path] = None,
) -> Tuple[EstruturaDadosEducacional, dict]:
    """
    Executa o pipeline completo de carga:
      1. Localiza e lê todos os CSVs (2018-2026);
      2. Popula a EstruturaDadosEducacional e classes OO em memória;
      3. Persiste todos os dados normalizados no banco SQLite;
      4. Retorna a estrutura carregada e um relatório detalhado da carga.
    """
    arquivos = localizar_arquivos_csv(diretorio_csv)
    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo 'matriculas-por-unidade-escolar-*.csv' foi encontrado."
        )

    estrutura = EstruturaDadosEducacional()
    relatorio_arquivos = {}

    for arq in arquivos:
        registros_ano = ler_arquivo_csv(arq)
        for reg in registros_ano:
            estrutura.inserir_registro(reg)
        relatorio_arquivos[arq.name] = len(registros_ano)

    db_destino = Path(caminho_db) if caminho_db else CAMINHO_DB_PADRAO
    db_manager = DatabaseManager(db_destino)
    resumo_db = db_manager.persistir_estrutura(estrutura, limpar_antes=True)
    resumo_mem = estrutura.resumo_estatistico()

    relatorio = {
        "arquivos_processados": len(arquivos),
        "linhas_por_arquivo": relatorio_arquivos,
        "caminho_banco": str(db_destino),
        **resumo_mem,
        **resumo_db,
    }
    return estrutura, relatorio


if __name__ == "__main__":
    _, info = executar_pipeline_etl()
    print("=== PIPELINE ETL CONCLUÍDO COM SUCESSO ===")
    print(f"Banco SQLite gerado em: {info['caminho_banco']}")
    print(f"Arquivos CSV processados: {info['arquivos_processados']}")
    print(f"Anos carregados: {info['anos']}")
    print(f"Total de Municípios únicos (normalizados): {info['total_municipios']}")
    print(f"Total de Unidades Escolares únicas: {info['total_escolas']}")
    print(f"Total de Registros Históricos persistidos: {info['matriculas_persistidas']}")
    print("\nDetalhamento por arquivo:")
    for nome_arq, qtd in info["linhas_por_arquivo"].items():
        print(f"  - {nome_arq}: {qtd} registros")