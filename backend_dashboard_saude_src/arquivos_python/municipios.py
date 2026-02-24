import os
import sys
import pandas as pd
from datetime import datetime
import requests
from io import StringIO

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.models.user import db, User
from src.models.health_data import HealthCase, Municipality, HealthUnit

# Configurar Flask app para acesso ao banco
app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = (
    "mysql+pymysql://root:123456@172.22.1.2:3306/dashboard_saude?charset=utf8mb4"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

import json

def gerar_municipios_sql():
    # Estrutura base para você não depender de download
    # Estou enviando o comando que gera o arquivo SQL no seu disco
    output_file = "popula_tudo.sql"
    
    print("🛠️ Gerando arquivo SQL de municípios...")
    
    # Início do comando SQL
    sql_header = "INSERT INTO municipalities (id, name, uf, region, latitude, longitude, population) VALUES \n"
    
    # Simulação de dados para o arquivo (Ajuste para o volume real no seu servidor)
    # Como o chat tem limite, este script cria a estrutura. 
    # Para ter os 5570 AGORA, use o comando SQL abaixo do script.
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(sql_header)
        # Exemplo de entrada (Aqui você pode colar a lista que te enviei antes)
        f.write("('3550308', 'São Paulo', 'SP', 'Sudeste', -23.5489, -46.6388, NULL),\n")
        f.write("('3304557', 'Rio de Janeiro', 'RJ', 'Sudeste', -22.9035, -43.2096, NULL),\n")
        f.write("('3136700', 'Belo Horizonte', 'MG', 'Sudeste', -19.9209, -43.9378, NULL);\n")
        
    print(f"✅ Arquivo {output_file} gerado com sucesso!")


def main():
    gerar_municipios_sql()


if __name__ == "__main__":
    gerar_municipios_sql()
