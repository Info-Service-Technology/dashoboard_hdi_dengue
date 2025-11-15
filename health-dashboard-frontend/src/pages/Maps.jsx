import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const Maps = () => {
  const [healthData, setHealthData] = useState([]);
  const [selectedDisease, setSelectedDisease] = useState('all');
  const [loading, setLoading] = useState(true);

  // Coordenadas dos estados brasileiros (capitais)
  const stateCoordinates = {
    'AC': [-9.9754, -67.8249], // Acre - Rio Branco
    'AL': [-9.6658, -35.7353], // Alagoas - Maceió
    'AP': [0.0389, -51.0664], // Amapá - Macapá
    'AM': [-3.1190, -60.0217], // Amazonas - Manaus
    'BA': [-12.9714, -38.5014], // Bahia - Salvador
    'CE': [-3.7319, -38.5267], // Ceará - Fortaleza
    'DF': [-15.8267, -47.9218], // Distrito Federal - Brasília
    'ES': [-20.3155, -40.3128], // Espírito Santo - Vitória
    'GO': [-16.6869, -49.2648], // Goiás - Goiânia
    'MA': [-2.5387, -44.2825], // Maranhão - São Luís
    'MT': [-15.6014, -56.0979], // Mato Grosso - Cuiabá
    'MS': [-20.4697, -54.6201], // Mato Grosso do Sul - Campo Grande
    'MG': [-19.8157, -43.9542], // Minas Gerais - Belo Horizonte
    'PA': [-1.4558, -48.5044], // Pará - Belém
    'PB': [-7.1195, -34.8450], // Paraíba - João Pessoa
    'PR': [-25.4284, -49.2733], // Paraná - Curitiba
    'PE': [-8.0476, -34.8770], // Pernambuco - Recife
    'PI': [-5.0892, -42.8019], // Piauí - Teresina
    'RJ': [-22.9068, -43.1729], // Rio de Janeiro - Rio de Janeiro
    'RN': [-5.7945, -35.2110], // Rio Grande do Norte - Natal
    'RS': [-30.0346, -51.2177], // Rio Grande do Sul - Porto Alegre
    'RO': [-8.7612, -63.9039], // Rondônia - Porto Velho
    'RR': [2.8235, -60.6758], // Roraima - Boa Vista
    'SC': [-27.5954, -48.5480], // Santa Catarina - Florianópolis
    'SP': [-23.5505, -46.6333], // São Paulo - São Paulo
    'SE': [-10.9472, -37.0731], // Sergipe - Aracaju
    'TO': [-10.1753, -48.2982], // Tocantins - Palmas
  };

  useEffect(() => {
    fetchHealthData();
  }, []);

  const fetchHealthData = async () => {
    try {
      setLoading(true);
      // Simular dados de saúde por estado
      const mockData = [
        { state: 'SP', disease: 'Dengue', cases: 450, lat: -23.5505, lng: -46.6333 },
        { state: 'RJ', disease: 'Dengue', cases: 320, lat: -22.9068, lng: -43.1729 },
        { state: 'MG', disease: 'Dengue', cases: 280, lat: -19.8157, lng: -43.9542 },
        { state: 'BA', disease: 'Chikungunya', cases: 150, lat: -12.9714, lng: -38.5014 },
        { state: 'PE', disease: 'Zika', cases: 120, lat: -8.0476, lng: -34.8770 },
        { state: 'CE', disease: 'Dengue', cases: 200, lat: -3.7319, lng: -38.5267 },
        { state: 'PR', disease: 'Coqueluche', cases: 80, lat: -25.4284, lng: -49.2733 },
        { state: 'RS', disease: 'Rotavirus', cases: 90, lat: -30.0346, lng: -51.2177 },
      ];
      setHealthData(mockData);
    } catch (error) {
      console.error('Erro ao buscar dados de saúde:', error);
    } finally {
      setLoading(false);
    }
  };

  const getMarkerColor = (disease) => {
    const colors = {
      'Dengue': '#ff4444',
      'Chikungunya': '#ff8800',
      'Zika': '#4444ff',
      'Coqueluche': '#8844ff',
      'Rotavirus': '#44ff44',
    };
    return colors[disease] || '#666666';
  };

  const getMarkerSize = (cases) => {
    if (cases > 400) return 25;
    if (cases > 200) return 20;
    if (cases > 100) return 15;
    return 10;
  };

  const filteredData = selectedDisease === 'all' 
    ? healthData 
    : healthData.filter(item => item.disease === selectedDisease);

  const diseases = [...new Set(healthData.map(item => item.disease))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Carregando dados do mapa...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Mapas de Saúde</h1>
        <div className="flex items-center space-x-4">
          <label htmlFor="disease-filter" className="text-sm font-medium text-gray-700">
            Filtrar por doença:
          </label>
          <select
            id="disease-filter"
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todas as doenças</option>
            {diseases.map(disease => (
              <option key={disease} value={disease}>{disease}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Distribuição Geográfica dos Casos</h2>
        
        <div className="h-96 rounded-lg overflow-hidden border">
          <MapContainer
            center={[-14.2350, -51.9253]} // Centro do Brasil
            zoom={4}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            
            {filteredData.map((item, index) => (
              <CircleMarker
                key={index}
                center={[item.lat, item.lng]}
                radius={getMarkerSize(item.cases)}
                fillColor={getMarkerColor(item.disease)}
                color={getMarkerColor(item.disease)}
                weight={2}
                opacity={0.8}
                fillOpacity={0.6}
              >
                <Popup>
                  <div className="text-center">
                    <h3 className="font-semibold">{item.state}</h3>
                    <p className="text-sm text-gray-600">{item.disease}</p>
                    <p className="text-lg font-bold text-blue-600">{item.cases} casos</p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <div className="mt-4 flex flex-wrap gap-4">
          <div className="text-sm text-gray-600">
            <strong>Legenda:</strong>
          </div>
          {diseases.map(disease => (
            <div key={disease} className="flex items-center space-x-2">
              <div 
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: getMarkerColor(disease) }}
              ></div>
              <span className="text-sm text-gray-700">{disease}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredData.map((item, index) => (
          <div key={index} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold">{item.state}</h3>
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getMarkerColor(item.disease) }}
              ></div>
            </div>
            <p className="text-gray-600 mb-1">{item.disease}</p>
            <p className="text-2xl font-bold text-blue-600">{item.cases} casos</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Maps;

