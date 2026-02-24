#!/usr/bin/env python3
"""
Script de ingestão de dados CSV (amostra) para o dashboard de saúde
"""

import os
import sys
import pandas as pd
from datetime import datetime
import sqlite3

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from flask import Flask
from src.models.user import db, User
from src.models.health_data import HealthCase, Municipality, HealthUnit

# Configurar Flask app para acesso ao banco
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def parse_date(date_str):
    """Converter string de data para objeto date"""
    if pd.isna(date_str) or date_str == '' or date_str is None:
        return None
    
    try:
        # Tentar diferentes formatos de data
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(str(date_str), fmt).date()
            except ValueError:
                continue
        return None
    except:
        return None

def safe_int(value):
    """Converter valor para int de forma segura"""
    if pd.isna(value) or value == '' or value is None:
        return None
    try:
        return int(float(value))
    except:
        return None

def ingest_csv_sample(csv_path, disease_code, disease_name, sample_size=1000):
    """Ingerir uma amostra de um arquivo CSV"""
    print(f"Processando amostra de {csv_path} - {disease_name} ({sample_size} registros)...")
    
    try:
        # Ler apenas uma amostra do CSV
        df = pd.read_csv(csv_path, nrows=sample_size, low_memory=False)
        print(f"Amostra carregada: {len(df)} registros")
        
        cases_to_insert = []
        
        for _, row in df.iterrows():
            try:
                case = HealthCase(
                    tp_not=str(row.get('TP_NOT', '')),
                    id_agravo=disease_code,
                    disease_name=disease_name,
                    
                    # Datas
                    dt_notific=parse_date(row.get('DT_NOTIFIC')),
                    dt_sin_pri=parse_date(row.get('DT_SIN_PRI')),
                    dt_invest=parse_date(row.get('DT_INVEST')),
                    dt_obito=parse_date(row.get('DT_OBITO')),
                    dt_encerra=parse_date(row.get('DT_ENCERRA')),
                    dt_interna=parse_date(row.get('DT_INTERNA')),
                    
                    # Demografia
                    ano_nasc=safe_int(row.get('ANO_NASC')),
                    nu_idade_n=safe_int(row.get('NU_IDADE_N')),
                    cs_sexo=str(row.get('CS_SEXO', '')) if pd.notna(row.get('CS_SEXO')) else None,
                    cs_gestant=safe_int(row.get('CS_GESTANT')),
                    cs_raca=safe_int(row.get('CS_RACA')),
                    cs_escol_n=safe_int(row.get('CS_ESCOL_N')),
                    
                    # Localização
                    sg_uf_not=str(row.get('SG_UF_NOT', '')) if pd.notna(row.get('SG_UF_NOT')) else None,
                    id_municip=str(row.get('ID_MUNICIP', '')) if pd.notna(row.get('ID_MUNICIP')) else None,
                    id_regiona=str(row.get('ID_REGIONA', '')) if pd.notna(row.get('ID_REGIONA')) else None,
                    id_unidade=str(row.get('ID_UNIDADE', '')) if pd.notna(row.get('ID_UNIDADE')) else None,
                    
                    # Sintomas
                    febre=safe_int(row.get('FEBRE')),
                    mialgia=safe_int(row.get('MIALGIA')),
                    cefaleia=safe_int(row.get('CEFALEIA')),
                    exantema=safe_int(row.get('EXANTEMA')),
                    vomito=safe_int(row.get('VOMITO')),
                    nausea=safe_int(row.get('NAUSEA')),
                    dor_costas=safe_int(row.get('DOR_COSTAS')),
                    conjuntvit=safe_int(row.get('CONJUNTVIT')),
                    artrite=safe_int(row.get('ARTRITE')),
                    artralgia=safe_int(row.get('ARTRALGIA')),
                    diarreia=safe_int(row.get('DIARREIA')),
                    
                    # Comorbidades
                    diabetes=safe_int(row.get('DIABETES')),
                    hematolog=safe_int(row.get('HEMATOLOG')),
                    hepatopat=safe_int(row.get('HEPATOPAT')),
                    renal=safe_int(row.get('RENAL')),
                    hipertensa=safe_int(row.get('HIPERTENSA')),
                    
                    # Evolução
                    hospitaliz=safe_int(row.get('HOSPITALIZ')),
                    evolucao=safe_int(row.get('EVOLUCAO')),
                    classi_fin=safe_int(row.get('CLASSI_FIN')),
                    criterio=safe_int(row.get('CRITERIO'))
                )
                
                cases_to_insert.append(case)
                
            except Exception as e:
                print(f"Erro ao processar linha: {e}")
                continue
        
        # Inserir no banco
        if cases_to_insert:
            try:
                db.session.add_all(cases_to_insert)
                db.session.commit()
                print(f"✅ {disease_name}: {len(cases_to_insert)} registros inseridos com sucesso")
                return len(cases_to_insert)
            except Exception as e:
                print(f"❌ Erro ao inserir dados: {e}")
                db.session.rollback()
                return 0
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro ao processar {csv_path}: {e}")
        return 0

def create_admin_user():
    """Criar usuário administrador padrão"""
    try:
        # Verificar se já existe um admin
        admin = User.query.filter_by(email='admin@saude.gov.br').first()
        if admin:
            print("Usuário admin já existe")
            return
        
        # Criar admin
        admin = User(
            first_name='Administrador',
            last_name='Sistema',
            email='admin@saude.gov.br',
            role='admin'
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        
        print("✅ Usuário administrador criado: admin@saude.gov.br / admin123")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")
        db.session.rollback()

def create_guest_user():
    """Criar usuário guest padrão"""
    try:
        # Verificar se já existe um guest
        guest = User.query.filter_by(email='guest@saude.gov.br').first()
        if guest:
            print("Usuário guest já existe")
            return
        
        # Criar guest
        guest = User(
            first_name='Convidado',
            last_name='Sistema',
            email='guest@saude.gov.br',
            role='guest'
        )
        guest.set_password('guest123')
        
        db.session.add(guest)
        db.session.commit()
        
        print("✅ Usuário guest criado: guest@saude.gov.br / guest123")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário guest: {e}")
        db.session.rollback()

def main():
    """Função principal de ingestão"""
    print("🚀 Iniciando ingestão de dados de saúde (amostra)...")
    
    with app.app_context():
        # Criar tabelas
        db.create_all()
        print("✅ Tabelas criadas/verificadas")
        
        # Criar usuários padrão
        create_admin_user()
        create_guest_user()
        
        # Definir arquivos CSV com amostras menores
        csv_files = [
            ('/home/ubuntu/upload/DENGBR25.csv', 'A90', 'Dengue', 500),
            ('/home/ubuntu/upload/CHIKBR25.csv', 'A920', 'Chikungunya', 200),
            ('/home/ubuntu/upload/COQUBR25.csv', 'A379', 'Coqueluche', 100),
            ('/home/ubuntu/upload/ROTABR25.csv', 'A080', 'Rotavírus', 50),
            ('/home/ubuntu/upload/ZIKABR25.csv', 'A928', 'Zika', 150)
        ]
        
        total_records = 0
        
        # Processar cada arquivo
        for csv_path, disease_code, disease_name, sample_size in csv_files:
            if os.path.exists(csv_path):
                records = ingest_csv_sample(csv_path, disease_code, disease_name, sample_size)
                total_records += records
            else:
                print(f"⚠️  Arquivo não encontrado: {csv_path}")
        
        print(f"\n🎉 Ingestão concluída!")
        print(f"📊 Total de registros inseridos: {total_records}")
        
        # Estatísticas finais
        total_cases = HealthCase.query.count()
        diseases_count = db.session.query(HealthCase.disease_name, 
                                        db.func.count(HealthCase.id)).group_by(HealthCase.disease_name).all()
        
        print(f"\n📈 Estatísticas do banco:")
        print(f"Total de casos: {total_cases}")
        for disease, count in diseases_count:
            print(f"  - {disease}: {count} casos")

if __name__ == '__main__':
    main()

