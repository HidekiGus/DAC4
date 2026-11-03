from __future__ import annotations
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple
import pandas as pd
from entidades import EstruturaDadosEducacional, RegistroMatricula, chave_canonica
SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS municipios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave_canonica TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS unidades_escolares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    municipio_id INTEGER NOT NULL,
    chave_canonica TEXT NOT NULL,
    nome TEXT NOT NULL,
    FOREIGN KEY (municipio_id) REFERENCES municipios(id) ON DELETE CASCADE,
    UNIQUE (municipio_id, chave_canonica)
);
CREATE TABLE IF NOT EXISTS matriculas_historicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidade_escolar_id INTEGER NOT NULL,
    ano_referencia INTEGER NOT NULL,
    id_csv_original INTEGER,
    matriculas_total INTEGER NOT NULL DEFAULT 0,
    matricula_inicial INTEGER NOT NULL DEFAULT 0,
    matricula_apos_censo INTEGER NOT NULL DEFAULT 0,
    transferidos INTEGER NOT NULL DEFAULT 0,
    cancelados INTEGER NOT NULL DEFAULT 0,
    falecido INTEGER NOT NULL DEFAULT 0,
    abandono INTEGER NOT NULL DEFAULT 0,
    aprovados INTEGER NOT NULL DEFAULT 0,
    reprovados INTEGER NOT NULL DEFAULT 0,
    cursando INTEGER NOT NULL DEFAULT 0,
    outras_situacoes INTEGER NOT NULL DEFAULT 0,
    taxa_aprovacao_total REAL NOT NULL DEFAULT 0.0,
    taxa_aprovacao_concluintes REAL NOT NULL DEFAULT 0.0,
    taxa_abandono_total REAL NOT NULL DEFAULT 0.0,
    taxa_reprovacao_total REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (unidade_escolar_id) REFERENCES unidades_escolares(id) ON DELETE CASCADE,
    UNIQUE (unidade_escolar_id, ano_referencia)
);
CREATE INDEX IF NOT EXISTS idx_unidades_municipio ON unidades_escolares(municipio_id);
CREATE INDEX IF NOT EXISTS idx_matriculas_ano ON matriculas_historicas(ano_referencia);
CREATE INDEX IF NOT EXISTS idx_matriculas_escola ON matriculas_historicas(unidade_escolar_id);
DROP VIEW IF EXISTS vw_serie_historica_completa;
CREATE VIEW vw_serie_historica_completa AS
SELECT
    mh.id AS registro_id,
    mh.ano_referencia,
    m.id AS municipio_id,
    m.nome AS nome_municipio,
    ue.id AS unidade_escolar_id,
    ue.nome AS nome_unidade_escolar,
    mh.matriculas_total,
    mh.matricula_inicial,
    mh.matricula_apos_censo,
    mh.transferidos,
    mh.cancelados,
    mh.falecido,
    mh.abandono,
    mh.aprovados,
    mh.reprovados,
    mh.cursando,
    mh.outras_situacoes,
    mh.taxa_aprovacao_total,
    mh.taxa_aprovacao_concluintes,
    mh.taxa_abandono_total,
    mh.taxa_reprovacao_total
FROM matriculas_historicas mh
INNER JOIN unidades_escolares ue ON mh.unidade_escolar_id = ue.id
INNER JOIN municipios m ON ue.municipio_id = m.id;
"""

class DatabaseManager:
    """Gerenciador de persistência relacional SQLite para a série histórica escolar de MS."""
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir (parents=True, exist_ok=True)
    def conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    
    def inicializar_schema(self) -> None:
        """Cria as tabelas, chaves estrangeiras, índices e views caso não existam."""
        with self.conectar() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def limpar_dados(self) -> None:
        """Remove todos os registros existentes antes de uma recarga completa."""
        with self.conectar() as conn:
            conn.execute("DELETE FROM matriculas_historicas;")
            conn.execute("DELETE FROM unidades_escolares;")
            conn.execute("DELETE FROM municipios;")
            conn.commit()

    def persistir_estrutura(self, estrutura: EstruturaDadosEducacional, limpar_antes: bool = True) -> dict:
        """
        Persiste toda a EstruturaDadosEducacional (classes OO em memória) no banco SQLite
        utilizando transações atômicas para máxima performance e integridade referencial.
        """
        self.inicializar_schema()
        if limpar_antes:
            self.limpar_dados()
        municipios_inseridos = 0
        escolas_inseridas = 0
        matriculas_inseridas = 0
        with self.conectar() as conn:
            cursor = conn.cursor()
            for chave_mun, municipio_obj in sorted(estrutura.municipios.items()):
                cursor.execute(
                    """
                    INSERT INTO municipios (chave_canonica, nome)
                    VALUES (?, ?)
                    ON CONFLICT(chave_canonica) DO UPDATE SET nome = excluded.nome
                    RETURNING id;
                    """,
                    (chave_mun, municipio_obj.nome),
                )
                municipio_id = cursor.fetchone()[0]
                municipios_inseridos += 1
                for chave_esc, escola_obj in sorted(municipio_obj.escolas.items()):
                    cursor.execute(
                        """
                        INSERT INTO unidades_escolares (municipio_id, chave_canonica, nome)
                        VALUES (?, ?, ?)
                        ON CONFLICT(municipio_id, chave_canonica) DO UPDATE SET nome = excluded.nome
                        RETURNING id;
                        """,
                        (municipio_id, chave_esc, escola_obj.nome),
                    )
                    escola_id = cursor.fetchone()[0]
                    escolas_inseridas += 1
                    for ano, reg in sorted(escola_obj.historico_por_ano.items()):
                        cursor.execute(
                            """
                            INSERT INTO matriculas_historicas (
                                unidade_escolar_id, ano_referencia, id_csv_original,
                                matriculas_total, matricula_inicial, matricula_apos_censo,
                                transferidos, cancelados, falecido,
                                abandono, aprovados, reprovados,
                                cursando, outras_situacoes,
                                taxa_aprovacao_total, taxa_aprovacao_concluintes,
                                taxa_abandono_total, taxa_reprovacao_total
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(unidade_escolar_id, ano_referencia) DO UPDATE SET
                                matriculas_total = excluded.matriculas_total,
                                matricula_inicial = excluded.matricula_inicial,
                                matricula_apos_censo = excluded.matricula_apos_censo,
                                transferidos = excluded.transferidos,
                                cancelados = excluded.cancelados,
                                falecido = excluded.falecido,
                                abandono = excluded.abandono,
                                aprovados = excluded.aprovados,
                                reprovados = excluded.reprovados,
                                cursando = excluded.cursando,
                                outras_situacoes = excluded.outras_situacoes,
                                taxa_aprovacao_total = excluded.taxa_aprovacao_total,
                                taxa_aprovacao_concluintes = excluded.taxa_aprovacao_concluintes,
                                taxa_abandono_total = excluded.taxa_abandono_total,
                                taxa_reprovacao_total = excluded.taxa_reprovacao_total;
                            """,
                            (
                                escola_id,
                                ano,
                                reg.id_csv,
                                reg.matriculas_total,
                                reg.matricula_inicial,
                                reg.matricula_apos_censo,
                                reg.transferidos,
                                reg.cancelados,
                                reg.falecido,
                                reg.abandono,
                                reg.aprovados,
                                reg.reprovados,
                                reg.cursando,
                                reg.outras_situacoes,
                                reg.taxa_aprovacao_total,
                                reg.taxa_aprovacao_concluintes,
                                reg.taxa_abandono_total,
                                reg.taxa_reprovacao_total,
                            ),
                        )
                        matriculas_inseridas += 1
            conn.commit()
        return {
            "municipios_persistidos": municipios_inseridos,
            "escolas_persistidas": escolas_inseridas,
            "matriculas_persistidas": matriculas_inseridas,
        }
    
    def carregar_estrutura_do_banco(self) -> EstruturaDadosEducacional:
        """Reconstrói a EstruturaDadosEducacional em memória a partir dos registros do SQLite."""
        estrutura = EstruturaDadosEducacional()

        if not self.db_path.exists():
            return estrutura
        
        with self.conectar() as conn:
            cursor = conn.execute(
                """
                SELECT
                    registro_id AS id_csv,
                    ano_referencia,
                    nome_municipio,
                    nome_unidade_escolar,
                    matriculas_total,
                    matricula_inicial,
                    matricula_apos_censo,
                    transferidos,
                    cancelados,
                    falecido,
                    abandono,
                    aprovados,
                    reprovados,
                    cursando,
                    outras_situacoes
                FROM vw_serie_historica_completa
                ORDER BY ano_referencia ASC, nome_municipio ASC, nome_unidade_escolar ASC;
                """
            )

            for row in cursor.fetchall():
                reg = RegistroMatricula(
                    id_csv=row["id_csv"],
                    ano_referencia=row["ano_referencia"],
                    nome_municipio=row["nome_municipio"],
                    nome_unidade_escolar=row["nome_unidade_escolar"],
                    matriculas_total=row["matriculas_total"],
                    matricula_inicial=row["matricula_inicial"],
                    matricula_apos_censo=row["matricula_apos_censo"],
                    transferidos=row["transferidos"],
                    cancelados=row["cancelados"],
                    falecido=row["falecido"],
                    abandono=row["abandono"],
                    aprovados=row["aprovados"],
                    reprovados=row["reprovados"],
                    cursando=row["cursando"],
                    outras_situacoes=row["outras_situacoes"],
                )
                estrutura.inserir_registro(reg)
        return estrutura
    
    def consultar_dataframe(
        self,
        anos: Optional[List[int]] = None,
        municipios: Optional[List[str]] = None,
        busca_escola: Optional[str] = None,
    ) -> pd.DataFrame:
        """Executa consulta parametrizada na View SQL retornando um DataFrame Pandas."""
        query = "SELECT * FROM vw_serie_historica_completa WHERE 1=1"
        params: list = []
        if anos:
            placeholders = ",".join("?" for _ in anos)
            query += f" AND ano_referencia IN ({placeholders})"
            params.extend(anos)
        if municipios:
            placeholders = ",".join("?" for _ in municipios)
            query += f" AND nome_municipio IN ({placeholders})"
            params.extend(municipios)
        if busca_escola and busca_escola.strip():
            query += " AND UPPER(nome_unidade_escolar) LIKE ?"
            params.append(f"%{busca_escola.strip().upper()}%")
        query += " ORDER BY ano_referencia ASC, nome_municipio ASC, nome_unidade_escolar ASC"
        with self.conectar() as conn:
            return pd.read_sql_query(query, conn, params=params)
        
    def evolucao_anual_agregada(self, municipios: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Consulta SQL agregada por ano para construir as curvas de evolução histórica
        de aprovação, reprovação e abandono escolar (ODS 4).
        """
        filtro_mun = ""
        params: list = []
        if municipios:
            placeholders = ",".join("?" for _ in municipios)
            filtro_mun = f"WHERE nome_municipio IN ({placeholders})"
            params.extend(municipios)
        query = f"""
        SELECT
            ano_referencia,
            COUNT(DISTINCT municipio_id) AS total_municipios,
            COUNT(DISTINCT unidade_escolar_id) AS total_escolas,
            SUM(matriculas_total) AS matriculas_total,
            SUM(matricula_inicial) AS matricula_inicial,
            SUM(matricula_apos_censo) AS matricula_apos_censo,
            SUM(transferidos) AS transferidos,
            SUM(cancelados) AS cancelados,
            SUM(falecido) AS falecido,
            SUM(abandono) AS abandono,
            SUM(aprovados) AS aprovados,
            SUM(reprovados) AS reprovados,
            SUM(cursando) AS cursando,
            SUM(outras_situacoes) AS outras_situacoes,
            ROUND(
                CASE WHEN SUM(matriculas_total) > 0
                THEN (CAST(SUM(aprovados) AS REAL) / SUM(matriculas_total)) * 100.0
                ELSE 0.0 END, 2
            ) AS taxa_aprovacao_total,
            ROUND(
                CASE WHEN (SUM(aprovados) + SUM(reprovados) + SUM(abandono)) > 0
                THEN (CAST(SUM(aprovados) AS REAL) / (SUM(aprovados) + SUM(reprovados) + SUM(abandono))) * 100.0
                ELSE 0.0 END, 2
            ) AS taxa_aprovacao_concluintes,
            ROUND(
                CASE WHEN SUM(matriculas_total) > 0
                THEN (CAST(SUM(abandono) AS REAL) / SUM(matriculas_total)) * 100.0
                ELSE 0.0 END, 2
            ) AS taxa_abandono_total,
            ROUND(
                CASE WHEN (SUM(aprovados) + SUM(reprovados) + SUM(abandono)) > 0
                THEN (CAST(SUM(abandono) AS REAL) / (SUM(aprovados) + SUM(reprovados) + SUM(abandono))) * 100.0
                ELSE 0.0 END, 2
            ) AS taxa_abandono_concluintes,
            ROUND(
                CASE WHEN SUM(matriculas_total) > 0
                THEN (CAST(SUM(reprovados) AS REAL) / SUM(matriculas_total)) * 100.0
                ELSE 0.0 END, 2
            ) AS taxa_reprovacao_total
        FROM vw_serie_historica_completa
        {filtro_mun}
        GROUP BY ano_referencia
        ORDER BY ano_referencia ASC;
        """
        with self.conectar() as conn:
            return pd.read_sql_query(query, conn, params=params)