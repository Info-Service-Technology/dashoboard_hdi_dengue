import pandas as pd
import mysql.connector

# CSV com coordenadas
df = pd.read_csv("municipios_coordenadas.csv")

conn = mysql.connector.connect(
    host="172.22.1.2",
    user="root",
    password="123456",
    database="dashboard_saude"
)

cursor = conn.cursor()

for _, row in df.iterrows():
    sql = """
    UPDATE municipalities
    SET latitude = %s, longitude = %s
    WHERE id = %s
    """
    cursor.execute(sql, (row["latitude"], row["longitude"], int(row["codigo_ibge"])))

conn.commit()
cursor.close()
conn.close()

print("✅ Coordenadas atualizadas!")