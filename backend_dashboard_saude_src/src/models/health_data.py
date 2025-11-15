from src.models.user import db
from datetime import datetime

class HealthCase(db.Model):
    """Modelo unificado para casos de saúde de todas as doenças"""
    __tablename__ = 'health_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação do caso
    tp_not = db.Column(db.String(10))  # Tipo de notificação
    id_agravo = db.Column(db.String(10), nullable=False)  # Código do agravo (A90, A92.0, A379, A080, A928)
    disease_name = db.Column(db.String(50), nullable=False)  # Nome da doença
    
    # Datas
    dt_notific = db.Column(db.Date)  # Data de notificação
    dt_sin_pri = db.Column(db.Date)  # Data início dos sintomas
    dt_invest = db.Column(db.Date)   # Data de investigação
    dt_obito = db.Column(db.Date)    # Data do óbito
    dt_encerra = db.Column(db.Date)  # Data de encerramento
    dt_interna = db.Column(db.Date)  # Data de internação
    
    # Demografia
    ano_nasc = db.Column(db.Integer)  # Ano de nascimento
    nu_idade_n = db.Column(db.Integer)  # Idade
    cs_sexo = db.Column(db.String(1))  # Sexo (M/F)
    cs_gestant = db.Column(db.Integer)  # Gestante
    cs_raca = db.Column(db.Integer)    # Raça/cor
    cs_escol_n = db.Column(db.Integer) # Escolaridade
    
    # Localização
    sg_uf_not = db.Column(db.String(2))  # UF de notificação
    id_municip = db.Column(db.String(10)) # Município
    id_regiona = db.Column(db.String(10)) # Região
    id_unidade = db.Column(db.String(20)) # Unidade de saúde
    
    # Sintomas (1=Sim, 2=Não, 9=Ignorado)
    febre = db.Column(db.Integer)
    mialgia = db.Column(db.Integer)
    cefaleia = db.Column(db.Integer)
    exantema = db.Column(db.Integer)
    vomito = db.Column(db.Integer)
    nausea = db.Column(db.Integer)
    dor_costas = db.Column(db.Integer)
    conjuntvit = db.Column(db.Integer)
    artrite = db.Column(db.Integer)
    artralgia = db.Column(db.Integer)
    diarreia = db.Column(db.Integer)  # Para rotavírus
    
    # Comorbidades (1=Sim, 2=Não, 9=Ignorado)
    diabetes = db.Column(db.Integer)
    hematolog = db.Column(db.Integer)
    hepatopat = db.Column(db.Integer)
    renal = db.Column(db.Integer)
    hipertensa = db.Column(db.Integer)
    
    # Evolução e desfecho
    hospitaliz = db.Column(db.Integer)  # Hospitalização (1=Sim, 2=Não)
    evolucao = db.Column(db.Integer)    # Evolução (1=Cura, 2=Óbito, etc.)
    classi_fin = db.Column(db.Integer)  # Classificação final
    criterio = db.Column(db.Integer)    # Critério de confirmação
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<HealthCase {self.id} - {self.disease_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'disease_name': self.disease_name,
            'id_agravo': self.id_agravo,
            'dt_notific': self.dt_notific.isoformat() if self.dt_notific else None,
            'dt_sin_pri': self.dt_sin_pri.isoformat() if self.dt_sin_pri else None,
            'ano_nasc': self.ano_nasc,
            'nu_idade_n': self.nu_idade_n,
            'cs_sexo': self.cs_sexo,
            'cs_gestant': self.cs_gestant,
            'cs_raca': self.cs_raca,
            'sg_uf_not': self.sg_uf_not,
            'id_municip': self.id_municip,
            'febre': self.febre,
            'mialgia': self.mialgia,
            'cefaleia': self.cefaleia,
            'exantema': self.exantema,
            'vomito': self.vomito,
            'nausea': self.nausea,
            'diabetes': self.diabetes,
            'hipertensa': self.hipertensa,
            'hospitaliz': self.hospitaliz,
            'evolucao': self.evolucao,
            'dt_obito': self.dt_obito.isoformat() if self.dt_obito else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Municipality(db.Model):
    """Modelo para municípios brasileiros"""
    __tablename__ = 'municipalities'
    
    id = db.Column(db.String(10), primary_key=True)  # Código IBGE
    name = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    region = db.Column(db.String(20))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    population = db.Column(db.Integer)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'uf': self.uf,
            'region': self.region,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'population': self.population
        }

class HealthUnit(db.Model):
    """Modelo para unidades de saúde"""
    __tablename__ = 'health_units'
    
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(200))
    type = db.Column(db.String(50))  # UBS, Hospital, etc.
    municipality_id = db.Column(db.String(10), db.ForeignKey('municipalities.id'))
    uf = db.Column(db.String(2))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'municipality_id': self.municipality_id,
            'uf': self.uf
        }

