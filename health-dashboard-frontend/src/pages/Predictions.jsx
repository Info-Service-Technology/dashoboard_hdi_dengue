import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

// ✅ axios local (não afeta o resto do app)
const api = axios.create({
  baseURL: "http://localhost:5000/api/predictions"
});

// ✅ injeta token automaticamente em toda request desse módulo
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const Predictions = () => {
  const [forecast, setForecast] = useState(null);
  const [risk, setRisk] = useState(null);
  const [error, setError] = useState(null);

  const [diseases, setDiseases] = useState([]);
  const [states, setStates] = useState([]);

  const [disease, setDisease] = useState("");
  const [state, setState] = useState("");

  // ✅ evita recriar array toda render
  const chartData = useMemo(() => {
    if (!forecast) return [];

    const hist = (forecast.historical_data || []).map((h) => ({
      date: h.date,
      real: h.cases
    }));

    const pred = (forecast.forecast || []).map((f, i) => ({
      date: f.date,
      predicted: f.predicted_cases,
      low: forecast.confidence_interval?.[i]?.lower_bound,
      high: forecast.confidence_interval?.[i]?.upper_bound
    }));

    return [...hist, ...pred];
  }, [forecast]);

  useEffect(() => {
    loadCatalogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (disease) loadForecast();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disease]);

  useEffect(() => {
    if (state) loadRisk();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const normalizeError = (e, fallback) =>
    e?.response?.data?.msg ||
    e?.response?.data?.message ||
    e?.response?.data?.error ||
    e?.message ||
    fallback;

  const loadCatalogs = async () => {
    try {
      setError(null);

      const [dRes, sRes] = await Promise.all([
        api.get("/diseases"),
        api.get("/states")
      ]);

      const dList = Array.isArray(dRes.data?.diseases) ? dRes.data.diseases : [];
      const sList = Array.isArray(sRes.data?.states) ? sRes.data.states : [];

      setDiseases(dList);
      setStates(sList);

      // ✅ garante default
      if (!disease && dList.length) setDisease(dList[0]);
      if (!state && sList.length) setState(sList[0]);
    } catch (e) {
      setError(normalizeError(e, "Erro ao carregar catálogos"));
    }
  };

  const loadForecast = async () => {
    try {
      setError(null);
      const res = await api.post("/forecast", { disease, months_ahead: 6 });
      setForecast(res.data);
    } catch (e) {
      setForecast(null);
      setError(normalizeError(e, "Erro ao carregar forecast"));
    }
  };

  const loadRisk = async () => {
    try {
      setError(null);
      const res = await api.post("/risk-analysis", { state });
      setRisk(res.data);
    } catch (e) {
      setRisk(null);
      setError(normalizeError(e, "Erro ao carregar risco"));
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Análise Preditiva</h1>

      <div className="flex gap-4">
        <select value={disease} onChange={(e) => setDisease(e.target.value)}>
          {diseases.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        <select value={state} onChange={(e) => setState(e.target.value)}>
          {states.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <div className="bg-white p-4 rounded shadow">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line dataKey="real" stroke="#2563eb" name="Casos Reais" />
            <Line dataKey="predicted" stroke="#dc2626" name="Previstos" />
            <Line
              dataKey="high"
              stroke="#f59e0b"
              strokeDasharray="4 4"
              name="Limite superior"
            />
            <Line
              dataKey="low"
              stroke="#10b981"
              strokeDasharray="4 4"
              name="Limite inferior"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {risk && (
        <div className="bg-white p-4 rounded shadow">
          <h2 className="font-semibold">Risco {risk.state}</h2>
          <p>
            Nível: <strong>{risk.risk_level}</strong>
          </p>
          <p>Score: {(risk.risk_score * 100).toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
};

export default Predictions;