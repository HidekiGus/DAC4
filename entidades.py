from __future__ import annotations
from dataclasses import dataclass, field
import unicodedata
from typing import Dict, List


def normalizar_texto(texto: str) -> str:
    #Remove espaços extras preservando a acentuação.
    if not texto:
        return ""
    limpo = " ".join(str(texto).strip().split())
    return limpo


def chave_canonica(texto: str) -> str:
    #Gera uma chave canônica sem acentos para evitar duplicatas.
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    apenas_ascii = "".join(c if c.isalnum() or c in " -." else "" for c in sem_acento)
    return " ".join(apenas_ascii.upper().split())


@dataclass
class RegistroMatricula:
    #Representa o registro anual de matrículas e situações de uma escola
    id_csv: int
    ano_referencia: int
    nome_municipio: str
    nome_unidade_escolar: str
    matriculas_total: int
    matricula_inicial: int
    matricula_apos_censo: int
    transferidos: int
    cancelados: int
    falecido: int
    abandono: int
    aprovados: int
    reprovados: int
    cursando: int
    outras_situacoes: int

    @property
    def total_desfechos_avaliados(self) -> int:
        return self.aprovados + self.reprovados + self.abandono

    @property
    def taxa_aprovacao_total(self) -> float:
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.aprovados / self.matriculas_total) * 100.0, 2)

    @property
    def taxa_aprovacao_concluintes(self) -> float:
        base = self.total_desfechos_avaliados
        if base <= 0:
            return 0.0
        return round((self.aprovados / base) * 100.0, 2)

    @property
    def taxa_abandono_total(self) -> float:
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.abandono / self.matriculas_total) * 100.0, 2)

    @property
    def taxa_reprovacao_total(self) -> float:
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.reprovados / self.matriculas_total) * 100.0, 2)


@dataclass
class UnidadeEscolar:
    #Representa uma escola da rede pública de MS e seu histórico por ano.
    nome: str
    municipio: str
    chave_escola: str = field(init=False)
    historico_por_ano: Dict[int, RegistroMatricula] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chave_escola = chave_canonica(self.nome)

    def adicionar_registro(self, registro: RegistroMatricula) -> None:
        self.historico_por_ano[registro.ano_referencia] = registro


@dataclass
class Municipio:
    #Agrega as Unidades Escolares pertencentes a um município de MS.
    nome: str
    chave_municipio: str = field(init=False)
    escolas: Dict[str, UnidadeEscolar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chave_municipio = chave_canonica(self.nome)

    def obter_ou_criar_escola(self, nome_escola: str) -> UnidadeEscolar:
        chave = chave_canonica(nome_escola)
        if chave not in self.escolas:
            self.escolas[chave] = UnidadeEscolar(
                nome=normalizar_texto(nome_escola),
                municipio=self.nome,
            )
        return self.escolas[chave]