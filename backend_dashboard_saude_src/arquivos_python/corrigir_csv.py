# fix_acentuacao.py
import pandas as pd


# Ler CSV SEM charset específico (pandas detecta)
df = pd.read_csv('/home/mauroslucios/workspace/dashboard_manus/backend_dashboard_saude_src/arquivos_python/municipalities_completo.csv')

# Forçar UTF-8 nas strings
for col in ['id', 'name', 'uf', 'region']:
    df[col] = df[col].astype(str)

print("Antes:")
print(df[['id', 'name']].head(3))

# Salvar COM UTF-8 explícito
df.to_csv('municipalities_fixed.csv', index=False, encoding='utf-8')

print("✅ municipalities_fixed.csv criado com UTF-8!")
