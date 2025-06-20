import requests
import os
import json
import pandas as pd
import glob
import re
from datetime import datetime

# =============================
# Bronze - Ingestão da API
# =============================
def coletar_dados_api():
    url = "https://api.openbrewerydb.org/v1/breweries"
    response = requests.get(url)
    if response.status_code == 200:
        dados = response.json()
        os.makedirs("data/bronze", exist_ok=True)
        caminho = f"data/bronze/breweries_{datetime.now().date()}.json"
        with open(caminho, "w") as f:
            json.dump(dados, f, indent=2)
        print(f"Arquivo salvo em {caminho}")
    else:
        raise Exception(f"Erro ao acessar API: {response.status_code} - {response.text}")

# =============================
# Silver - Transformação
# =============================

def transformar_para_silver():
    arquivos = glob.glob("data/bronze/*.json")
    if not arquivos:
        raise FileNotFoundError("Nenhum JSON encontrado na pasta bronze")

    def pegar_data(nome):
        achou = re.search(r"(\d{4}-\d{2}-\d{2})", nome)
        return datetime.strptime(achou.group(1), "%Y-%m-%d") if achou else datetime.min

    arquivos.sort(key=pegar_data, reverse=True)
    arquivo_recente = arquivos[0]

    df = pd.read_json(arquivo_recente)

    colunas = [
        'id', 'name', 'brewery_type', 'city', 'state_province',
        'postal_code', 'country', 'longitude', 'latitude', 'phone', 'website_url'
    ]

    df = df[colunas].rename(columns={
        'id': 'ID', 'name': 'NAME', 'brewery_type': 'TYPE BREWERY',
        'city': 'CITY', 'state_province': 'STATE PROVINCE',
        'postal_code': 'POSTAL CODE', 'country': 'COUNTRY',
        'longitude': 'LONGITUDE', 'latitude': 'LATITUDE',
        'phone': 'PHONE', 'website_url': 'URL WEBSITE'
    })

    df['TYPE BREWERY'] = df['TYPE BREWERY'].str.upper().str.strip()
    df['STATE PROVINCE'] = df['STATE PROVINCE'].str.upper().str.strip()
    df['COUNTRY'] = df['COUNTRY'].str.upper().str.strip()
    df['CITY'] = df['CITY'].str.upper().str.strip()
    df['PHONE'] = df['PHONE'].astype('Int64')
    df['URL WEBSITE'] = df['URL WEBSITE'].str.replace(r'^https?://', '', regex=True)

    df = df[(df['LATITUDE'].between(-90, 90)) & (df['LONGITUDE'].between(-180, 180))]
    df = df.fillna({col: 'Unknown' if df[col].dtype == 'object' else 0 for col in df.columns})

    os.makedirs("data/silver", exist_ok=True)
    df.to_parquet("data/silver/breweries.parquet", partition_cols=['STATE PROVINCE'], index=False)
    print("Silver exportado com sucesso")

# =============================
# Validação
# =============================

def validar_silver():
    path = "data/silver/breweries.parquet"
    if not os.path.exists(path):
        raise FileNotFoundError("Arquivo Parquet não encontrado")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValueError("DataFrame está vazio")
    if "STATE PROVINCE" not in df.columns:
        raise ValueError("Coluna 'STATE PROVINCE' ausente")

    print("Silver validado com sucesso")

# =============================
# Gold - Agregações
# =============================

def gerar_aggregacoes():
    df = pd.read_parquet("data/silver/breweries.parquet")
    print(df.columns)
    df1 = df.groupby(['STATE PROVINCE', 'TIPO'], observed=True).size().reset_index(name='COUNT_BREWERY')
    df2 = df.groupby(['PAIS'], observed=True).size().reset_index(name='COUNT_COUNTRY')
    df3 = df.groupby(['TIPO'], observed=True).size().reset_index(name='COUNT_TYPE')
    df4 = df.groupby(['STATE PROVINCE'], observed=True).size().reset_index(name='TOTAL BREWERIES')
    df5 = df4.sort_values(by='TOTAL BREWERIES', ascending=False).head(10)
    df6 = df[~df['SITE'].str.contains(r'\.', na=False)]

    os.makedirs("data/gold", exist_ok=True)

    df1.to_parquet("data/gold/state_type.parquet", index=False)
    df2.to_parquet("data/gold/country.parquet", index=False)
    df3.to_parquet("data/gold/type.parquet", index=False)
    df4.to_parquet("data/gold/state_total.parquet", index=False)
    df5.to_parquet("data/gold/top_states.parquet", index=False)
    df6.to_parquet("data/gold/sem_site.parquet", index=False)

    print("Gold gerado com sucesso")
