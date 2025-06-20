from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import os
import json
import pandas as pd
import glob
import re
import shutil

# ============================
# Funções auxiliares
# ============================

# Limpa a pasta da Silver antes de salvar novo parquet
def limpar_silver():
    caminho = "/opt/airflow/data/silver"
    if os.path.exists(caminho):
        shutil.rmtree(caminho)
    os.makedirs(caminho)

# Limpa a pasta da Gold antes de salvar novos agregados
def limpar_gold():
    caminho = "/opt/airflow/data/gold"
    if os.path.exists(caminho):
        shutil.rmtree(caminho)
    os.makedirs(caminho)

# ============================
# BRONZE - Ingestão da API
# ============================
def coletar_dados_api():
    url = "https://api.openbrewerydb.org/v1/breweries"
    resposta = requests.get(url)
    if resposta.status_code == 200:
        dados = resposta.json()
        os.makedirs("/opt/airflow/data/bronze", exist_ok=True)
        caminho = f"/opt/airflow/data/bronze/breweries_{datetime.now().date()}.json"
        with open(caminho, "w") as f:
            json.dump(dados, f, indent=2)
        print(f" Dados salvos em: {caminho}")
    else:
        raise Exception(f"Erro na API: {resposta.status_code} - {resposta.text}")


# ============================
# SILVER - Transformação
# ============================

def transformar_para_silver():
    limpar_silver()  # Limpa a pasta antes de salvar novo dado

    arquivos = glob.glob("/opt/airflow/data/bronze/*.json")
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo JSON encontrado na bronze.")

    def extrair_data(nome):
        match = re.search(r"(\d{4}-\d{2}-\d{2})", nome)
        return datetime.strptime(match.group(1), "%Y-%m-%d") if match else datetime.min

    arquivos.sort(key=extrair_data, reverse=True)
    caminho_arquivo = arquivos[0]

    df = pd.read_json(caminho_arquivo)

    colunas = [
        'id', 'name', 'brewery_type', 'city', 'state_province',
        'postal_code', 'country', 'longitude', 'latitude', 'phone', 'website_url'
    ]
    df = df[colunas].rename(columns={
        'id': 'ID', 'name': 'NOME', 'brewery_type': 'TIPO',
        'city': 'CIDADE', 'state_province': 'ESTADO',
        'country': 'PAIS', 'longitude': 'LONGITUDE',
        'latitude': 'LATITUDE', 'phone': 'TELEFONE',
        'website_url': 'SITE', 'postal_code': 'CEP'
    })

    for col in ['TIPO', 'ESTADO', 'PAIS', 'CIDADE']:
        df[col] = df[col].astype(str).str.strip().str.upper()

    df['TELEFONE'] = df['TELEFONE'].astype('Int64')
    df['SITE'] = df['SITE'].str.replace(r'^https?://', '', regex=True)

    df = df[(df['LATITUDE'].between(-90, 90)) & (df['LONGITUDE'].between(-180, 180))]
    df = df.fillna({col: 'Unknown' if df[col].dtype == 'object' else 0 for col in df.columns})

    df.to_parquet("/opt/airflow/data/silver/breweries.parquet", partition_cols=['ESTADO'], index=False)
    print("Dados salvos na camada Silver.")


# ============================
# VALIDAÇÃO - Silver
# ============================

def validar_silver():
    caminho = "/opt/airflow/data/silver/breweries.parquet"
    if not os.path.exists(caminho):
        raise FileNotFoundError("Arquivo Parquet da Silver não encontrado.")

    df = pd.read_parquet(caminho)
    if df.empty:
        raise ValueError("DataFrame Silver está vazio.")
    if "ESTADO" not in df.columns:
        raise ValueError("Coluna 'ESTADO' não encontrada.")

    print("Silver validada com sucesso.")


# ============================
# GOLD - Agregações
# ============================
def gerar_aggregacoes():
    limpar_gold()  # Limpa a pasta antes de salvar novos dados

    df = pd.read_parquet("/opt/airflow/data/silver/breweries.parquet")

    df_estado_tipo = df.groupby(['ESTADO', 'TIPO'], observed=True).size().reset_index(name='QTD_CERVEJARIAS')
    df_pais = df.groupby(['PAIS'], observed=True).size().reset_index(name='QTD_POR_PAIS')
    df_tipo = df.groupby(['TIPO'], observed=True).size().reset_index(name='QTD_POR_TIPO')
    df_estado_total = df.groupby(['ESTADO'], observed=True).size().reset_index(name='TOTAL_ESTADO')
    top_estados = df_estado_total.sort_values(by='TOTAL_ESTADO', ascending=False).head(10)
    sem_site = df[~df['SITE'].str.contains(r'\.', na=False)]

    df_estado_tipo.to_parquet("/opt/airflow/data/gold/estado_tipo.parquet", index=False)
    df_pais.to_parquet("/opt/airflow/data/gold/pais.parquet", index=False)
    df_tipo.to_parquet("/opt/airflow/data/gold/tipo.parquet", index=False)
    df_estado_total.to_parquet("/opt/airflow/data/gold/estado.parquet", index=False)
    top_estados.to_parquet("/opt/airflow/data/gold/top_estados.parquet", index=False)
    sem_site.to_parquet("/opt/airflow/data/gold/sem_site.parquet", index=False)

    print("Agregações salvas na Gold.")


# ============================
# DAG
# ============================

default_args = {
    'owner': 'lucascarvalho',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=10),
    'email_on_failure': True,
    'email': ['lucasfilip54@gmail.com'],
    'email_on_retry': False,
}

with DAG(
    dag_id='beer_pipeline',
    default_args=default_args,
    description='Pipeline: Bronze -> Silver -> Validação -> Gold',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['beer']
) as dag:

    extrair = PythonOperator(
        task_id='extrair_bronze',
        python_callable=coletar_dados_api
    )

    transformar = PythonOperator(
        task_id='transformar_silver',
        python_callable=transformar_para_silver
    )

    validar = PythonOperator(
        task_id='validar_silver',
        python_callable=validar_silver
    )

    agregar = PythonOperator(
        task_id='gerar_gold',
        python_callable=gerar_aggregacoes
    )

    extrair >> transformar >> validar >> agregar
