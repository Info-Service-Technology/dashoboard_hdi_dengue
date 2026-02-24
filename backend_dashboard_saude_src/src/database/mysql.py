import mysql.connector
import pandas as pd
import os

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "172.22.1.2"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database=os.getenv("MYSQL_DATABASE", "dashboard_saude")
    )

def query_df(sql, params=None):
    conn = get_connection()
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    return df