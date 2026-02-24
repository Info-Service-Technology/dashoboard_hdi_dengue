import pandas as pd
import requests

# Ler CSV atual
df = pd.read_csv('municipalities.csv')

print(f"📍 Completando {len(df)} municípios...")

# API para coordenadas (exemplo com Nominatim)
def get_coords(city, state):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city}+{state}+Brasil&format=json&limit=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=2)
        if resp.json():
            data = resp.json()[0]
            return float(data['lat']), float(data['lon'])
    except:
        pass
    return None, None

# Completar população por UF (estimativa 2025)
pop_uf = {
    'SP': 46000000, 'MG': 21000000, 'RJ': 17000000, 'RS': 11500000, 
    'PR': 11500000, 'BA': 15000000, 'GO': 7200000, 'SC': 7400000,
    'PE': 9600000, 'CE': 9200000, 'PA': 9100000, 'PB': 4100000,
    'ES': 4100000, 'MA': 7200000, 'PI': 3400000, 'MT': 3600000,
    'MS': 2900000, 'RO': 2400000, 'TO': 1700000, 'AC': 950000,
    'AP': 950000, 'RR': 700000, 'AL': 3400000, 'SE': 2400000, 'DF': 3200000
}

# Processar em lotes (só primeiras 100 cidades como exemplo)
for i, row in df.head(100).iterrows():
    if pd.isna(df.loc[i, 'latitude']):
        lat, lon = get_coords(row['name'], row['uf'])
        df.loc[i, 'latitude'] = lat
        df.loc[i, 'longitude'] = lon
        print(f"✅ {row['name']}: {lat}, {lon}")
    
    # População estimada
    df.loc[i, 'population'] = int(pop_uf.get(row['uf'], 100000) / 100)  # Média por município

df.to_csv('municipalities_completo.csv', index=False)
print("✅ municipalities_completo.csv criado!")
