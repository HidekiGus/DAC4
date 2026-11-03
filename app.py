from ler_csv import carregar_em_memoria


def main() -> None:
    estrutura = carregar_em_memoria()
    resumo = estrutura.resumo_estatistico()

    print("=== RESUMO DA ESTRUTURA EM MEMÓRIA ===")
    print(f"Anos carregados: {resumo['anos']}")
    print(f"Municípios únicos (MS): {resumo['total_municipios']}")
    print(f"Unidades escolares únicas: {resumo['total_escolas']}")
    print(f"Total de registros: {resumo['total_registros']}")

    print("\nTop 5 Escolas com Maior Abandono em 2023:")
    for r in estrutura.top_escolas_maior_abandono(n=5, ano=2023):
        print(f" - {r.nome_unidade_escolar} ({r.nome_municipio}): {r.taxa_abandono_total}%")


if __name__ == "__main__":
    main()