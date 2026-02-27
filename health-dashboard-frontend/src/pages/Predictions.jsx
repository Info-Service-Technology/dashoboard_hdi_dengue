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
  ResponsiveContainer,
} from "recharts";

// ✅ axios local (não afeta o resto do app)
const api = axios.create({
  baseURL: "http://localhost:5000/api/predictions",
  timeout: 20000,
});

// ✅ injeta token automaticamente em toda request desse módulo
api.interceptors.request.use((config) => {
  const token =
    localStorage.getItem("token") || localStorage.getItem("access_token");
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

  const normalizeError = (e, fallback) =>
    e?.response?.data?.msg ||
    e?.response?.data?.message ||
    e?.response?.data?.error ||
    e?.message ||
    fallback;

  // ✅ evita recriar array toda render
  const chartData = useMemo(() => {
    if (!forecast) return [];

    const hist = (forecast.historical_data || []).map((h) => ({
      date: h.date,
      real: Number(h.cases || 0),
    }));

    const pred = (forecast.forecast || []).map((f, i) => ({
      date: f.date,
      predicted: Number(f.predicted_cases || 0),
      low: Number(forecast.confidence_interval?.[i]?.lower_bound ?? null),
      high: Number(forecast.confidence_interval?.[i]?.upper_bound ?? null),
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

  const loadCatalogs = async () => {
    try {
      setError(null);

      const [dRes, sRes] = await Promise.all([
        api.get("/diseases"),
        api.get("/states"),
      ]);

      const dList = Array.isArray(dRes.data?.diseases) ? dRes.data.diseases : [];
      const sList = Array.isArray(sRes.data?.states) ? sRes.data.states : [];

      setDiseases(dList);
      setStates(sList);

      // ✅ garante default sem loop
      setDisease((prev) => prev || (dList.length ? dList[0] : ""));
      setState((prev) => prev || (sList.length ? sList[0] : ""));
    } catch (e) {
      setError(normalizeError(e, "Erro ao carregar catálogos"));
    }
  };

  const loadForecast = async () => {
    try {
      setError(null);
      setForecast(null);

      // backend espera: { disease, months_ahead }
      const res = await api.post("/forecast", { disease, months_ahead: 6 });
      setForecast(res.data || null);
    } catch (e) {
      setForecast(null);
      setError(normalizeError(e, "Erro ao carregar forecast"));
    }
  };

  const loadRisk = async () => {
    try {
      setError(null);
      setRisk(null);

      // backend espera: { state }
      const res = await api.post("/risk-analysis", { state });
      setRisk(res.data || null);
    } catch (e) {
      setRisk(null);
      setError(normalizeError(e, "Erro ao carregar risco"));
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Análise Preditiva</h1>

      <div className="flex gap-4">
        <select
          value={disease}
          onChange={(e) => setDisease(e.target.value)}
          className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm"
        >
          {diseases.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>

        <select
          value={state}
          onChange={(e) => setState(e.target.value)}
          className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm"
        >
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

            <Line dataKey="real" stroke="#2563eb" name="Casos Reais" dot={false} />
            <Line dataKey="predicted" stroke="#dc2626" name="Previstos" dot={false} />
            <Line
              dataKey="high"
              stroke="#f59e0b"
              strokeDasharray="4 4"
              name="Limite superior"
              dot={false}
              connectNulls
            />
            <Line
              dataKey="low"
              stroke="#10b981"
              strokeDasharray="4 4"
              name="Limite inferior"
              dot={false}
              connectNulls
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
          <p>Score: {(Number(risk.risk_score || 0) * 100).toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
};

export default Predictions;