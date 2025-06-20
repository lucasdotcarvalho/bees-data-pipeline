FROM continuumio/anaconda3

# Instalação de bibliotecas necessárias
RUN pip install --no-cache-dir \
    pandas \
    requests \
    pyarrow \
    fastparquet \
    jupyterlab

COPY ./

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--NotebookApp.token=''", "--NotebookApp.password=''"]
