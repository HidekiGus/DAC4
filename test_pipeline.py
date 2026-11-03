"""
Testes automatizados de unidade e integração para o projeto DAC ODS 4 (Educação em MS).

Valida:
1. Classes Orientadas a Objetos (`RegistroMatricula`, `UnidadeEscolar`, `Municipio`);
2. Estrutura de Dados em Memória (`EstruturaDadosEducacional`, indexação O(1) e Heap);
3. Persistência Relacional SQLite (`DatabaseManager`, integridade referencial 3FN e Views);
4. Carga completa dos 8 arquivos CSV oficiais (2018-2026).
"""

import unittest
from pathlib import Path

from database import DatabaseManager
from ler_csv import DIRETORIOS_CSV_PADRAO, executar_pipeline_etl, CAMINHO_DB_PADRAO
from entidades import   EstruturaDadosEducacional, RegistroMatricula, chave_canonica


class TestSistemaEducacionalMS(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.estrutura, cls.relatorio = executar_pipeline_etl(caminho_db=CAMINHO_DB_PADRAO)
        cls.db = DatabaseManager(CAMINHO_DB_PADRAO)

    def test_01_normalizacao_chave_canonica(self) -> None:
        self.assertEqual(chave_canonica("Camapuã"), "CAMAPUA")
        self.assertEqual(chave_canonica("Camapua"), "CAMAPUA")
        self.assertEqual(chave_canonica("Três Lagoas"), "TRES LAGOAS")
        self.assertEqual(chave_canonica("Tres Lagoas"), "TRES LAGOAS")

    def test_02_calculo_indicadores_oo(self) -> None:
        reg = RegistroMatricula(
            id_csv=1,
            ano_referencia=2023,
            nome_municipio="Campo Grande",
            nome_unidade_escolar="ESCOLA TESTE",
            matriculas_total=200,
            matricula_inicial=180,
            matricula_apos_censo=20,
            transferidos=10,
            cancelados=10,
            falecido=0,
            abandono=20,
            aprovados=140,
            reprovados=20,
            cursando=0,
            outras_situacoes=0,
        )
        self.assertEqual(reg.total_desfechos_avaliados, 180)
        self.assertEqual(reg.taxa_aprovacao_total, 70.0)
        self.assertAlmostEqual(reg.taxa_aprovacao_concluintes, 77.78, places=2)
        self.assertEqual(reg.taxa_abandono_total, 10.0)

    def test_03_carga_completa_csvs_e_79_municipios(self) -> None:
        self.assertEqual(self.relatorio["arquivos_processados"], 8)
        self.assertEqual(self.relatorio["total_municipios"], 79)
        self.assertEqual(self.relatorio["anos"], [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026])
        self.assertGreater(self.relatorio["total_escolas"], 550)
        self.assertGreater(self.relatorio["matriculas_persistidas"], 3600)

    def test_04_consultas_sql_e_filtros(self) -> None:
        df_cg = self.db.consultar_dataframe(anos=[2018, 2023], municipios=["Campo Grande"])
        self.assertFalse(df_cg.empty)
        self.assertTrue(set(df_cg["ano_referencia"].unique()).issubset({2018, 2023}))
        self.assertEqual(df_cg["nome_municipio"].unique().tolist(), ["Campo Grande"])

        df_evol = self.db.evolucao_anual_agregada()
        self.assertEqual(len(df_evol), 8)

    def test_05_rankings_heap_em_memoria(self) -> None:
        top_aprov = self.estrutura.top_escolas_por_aprovacao(n=5, ano=2022, min_matriculas=50)
        self.assertEqual(len(top_aprov), 5)
        self.assertGreaterEqual(
            top_aprov[0].taxa_aprovacao_concluintes, top_aprov[-1].taxa_aprovacao_concluintes
        )

    def test_06_reconstrucao_estrutura_do_banco(self) -> None:
        estrutura_reconstruida = self.db.carregar_estrutura_do_banco()
        resumo = estrutura_reconstruida.resumo_estatistico()
        self.assertEqual(resumo["total_municipios"], 79)
        self.assertEqual(resumo["total_escolas"], 598)
        self.assertEqual(resumo["total_registros"], 3703)


if __name__ == "__main__":
    unittest.main()