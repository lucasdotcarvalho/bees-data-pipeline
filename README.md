# BEES Data Engineering – Breweries Pipeline

Este projeto tem como objetivo construir um pipeline de dados orquestrado com Apache Airflow para consumir, transformar e disponibilizar dados da Open Brewery DB seguindo a arquitetura em camadas Medallion: **Bronze**, **Silver** e **Gold**.

O teste proposto tem como foco avaliar habilidades em:

* Consumo de dados via API
* Transformação e tratamento de dados
* Armazenamento em camadas (Data Lake)
* Orquestração de pipeline com retries e validações
* Modularização com Docker e Airflow

## Tecnologias Utilizadas

* Python 3.12
* Apache Airflow 2.9.1
* Docker
* Parquet

## Estrutura da Arquitetura Medallion

```
bees-case/
├── airflow_pipeline/         
│   └── dags/
│       └── beer_dag.py       # DAG Consolidada estrutura Data Lake finalizada
├── └── Dockerfile            # Dockerfile para ambiente local (ex: Jupyter)
├── └── docker-compose
├── └── pipeline_functions.py # Arquivo local separado de Airflow para testes
├── └── teste_pipeline.py     # Executável de teste pipeline_functions.py


├── notebooks/                # Scripts Jupyter originais com estrutura Data Lake teste
        ├── data/                     
│       ├── bronze/
│       ├── silver/
│       └── gold/


└── README.md                 # Documentação do projeto
```

---

## Schedule & Retry

* DAG agendada para rodar **diariamente** (`@daily`)
* Configuração de **3 tentativas** em caso de falha
* Timeout de **10 minutos** por execução

---

## Fluxo de Execução da DAG

A DAG `beer_pipeline` realiza as seguintes tarefas:

### 1. `extrair_bronze`

* Acessa a API da Open Brewery DB
* Salva o retorno bruto da API como `.json` na pasta `data/bronze`
* Nome do arquivo é gerado com a data atual

### 2. `transformar_silver`

* Lê o arquivo mais recente da Bronze
* Limpa, trata e padroniza as colunas relevantes
* Salva um arquivo `breweries.parquet` particionado por estado na pasta `silver`
* Trunca a pasta Silver antes de salvar

### 3. `validar_silver`

* Valida se o arquivo existe, se possui registros e se a coluna `ESTADO` está presente

### 4. `gerar_gold`

* Realiza agregados:

  * Contagem de cervejarias por estado e tipo
  * Total por país e por tipo
  * Top 10 estados com mais cervejarias
  * Lista de cervejarias sem site
* Trunca a pasta Gold antes de salvar novos arquivos `.parquet`

---

## Como Rodar

1. Clone o repositório:

```bash
git clone https://github.com/lucasdotcarvalho/bees-data-pipeline.git
cd bees-data-pipeline
```

2. Suba os containers:

```bash
docker compose up -d --build
```

3. Acesse o Airflow:

```
http://localhost:8080
```

### Login no Airflow

* **Usuário:** admin
* **Senha:** admin

4. Ative a DAG `beer_pipeline` e aguarde a execução.
   
---

## Rodar Localmente (Teste)

1. Execute o arquivo test_pipeline.py ele executará de forma localmente de forma separada ao airflow.

---

## Monitoramento

* Possibilidade de integrar com e-mail em caso de falha

---

### Camada Silver:

* `breweries.parquet` particionado por estado

### Camada Gold:

* `estado_tipo.parquet`
* `pais.parquet`
* `tipo.parquet`
* `estado.parquet`
* `top_estados.parquet`
* `sem_site.parquet`

---

## Considerações Finais

Evitei abstrações desnecessárias para deixar o código acessível e legível para outros desenvolvedores.

---

## Autor

Lucas Carvalho
linkedin/lucas-carvalho-664b1014b/
