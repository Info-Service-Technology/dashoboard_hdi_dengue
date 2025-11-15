import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, AlertTriangle, Calendar, Target, Activity, Brain } from 'lucide-react';

const Predictions = () => {
  const [forecastData, setForecastData] = useState(null);
  const [riskAnalysis, setRiskAnalysis] = useState(null);
  const [selectedDisease, setSelectedDisease] = useState('Dengue');
  const [selectedState, setSelectedState] = useState('SP');
  const [loading, setLoading] = useState(false);
  const [monthsAhead, setMonthsAhead] = useState(6);

  const diseases = ['Dengue', 'Chikungunya', 'Zika', 'Coqueluche', 'Rotavirus'];
  const states = ['SP', 'RJ', 'MG', 'BA', 'PE', 'CE', 'PR', 'RS'];

  useEffect(() => {
    fetchForecast();
    fetchRiskAnalysis();
  }, [selectedDisease, selectedState, monthsAhead]);

  const fetchForecast = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/predictions/forecast', {
        disease: selectedDisease,
        months_ahead: monthsAhead
      });
      setForecastData(response.data);
    } catch (error) {
      console.error('Erro ao buscar previsões:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRiskAnalysis = async () => {
    try {
      const response = await axios.post('/api/predictions/risk-analysis', {
        state: selectedState
      });
      setRiskAnalysis(response.data);
    } catch (error) {
      console.error('Erro ao buscar análise de risco:', error);
    }
  };

  const getRiskColor = (level) => {
    const colors = {
      'Baixo': '#10b981',
      'Médio': '#f59e0b',
      'Alto': '#ef4444',
      'Muito Alto': '#dc2626'
    };
    return colors[level] || '#6b7280';
  };

  const formatChartData = () => {
    if (!forecastData) return [];
    
    const historical = forecastData.historical_data.slice(-12).map(item => ({
      date: item.date,
      casos_reais: item.cases,
      tipo: 'Histórico'
    }));

    const forecast = forecastData.forecast.map((item, index) => ({
      date: item.date,
      casos_previstos: item.predicted_cases,
      limite_inferior: forecastData.confidence_interval[index].lower_bound,
      limite_superior: forecastData.confidence_interval[index].upper_bound,
      tipo: 'Previsão'
    }));

    return [...historical, ...forecast];
  };

  const riskFactorsData = riskAnalysis ? [
    { name: 'Temperatura', value: riskAnalysis.risk_factors.temperature, max: 35, unit: '°C' },
    { name: 'Umidade', value: riskAnalysis.risk_factors.humidity, max: 100, unit: '%' },
    { name: 'Densidade Pop.', value: riskAnalysis.risk_factors.population_density, max: 1000, unit: '/km²' },
    { name: 'Saneamento', value: riskAnalysis.risk_factors.sanitation_index * 100, max: 100, unit: '%' },
    { name: 'Casos Anteriores', value: riskAnalysis.risk_factors.previous_cases, max: 500, unit: 'casos' }
  ] : [];

  if (loading && !forecastData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-lg">Carregando análises preditivas...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center">
          <Brain className="mr-3 h-8 w-8 text-blue-600" />
          Análise Preditiva
        </h1>
        <div className="flex items-center space-x-4">
          <select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {diseases.map(disease => (
              <option key={disease} value={disease}>{disease}</option>
            ))}
          </select>
          <select
            value={monthsAhead}
            onChange={(e) => setMonthsAhead(parseInt(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={12}>12 meses</option>
          </select>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Próximo Mês</p>
              <p className="text-2xl font-bold text-blue-600">
                {forecastData?.forecast[0]?.predicted_cases || 0}
              </p>
              <p className="text-xs text-gray-500">casos previstos</p>
            </div>
            <TrendingUp className="h-8 w-8 text-blue-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Tendência</p>
              <p className="text-2xl font-bold text-green-600">Estável</p>
              <p className="text-xs text-gray-500">próximos meses</p>
            </div>
            <Activity className="h-8 w-8 text-green-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Nível de Risco</p>
              <p 
                className="text-2xl font-bold"
                style={{ color: getRiskColor(riskAnalysis?.risk_level) }}
              >
                {riskAnalysis?.risk_level || 'Carregando...'}
              </p>
              <p className="text-xs text-gray-500">{selectedState}</p>
            </div>
            <AlertTriangle 
              className="h-8 w-8"
              style={{ color: getRiskColor(riskAnalysis?.risk_level) }}
            />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Confiança</p>
              <p className="text-2xl font-bold text-purple-600">85%</p>
              <p className="text-xs text-gray-500">do modelo</p>
            </div>
            <Target className="h-8 w-8 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Gráfico de Previsão */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Calendar className="mr-2 h-5 w-5" />
          Previsão de Casos - {selectedDisease}
        </h2>
        
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formatChartData()}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="casos_reais" 
                stroke="#3b82f6" 
                strokeWidth={2}
                name="Casos Reais"
              />
              <Line 
                type="monotone" 
                dataKey="casos_previstos" 
                stroke="#ef4444" 
                strokeWidth={2}
                strokeDasharray="5 5"
                name="Casos Previstos"
              />
              <Line 
                type="monotone" 
                dataKey="limite_superior" 
                stroke="#f59e0b" 
                strokeWidth={1}
                strokeDasharray="2 2"
                name="Limite Superior"
              />
              <Line 
                type="monotone" 
                dataKey="limite_inferior" 
                stroke="#10b981" 
                strokeWidth={1}
                strokeDasharray="2 2"
                name="Limite Inferior"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Análise de Risco */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Análise de Risco - {selectedState}</h2>
          
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Nível de Risco Geral</span>
              <span 
                className="px-3 py-1 rounded-full text-sm font-medium text-white"
                style={{ backgroundColor: getRiskColor(riskAnalysis?.risk_level) }}
              >
                {riskAnalysis?.risk_level}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="h-2 rounded-full"
                style={{ 
                  width: `${(riskAnalysis?.risk_score || 0) * 100}%`,
                  backgroundColor: getRiskColor(riskAnalysis?.risk_level)
                }}
              ></div>
            </div>
          </div>

          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-700">Estado:</label>
            <select
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {states.map(state => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>

          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Fatores de Risco:</h3>
            <div className="space-y-2">
              {riskFactorsData.map((factor, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{factor.name}</span>
                  <span className="text-sm font-medium">
                    {factor.value.toFixed(1)} {factor.unit}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recomendações */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Recomendações</h2>
          
          {riskAnalysis?.recommendations && (
            <div className="space-y-3">
              {riskAnalysis.recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-xs font-medium text-blue-600">{index + 1}</span>
                  </div>
                  <p className="text-sm text-gray-700">{recommendation}</p>
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
              <h3 className="text-sm font-medium text-yellow-800">Atenção</h3>
            </div>
            <p className="mt-1 text-sm text-yellow-700">
              As previsões são baseadas em modelos estatísticos e devem ser interpretadas 
              junto com outros indicadores epidemiológicos.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Predictions;

