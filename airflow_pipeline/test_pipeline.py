from pipeline_functions import (
    coletar_dados_api,
    transformar_para_silver,
    validar_silver,
    gerar_aggregacoes
)

if __name__ == "__main__":
    print("🔁 Executando pipeline local...\n")

    coletar_dados_api()
    transformar_para_silver()
    validar_silver()
    gerar_aggregacoes()

    print("\n✅ Pipeline finalizado com sucesso.")
