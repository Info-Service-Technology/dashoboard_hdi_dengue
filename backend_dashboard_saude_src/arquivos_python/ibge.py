import requests
import pandas as pd

print("📍 Baixando municípios do IBGE...")

response = requests.get('https://servicodados.ibge.gov.br/api/v1/localidades/municipios')
municipios = response.json()

print(f"✅ {len(municipios)} municípios encontrados!")

data = []
for i, mun in enumerate(municipios):
    try:
        # Pegar UF e região de forma SEGURA
        uf = regiao = None
        if mun.get('microrregiao') and mun['microrregiao'].get('mesorregiao'):
            uf_obj = mun['microrregiao']['mesorregiao'].get('UF')
            if uf_obj:
                uf = uf_obj.get('sigla')
                regiao = uf_obj.get('regiao', {}).get('nome')
        
        # Se não achou, usa nome do estado do município
        if not uf:
            nome_uf = mun.get('nome').split()[-1].upper()[:2] if mun.get('nome') else 'SP'
            if nome_uf in ['SP','RJ','MG','RS','PR','BA','GO','SC','PE','CE','PA','PB','ES','MA','PI','MT','MS','RO','AC','AP','TO','RR','AL','SE','DF']:
                uf = nome_uf
        
        data.append({
            'id': str(mun['id']),
            'name': mun['nome'],
            'uf': uf or 'SP',
            'region': regiao or 'Sudeste',
            'latitude': None,
            'longitude': None,
            'population': None
        })
        
        if i % 1000 == 0:
            print(f"Processados {i}/{len(municipios)}...")
            
    except Exception as e:
        print(f"Erro no município {i}: {e}")
        continue

df = pd.DataFrame(data)
df.to_csv('municipalities.csv', index=False)
print(f"✅ municipalities.csv criado com {len(df)} municípios!")
print(df.head())
