from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://root:123456@172.22.1.2/dashboard_saude")
engine.connect()
print("Conectou")