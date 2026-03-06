import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useAuth } from "../contexts/AuthContext";
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

const api = axios.create({
  baseURL: "http://localhost:5000/api/predictions",
  timeout: 20000,
});

api.interceptors.request.use((config) => {
  const token =
    localStorage.getItem("token") || localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

const Predictions = () => {
  const { tenant } = useAuth();

  const tenantScopeType = String(tenant?.scope_type || "BR").toUpperCase();
  const isPrefeitura = tenantScopeType === "MUN";

  const [historical, setHistorical] = useState([]);
  const [forecast, setForecast] = useState([]);
  const [error, setError] = useState(null);

  const [diseases, setDiseases] = useState([]);
  const [disease, setDisease] = useState("");

  const normalizeError = (e, fallback) =>
    e?.response?.data?.msg ||
    e?.response?.data?.message ||
    e?.response?.data?.error ||
    e?.message ||
    fallback;

  const chartData = useMemo(() => {
    const hist = (historical || []).map((h) => ({
      bucket: h.bucket,
      real: Number(h.cases || 0),
      predicted: null,
    }));

    const pred = (forecast || []).map((f) => ({
      bucket: f.bucket,
      real: null,
      predicted: Number(f.cases_pred || 0),
    }));

    if (hist.length && pred.length) {
      pred.unshift({
        bucket: hist[hist.length - 1].bucket,
        real: null,
        predicted: hist[hist.length - 1].real,
      });
    }

    return [...hist, ...pred];
  }, [historical, forecast]);

  useEffect(() => {
    loadCatalogs();
  }, []);

  useEffect(() => {
    if (disease) {
      loadHistorical();
      loadForecast();
    }
  }, [disease]);

  const loadCatalogs = async () => {
    try {
      setError(null);

      const dRes = await api.get("/diseases");

      const dList = Array.isArray(dRes.data)
        ? dRes.data
        : Array.isArray(dRes.data?.diseases)
          ? dRes.data.diseases
          : [];

      setDiseases(dList);
      setDisease((prev) => prev || (dList.length ? dList[0] : ""));
    } catch (e) {
      setError(normalizeError(e, "Erro ao carregar doenças"));
    }
  };

  const loadHistorical = async () => {
    try {
      setError(null);
      setHistorical([]);

      // histórico ainda não vem separado do backend atual
      setHistorical([]);
    } catch (e) {
      setHistorical([]);
      setError(normalizeError(e, "Erro ao carregar histórico"));
    }
  };

  const loadForecast = async () => {
    try {
      setError(null);
      setForecast([]);

      const res = await api.get("/trends", {
        params: {
          disease: disease || "all",
          gran: "month",
          horizon: 6,
        },
      });

      setForecast(Array.isArray(res.data) ? res.data : []);
    } catch (e) {
      setForecast([]);
      setError(normalizeError(e, "Erro ao carregar forecast"));
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">
          {isPrefeitura ? "Análise Preditiva do Município" : "Análise Preditiva"}
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          {isPrefeitura
            ? "Previsão epidemiológica no escopo do tenant prefeitura."
            : "Previsões epidemiológicas por série temporal."}
        </p>
      </div>

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

        {isPrefeitura && (
          <div className="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700">
            Escopo municipal aplicado automaticamente
          </div>
        )}
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
            <XAxis dataKey="bucket" />
            <YAxis />
            <Tooltip />
            <Legend />

            <Line
              dataKey="real"
              stroke="#2563eb"
              name="Casos Reais"
              dot={false}
              connectNulls
            />

            <Line
              dataKey="predicted"
              stroke="#dc2626"
              name="Previstos"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="text-xs text-gray-500">
        {isPrefeitura
          ? "Tenant prefeitura: previsão baseada no município do escopo JWT."
          : "Tenant Brasil: previsão baseada na série temporal nacional/filtrada."}
      </div>
    </div>
  );
};

export default Predictions;