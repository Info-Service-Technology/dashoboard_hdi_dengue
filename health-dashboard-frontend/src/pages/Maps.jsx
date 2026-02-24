import { useAuth } from '../contexts/AuthContext';
import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, CircleMarker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const Maps = () => {
  const { token } = useAuth();
  const [healthData, setHealthData] = useState([]);
  const [selectedDisease, setSelectedDisease] = useState('all');
  const [loading, setLoading] = useState(true);

  // ✅ Só busca quando o token existir (evita "Missing Authorization Header")
  useEffect(() => {
    if (token) {
      fetchHealthData();
    } else {
      // se ainda não tem token, não tenta carregar e não quebra o layout
      setLoading(false);
      setHealthData([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // ✅ Única função fetchHealthData (robusta)
  const fetchHealthData = async () => {
    try {
      setLoading(true);

      if (!token) {
        setHealthData([]);
        return;
      }

      const response = await fetch('http://localhost:5000/api/maps', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      // 401 acontece quando token expira ou não foi enviado
      if (response.status === 401) {
        console.error('❌ 401 (JWT): Missing/Invalid Authorization Header');
        setHealthData([]);
        return;
      }

      if (!response.ok) {
        console.error('Erro API:', response.status);
        setHealthData([]);
        return;
      }

      const data = await response.json();

      // ✅ evita "healthData.map is not a function"
      setHealthData(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Erro ao buscar mapa:', error);
      setHealthData([]);
    } finally {
      setLoading(false);
    }
  };

  const getMarkerColor = (disease) => {
    const colors = {
      Dengue: '#ef4444', // Vermelho
      Chikungunya: '#f97316', // Laranja
      Zika: '#3b82f6', // Azul
      Coqueluche: '#a855f7', // Roxo
      Rotavírus: '#22c55e', // Verde
    };
    return colors[disease] || '#64748b';
  };

  const getMarkerSize = (cases) => {
    if (cases > 500) return 35;
    if (cases > 100) return 25;
    if (cases > 50) return 15;
    return 10;
  };

  const safeHealthData = Array.isArray(healthData) ? healthData : [];

  const filteredData =
    selectedDisease === 'all'
      ? safeHealthData
      : safeHealthData.filter((item) => item.disease === selectedDisease);

  const diseases = [...new Set(safeHealthData.map((item) => item.disease))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-lg">Carregando mapa epidemiológico...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* HEADER E FILTRO */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900">Análise Geográfica</h1>
        <div className="flex items-center space-x-3 bg-white p-2 rounded-lg shadow-sm border">
          <label htmlFor="disease-filter" className="text-sm font-semibold text-gray-600">
            Filtrar:
          </label>
          <select
            id="disease-filter"
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="bg-transparent focus:outline-none text-blue-600 font-bold"
          >
            <option value="all">Todos as doenças</option>
            {diseases.map((disease) => (
              <option key={disease} value={disease}>
                {disease}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* MAPA */}
      <div className="bg-white rounded-xl shadow-xl p-4 border border-gray-100">
        <div className="h-[600px] rounded-lg overflow-hidden relative z-0">
          <MapContainer center={[-14.2350, -51.9253]} zoom={4} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
            />

            {filteredData.map((item, index) => (
              <React.Fragment key={index}>
                {/* PIN INTERATIVO */}
                <Marker position={[item.lat, item.lng]}>
                  <Popup>
                    <div className="min-w-[150px]">
                      <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Município</div>
                      <div className="text-lg font-bold text-gray-900 leading-tight mb-2">
                        {item.city} - {item.state}
                      </div>
                      <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
                        <span className="text-sm text-gray-600">{item.disease}</span>
                        <span className="text-md font-black text-red-600">{item.cases}</span>
                      </div>
                    </div>
                  </Popup>
                </Marker>

                {/* AURA DE INTENSIDADE (Visual apenas) */}
                <CircleMarker
                  center={[item.lat, item.lng]}
                  radius={getMarkerSize(item.cases)}
                  fillColor={getMarkerColor(item.disease)}
                  color={getMarkerColor(item.disease)}
                  weight={1}
                  opacity={0.3}
                  fillOpacity={0.2}
                  interactive={false}
                />
              </React.Fragment>
            ))}
          </MapContainer>
        </div>

        {/* LEGENDA DINÂMICA */}
        <div className="mt-4 flex flex-wrap gap-6 p-4 bg-gray-50 rounded-lg">
          {diseases.map((disease) => (
            <div key={disease} className="flex items-center space-x-2">
              <div className="w-4 h-4 rounded-full shadow-sm" style={{ backgroundColor: getMarkerColor(disease) }}></div>
              <span className="text-sm font-medium text-gray-700">{disease}</span>
            </div>
          ))}
        </div>
      </div>

      {/* LISTAGEM RESUMO */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {filteredData.slice(0, 8).map((item, index) => (
          <div
            key={index}
            className="bg-white border-l-4 rounded-lg shadow-sm p-4"
            style={{ borderColor: getMarkerColor(item.disease) }}
          >
            <div className="text-xs font-bold text-gray-400">
              {item.city} ({item.state})
            </div>
            <div className="text-xl font-bold text-gray-800">{item.cases} casos</div>
            <div className="text-sm text-gray-500">{item.disease}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Maps;