from __future__ import annotations
from dataclasses import dataclass, field
import heapq
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

def normalizar_texto(texto: str) -> str:
    """
    Normaliza strings removendo espaços extras e padronizando caixa alta,
    preservando acentuação legível quando possível e corrigindo artefatos de encoding.
    """
    if not texto:
        return ""
    limpo = " ".join(str(texto).strip().split())
    return limpo

def chave_canonica(texto: str) -> str:
    """
    Gera uma chave canônica sem acentos e em letras maiúsculas para indexação
    em tabelas hash (evitando duplicatas como 'Camapua' vs 'Camapuã' ou 'Tres Lagoas' vs 'Três Lagoas').
    """
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove caracteres corrompidos residuais se houver
    apenas_ascii = "".join(c if c.isalnum() or c in " -." else "" for c in sem_acento)
    return " ".join(apenas_ascii.upper().split())

@dataclass
class RegistroMatricula:
    """
    Representa o registro anual de matrículas e situações de uma Unidade Escolar.
    Aplica encapsulamento e propriedades calculadas para indicadores da ODS 4.
    """
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
        """Soma de alunos com resultado final consolidado (Aprovados + Reprovados + Abandono)."""
        return self.aprovados + self.reprovados + self.abandono
    
    @property
    def matriculas_efetivas(self) -> int:
        """
        Matrículas líquidas permanecentes na escola (Total menos Transferidos, Cancelados e Falecidos).
        Se for menor ou igual a zero, retorna matriculas_total como fallback seguro.
        """
        efetivas = self.matriculas_total - (self.transferidos + self.cancelados + self.falecido)
        return efetivas if efetivas > 0 else self.matriculas_total
    
    @property
    def taxa_aprovacao_total(self) -> float:
        """Percentual de aprovados em relação ao total de matrículas."""
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.aprovados / self.matriculas_total) * 100.0, 2)
    
    @property
    def taxa_aprovacao_concluintes(self) -> float:
        """
        Indicador ODS 4: Taxa de rendimento/aprovação entre alunos com situação final definida
        (Aprovados / (Aprovados + Reprovados + Abandono)).
        """
        base = self.total_desfechos_avaliados
        if base <= 0:
            return 0.0
        return round((self.aprovados / base) * 100.0, 2)
    
    @property
    def taxa_abandono_total(self) -> float:
        """Percentual de abandono em relação ao total de matrículas."""
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.abandono / self.matriculas_total) * 100.0, 2)
    
    @property
    def taxa_abandono_concluintes(self) -> float:
        """Indicador ODS 4: Taxa de abandono entre desfechos definidos."""
        base = self.total_desfechos_avaliados
        if base <= 0:
            return 0.0
        return round((self.abandono / base) * 100.0, 2)
    
    @property
    def taxa_reprovacao_total(self) -> float:
        """Percentual de reprovação em relação ao total de matrículas."""
        if self.matriculas_total <= 0:
            return 0.0
        return round((self.reprovados / self.matriculas_total) * 100.0, 2)
    
    def to_dict(self) -> dict:
        """Converte o objeto para dicionário estruturado para DataFrames e serialização."""
        return {
            "id_csv": self.id_csv,
            "ano_referencia": self.ano_referencia,
            "nome_municipio": self.nome_municipio,
            "nome_unidade_escolar": self.nome_unidade_escolar,
            "matriculas_total": self.matriculas_total,
            "matricula_inicial": self.matricula_inicial,
            "matricula_apos_censo": self.matricula_apos_censo,
            "transferidos": self.transferidos,
            "cancelados": self.cancelados,
            "falecido": self.falecido,
            "abandono": self.abandono,
            "aprovados": self.aprovados,
            "reprovados": self.reprovados,
            "cursando": self.cursando,
            "outras_situacoes": self.outras_situacoes,
            "taxa_aprovacao_total": self.taxa_aprovacao_total,
            "taxa_aprovacao_concluintes": self.taxa_aprovacao_concluintes,
            "taxa_abandono_total": self.taxa_abandono_total,
            "taxa_reprovacao_total": self.taxa_reprovacao_total,
        }
    
@dataclass
class UnidadeEscolar:
    """
    Entidade Orientada a Objetos que representa uma escola da rede pública de MS
    e mantém em memória sua série histórica ordenada por ano.
    """
    nome: str
    municipio: str
    chave_escola: str = field(init=False)
    historico_por_ano: Dict[int, RegistroMatricula] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chave_escola = chave_canonica(self.nome)

    def adicionar_registro(self, registro: RegistroMatricula) -> None:
        """Insere ou atualiza um registro anual na estrutura em memória da escola."""
        ano = registro.ano_referencia
        if ano in self.historico_por_ano:
            existente = self.historico_por_ano[ano]
            existente.matriculas_total += registro.matriculas_total
            existente.matricula_inicial += registro.matricula_inicial
            existente.matricula_apos_censo += registro.matricula_apos_censo
            existente.transferidos += registro.transferidos
            existente.cancelados += registro.cancelados
            existente.falecido += registro.falecido
            existente.abandono += registro.abandono
            existente.aprovados += registro.aprovados
            existente.reprovados += registro.reprovados
            existente.cursando += registro.cursando
            existente.outras_situacoes += registro.outras_situacoes
        else:
            self.historico_por_ano[ano] = registro

    @property
    def anos_ativos(self) -> List[int]:
        """Retorna a lista ordenada de anos em que a escola possui registros."""
        return sorted(self.historico_por_ano.keys())
    
    @property
    def total_matriculas_historico(self) -> int:
        return sum(r.matriculas_total for r in self.historico_por_ano.values())
    
    @property
    def total_aprovados_historico(self) -> int:
        return sum(r.aprovados for r in self.historico_por_ano.values())
    
    @property
    def total_abandono_historico(self) -> int:
        return sum(r.abandono for r in self.historico_por_ano.values())
    
@dataclass
class Municipio:
    """
    Entidade Orientada a Objetos que agrega as Unidades Escolares pertencentes
    a um município de Mato Grosso do Sul.
    """
    nome: str
    chave_municipio: str = field(init=False)
    escolas: Dict[str, UnidadeEscolar] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chave_municipio = chave_canonica(self.nome)

    def obter_ou_criar_escola(self, nome_escola: str) -> UnidadeEscolar:
        chave = chave_canonica(nome_escola)
        if chave not in self.escolas:
            self.escolas[chave] = UnidadeEscolar(nome=normalizar_texto(nome_escola), municipio=self.nome)
        return self.escolas[chave]
    
    @property
    def quantidade_escolas(self) -> int:
        return len(self.escolas)
    
class EstruturaDadosEducacional:
    """
    Estrutura de Dados em Memória para organização eficiente dos registros.
    Utiliza:
      - Tabelas Hash (dicionários aninhados) para busca O(1) por município e escola;
      - Índice invertido por ano (Dict[int, List[RegistroMatricula]]) para filtragem temporal rápida;
      - Conjuntos (Set) para controle de anos e municípios únicos;
      - Heap (fila de prioridade via heapq) para extração eficiente dos Top-N rankings.
    """

    def __init__(self) -> None:
        self.municipios: Dict[str, Municipio] = {}
        self.indice_por_ano: Dict[int, List[RegistroMatricula]] = {}
        self.todos_registros: List[RegistroMatricula] = []
        self.anos_disponiveis: Set[int] = set()

    def inserir_registro(self, registro: RegistroMatricula) -> None:
        """Insere um RegistroMatricula atualizando todos os índices em memória."""
        chave_mun = chave_canonica(registro.nome_municipio)
        if chave_mun not in self.municipios:
            self.municipios[chave_mun] = Municipio(nome=normalizar_texto(registro.nome_municipio))
        municipio_obj = self.municipios[chave_mun]
        # Padroniza o nome do município no registro com o nome canônico registrado
        registro.nome_municipio = municipio_obj.nome
        escola_obj = municipio_obj.obter_ou_criar_escola(registro.nome_unidade_escolar)
        registro.nome_unidade_escolar = escola_obj.nome
        escola_obj.adicionar_registro(registro)
        ano = registro.ano_referencia
        self.anos_disponiveis.add(ano)

        if ano not in self.indice_por_ano:
            self.indice_por_ano[ano] = []

        self.indice_por_ano[ano].append(registro)
        self.todos_registros.append(registro)

    def filtrar(
        self,
        ano: Optional[int] = None,
        municipio: Optional[str] = None,
        escola: Optional[str] = None,
    ) -> List[RegistroMatricula]:
        """Filtra registros em memória utilizando os índices de ano e município."""
        base = self.indice_por_ano.get(ano, []) if ano is not None else self.todos_registros
        resultado = base
        if municipio and municipio != "Todos":
            chave_mun = chave_canonica(municipio)
            resultado = [r for r in resultado if chave_canonica(r.nome_municipio) == chave_mun]
        if escola and escola != "Todas":
            chave_esc = chave_canonica(escola)
            resultado = [r for r in resultado if chave_canonica(r.nome_unidade_escolar) == chave_esc]
        return resultado
    
    def top_escolas_por_aprovacao(self, n: int = 10, ano: Optional[int] = None, min_matriculas: int = 50) -> List[RegistroMatricula]:
        """Utiliza fila de prioridade (heapq.nlargest) para retornar as N escolas com maior taxa de aprovação."""
        candidatos = [
            r for r in self.filtrar(ano=ano)
            if r.matriculas_total >= min_matriculas and r.total_desfechos_avaliados > 0
        ]
        return heapq.nlargest(n, candidatos, key=lambda r: (r.taxa_aprovacao_concluintes, r.aprovados))
    
    def top_escolas_maior_abandono(self, n: int = 10, ano: Optional[int] = None, min_matriculas: int = 50) -> List[RegistroMatricula]:
        """Utiliza fila de prioridade (heapq.nlargest) para identificar as N escolas mais críticas em abandono escolar."""
        candidatos = [
            r for r in self.filtrar(ano=ano)
            if r.matriculas_total >= min_matriculas and r.abandono > 0
        ]
        return heapq.nlargest(n, candidatos, key=lambda r: (r.taxa_abandono_total, r.abandono))
    
    def resumo_estatistico(self) -> dict:
        """Retorna métricas globais da estrutura carregada em memória."""
        total_escolas = sum(m.quantidade_escolas for m in self.municipios.values())
        return {
            "total_municipios": len(self.municipios),
            "total_escolas": total_escolas,
            "total_registros": len(self.todos_registros),
            "anos": sorted(self.anos_disponiveis),
        }