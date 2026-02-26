// src/pages/Analytics.jsx
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RTooltip,
  CartesianGrid,
  LineChart,
  Line,
  Cell,
} from "recharts";

function fmt(n) {
  const v = Number(n || 0);
  return v.toLocaleString("pt-BR");
}

function fmtDelta(delta) {
  if (delta === null || delta === undefined) return "—";
  const v = Number(delta);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function isoDate(d) {
  const pad = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function KpiCard({ title, value, sub, loading }) {
  return (
    <div className="rounded-2xl border border-gray-200 p-4 bg-white">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="text-2xl font-semibold mt-1 text-gray-900">
        {loading ? "…" : value}
      </div>
      {sub ? <div className="text-xs text-gray-500 mt-1">{sub}</div> : null}
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-3 py-2">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-sm font-semibold text-gray-900">{fmt(p.value)}</div>
    </div>
  );
}

export default function Analytics() {
  const { token } = useAuth();

  const PALETTE = [
    "#2563eb",
    "#16a34a",
    "#f97316",
    "#a855f7",
    "#ef4444",
    "#0ea5e9",
    "#84cc16",
    "#f59e0b",
    "#14b8a6",
    "#64748b",
  ];

  const ufColor = (ufLabel) => {
    let h = 0;
    const s = String(ufLabel || "");
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  };

  // previsão
  const [predTrends, setPredTrends] = useState([]);
  const [loadingPred, setLoadingPred] = useState(false);

  // filtros
  const [disease, setDisease] = useState("all");
  const [uf, setUf] = useState("all");
  const [gran, setGran] = useState("week");
  const [deltaMode, setDeltaMode] = useState("yoy"); // yoy|pop

  // default: 2 anos
  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return isoDate(d);
  });
  const [end, setEnd] = useState(() => isoDate(new Date()));

  // dados
  const [kpi, setKpi] = useState(null);
  const [compare, setCompare] = useState([]);
  const [trends, setTrends] = useState([]);

  // loading
  const [loadingKpi, setLoadingKpi] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [exporting, setExporting] = useState(false);

  // errors
  const [errKpi, setErrKpi] = useState("");
  const [errCompare, setErrCompare] = useState("");
  const [errTrends, setErrTrends] = useState("");

  const apiBase = "http://localhost:5000/api";

  const qs = useMemo(() => {
    const params = new URLSearchParams();
    params.set("disease", disease || "all");
    params.set("uf", uf || "all");
    params.set("start", start);
    params.set("end", end);
    params.set("gran", gran);
    params.set("delta_mode", deltaMode);
    return params.toString();
  }, [disease, uf, start, end, gran, deltaMode]);

  const authHeaders = useMemo(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  const fetchJson = useCallback(
    async (url) => {
      const res = await fetch(url, { headers: authHeaders });
      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : null;
      return { res, body };
    },
    [authHeaders]
  );

  const loadKpi = useCallback(async () => {
    if (!token) return;
    setLoadingKpi(true);
    setErrKpi("");

    try {
      const { res, body } = await fetchJson(`${apiBase}/analytics/kpi?${qs}`);
      if (res.status === 401) {
        setErrKpi("Não autorizado. Faça login novamente.");
        setKpi(null);
        return;
      }
      if (!res.ok) {
        setErrKpi(body?.error || `Erro ao carregar KPI (HTTP ${res.status}).`);
        setKpi(null);
        return;
      }
      setKpi(body);
    } catch (e) {
      console.error(e);
      setErrKpi("Falha ao carregar KPI.");
      setKpi(null);
    } finally {
      setLoadingKpi(false);
    }
  }, [token, fetchJson, apiBase, qs]);

  const loadCompare = useCallback(async () => {
    if (!token) return;
    setLoadingCompare(true);
    setErrCompare("");

    try {
      const { res, body } = await fetchJson(`${apiBase}/analytics/compare?${qs}`);
      if (res.status === 401) {
        setErrCompare("Não autorizado. Faça login novamente.");
        setCompare([]);
        return;
      }
      if (!res.ok) {
        setErrCompare(body?.error || `Erro ao carregar comparativos (HTTP ${res.status}).`);
        setCompare([]);
        return;
      }
      setCompare(Array.isArray(body) ? body : []);
    } catch (e) {
      console.error(e);
      setErrCompare("Falha ao carregar comparativos.");
      setCompare([]);
    } finally {
      setLoadingCompare(false);
    }
  }, [token, fetchJson, apiBase, qs]);

  const loadTrends = useCallback(async () => {
    if (!token) return;
    setLoadingTrends(true);
    setErrTrends("");

    try {
      const { res, body } = await fetchJson(`${apiBase}/analytics/trends?${qs}`);
      if (res.status === 401) {
        setErrTrends("Não autorizado. Faça login novamente.");
        setTrends([]);
        return;
      }
      if (!res.ok) {
        setErrTrends(body?.error || `Erro ao carregar tendências (HTTP ${res.status}).`);
        setTrends([]);
        return;
      }
      setTrends(Array.isArray(body) ? body : []);
    } catch (e) {
      console.error(e);
      setErrTrends("Falha ao carregar tendências.");
      setTrends([]);
    } finally {
      setLoadingTrends(false);
    }
  }, [token, fetchJson, apiBase, qs]);

  const loadPredictions = useCallback(async () => {
    if (!token) return;

    setLoadingPred(true);
    try {
      // qs já tem disease/uf/start/end/gran/delta_mode
      const res = await fetch(`${apiBase}/predictions/trends?${qs}&horizon=12`, {
        headers: authHeaders,
      });

      if (!res.ok) {
        setPredTrends([]);
        return;
      }
      const body = await res.json();
      setPredTrends(Array.isArray(body) ? body : []);
    } catch (e) {
      console.error(e);
      setPredTrends([]);
    } finally {
      setLoadingPred(false);
    }
  }, [token, apiBase, qs, authHeaders]);

  // debounce reload
  useEffect(() => {
    if (!token) return;
    const t = setTimeout(() => {
      loadKpi();
      loadCompare();
      loadTrends();
      loadPredictions();
    }, 250);
    return () => clearTimeout(t);
  }, [token, loadKpi, loadCompare, loadTrends, loadPredictions]);

  const exportCsv = useCallback(async () => {
    if (!token) {
      toast.error("Você precisa estar logado para exportar.");
      return;
    }

    setExporting(true);
    const url = `${apiBase}/analytics/export/csv?${qs}`;

    try {
      const res = await fetch(url, { headers: authHeaders });

      if (!res.ok) {
        let msg = `Falha ao exportar (HTTP ${res.status})`;
        const ct = res.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          const body = await res.json();
          msg = body?.error || msg;
        }
        throw new Error(msg);
      }

      const blob = await res.blob();
      const cd = res.headers.get("content-disposition") || "";
      const match = cd.match(/filename="([^"]+)"/);
      const filename = match?.[1] || "hdi_analytics.csv";

      const href = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => window.URL.revokeObjectURL(href), 1000);

      toast.success("CSV exportado com sucesso.");
    } catch (e) {
      console.error(e);
      toast.error(e?.message || "Erro ao exportar CSV.");
    } finally {
      setExporting(false);
    }
  }, [token, apiBase, qs, authHeaders]);

  // dropdowns (MVP)
  const diseases = ["Dengue", "Chikungunya", "Zika", "Coqueluche", "Rotavírus"];
  const ufs = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
  ];

  const compareTitle =
    uf === "all" ? "Top 10 UFs (casos)" : `Top 10 municípios de ${uf} (casos)`;

  const compareData = useMemo(() => {
    return compare.map((d) => ({
      label: d.label,
      cases: Number(d.cases || 0),
      short:
        String(d.label).length > 10
          ? String(d.label).slice(0, 10) + "…"
          : String(d.label),
    }));
  }, [compare]);

  // junta histórico + previsão, com "ponte" no último ponto histórico
  const trendsData = useMemo(() => {
    const hist = trends.map((p) => ({
      bucket: String(p.bucket),
      cases: Number(p.cases || 0),
      cases_pred: null,
    }));

    const pred = predTrends.map((p) => ({
      bucket: String(p.bucket),
      cases: null,
      cases_pred: Number(p.cases_pred || 0),
    }));

    if (hist.length && pred.length) {
      pred.unshift({
        bucket: hist[hist.length - 1].bucket,
        cases: null,
        cases_pred: hist[hist.length - 1].cases,
      });
    }

    return [...hist, ...pred];
  }, [trends, predTrends]);

  const windowDays = kpi?.delta_base?.window_days;
  const deltaTitle =   deltaMode === "yoy"
    ? `Δ (janela móvel ${windowDays || 0}d) vs ano passado`
    : `Δ (últimos ${windowDays || 0}d) vs período anterior`;

  const baseTotal = kpi?.delta_base?.base_total ?? 0;
  const prevTotal = kpi?.delta_base?.prev_total ?? 0;

  const deltaValue =
    baseTotal === 0
      ? "Sem dados na janela"
      : prevTotal === 0
        ? "Sem base histórica"
        : (kpi?.delta_pct === null || kpi?.delta_pct === undefined)
          ? "—"
          : fmtDelta(kpi.delta_pct);

  const deltaSub = kpi?.delta_base
  ? `Janela: ${fmt(baseTotal)} (${kpi.delta_base.base_start} → ${kpi.delta_base.base_end}) | Base: ${fmt(prevTotal)} (${kpi.delta_base.prev_start} → ${kpi.delta_base.prev_end})`
  : undefined;

  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Análises</h1>
            <p className="text-sm text-gray-500 mt-1">
              Gráficos, estatísticas e indicadores.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl p-3">
            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Doença</label>
              <select
                value={disease}
                onChange={(e) => setDisease(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              >
                <option value="all">Todas</option>
                {diseases.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">UF</label>
              <select
                value={uf}
                onChange={(e) => setUf(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              >
                <option value="all">Todas</option>
                {ufs.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Início</label>
              <input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Fim</label>
              <input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Gran</label>
              <select
                value={gran}
                onChange={(e) => setGran(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              >
                <option value="day">Dia</option>
                <option value="week">Semana</option>
                <option value="month">Mês</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Δ</label>
              <select
                value={deltaMode}
                onChange={(e) => setDeltaMode(e.target.value)}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              >
                <option value="yoy">Ano passado</option>
                <option value="pop">Período anterior</option>
              </select>
            </div>

            <button
              onClick={exportCsv}
              disabled={exporting}
              className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {exporting ? "Exportando…" : "Exportar CSV"}
            </button>

            {(loadingKpi || loadingCompare || loadingTrends || loadingPred) && (
              <span className="text-xs text-gray-500">Atualizando…</span>
            )}
          </div>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <KpiCard
            title="Casos no período"
            value={fmt(kpi?.total_cases)}
            loading={loadingKpi}
          />
          <KpiCard
            title="UFs afetadas"
            value={fmt(kpi?.uf_affected)}
            loading={loadingKpi}
          />
          <KpiCard
            title="Municípios afetados"
            value={fmt(kpi?.cities_affected)}
            loading={loadingKpi}
          />
          <KpiCard
            title={deltaTitle}
            value={deltaValue}
            sub={
              deltaSub ||
              (kpi?.top_uf
                ? `Top UF: ${kpi.top_uf.uf} (${fmt(kpi.top_uf.cases)})`
                : undefined)
            }
            loading={loadingKpi}
          />
        </div>
          {kpi?.executive_summary && (
            <div className="mt-6 rounded-2xl border border-gray-200 p-5 bg-gray-50">
              <div className="text-sm text-gray-500 mb-3">
                🧠 Insight Executivo
              </div>

              {/* Linha principal */}
              <div className="flex flex-wrap items-center gap-6 text-sm">
                <div>
                  <strong>Tendência:</strong>{" "}
                  {kpi.executive_summary.trend}
                </div>

                <div className="flex items-center gap-2">
                  <strong>Risco:</strong>
                  <span>{kpi.executive_summary.badge}</span>
                  <span className="font-semibold">
                    {kpi.executive_summary.risk_level}
                  </span>
                </div>

                <div>
                  <strong>Score:</strong>{" "}
                  <span className="text-lg font-semibold">
                    {kpi.executive_summary.risk_score}
                  </span>
                  <span className="text-gray-500">/100</span>
                </div>
              </div>

              {/* Escopo */}
              <div className="mt-3 text-xs text-gray-500">
                Escopo do score:{" "}
                <span className="font-semibold">
                  {kpi.executive_summary.scope}
                </span>{" "}
                | Período:{" "}
                <span className="font-semibold">
                  {kpi.executive_summary.context?.period_start}
                </span>
                {" → "}
                <span className="font-semibold">
                  {kpi.executive_summary.context?.period_end}
                </span>
              </div>

              {/* Drivers */}
              {uf === "all" && typeof kpi.executive_summary.top_share === "number" && (
                <div className="mt-2 text-xs text-gray-600">
                  UF líder no período analisado:{" "}
                  <strong>{kpi.top_uf?.uf}</strong>{" "}
                  ({kpi.executive_summary.top_share}% dos casos totais)
                </div>
              )}

              {/* Insight textual */}
              <div className="mt-4 text-sm text-gray-700">
                {kpi.executive_summary.alert}
              </div>
              <div className="text-sm text-gray-700">
                {kpi.executive_summary.recommendation}
              </div>
            </div>
          )}

        {errKpi && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-2">
            {errKpi}
          </div>
        )}

        {/* Gráficos */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          {/* Comparativos (Bar) */}
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Comparativos</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">{compareTitle}</div>

            {errCompare && (
              <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-2">
                {errCompare}
              </div>
            )}

            <div className="mt-4 h-[280px]">
              {loadingCompare ? (
                <div className="text-sm text-gray-500">Carregando…</div>
              ) : compareData.length === 0 ? (
                <div className="text-sm text-gray-500">Sem dados.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={compareData} margin={{ top: 10, right: 10, bottom: 40, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="short"
                      interval={0}
                      angle={-25}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tickFormatter={(v) => fmt(v)} width={70} />
                    <RTooltip content={<ChartTooltip />} />
                    <Bar dataKey="cases">
                      {compareData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={uf === "all" ? ufColor(entry.label) : "#2563eb"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="mt-2 text-xs text-gray-500">
              Dica: selecione uma UF para ver os top municípios.
            </div>
          </div>

          {/* Tendências (Line) + Previsão (pontilhada) */}
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Tendências</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">Casos ao longo do tempo</div>

            {errTrends && (
              <div className="mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-2">
                {errTrends}
              </div>
            )}

            <div className="mt-4 h-[280px]">
              {loadingTrends ? (
                <div className="text-sm text-gray-500">Carregando…</div>
              ) : trendsData.length === 0 ? (
                <div className="text-sm text-gray-500">{errTrends ? "—" : "Sem dados."}</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendsData} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bucket" hide />
                    <YAxis tickFormatter={(v) => fmt(v)} width={70} />
                    <RTooltip content={<ChartTooltip />} />

                    {/* histórico */}
                    <Line type="monotone" dataKey="cases" dot={false} stroke="#2563eb" connectNulls />

                    {/* previsão (pontilhada) */}
                    <Line
                      type="monotone"
                      dataKey="cases_pred"
                      dot={false}
                      stroke="#2563eb"
                      strokeDasharray="6 6"
                      connectNulls
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="mt-2 text-xs text-gray-500">
              Granularidade: <span className="font-semibold">{gran}</span>.{" "}
              {loadingPred ? "Carregando previsão…" : null}
            </div>
          </div>
        </div>

        <div className="mt-6 text-xs text-gray-500">
          Filtros ativos: doença=<span className="font-semibold">{disease}</span>, uf=
          <span className="font-semibold">{uf}</span>, período=
          <span className="font-semibold">{start}</span>→<span className="font-semibold">{end}</span>, gran=
          <span className="font-semibold">{gran}</span>, Δ=
          <span className="font-semibold">{deltaMode}</span>
        </div>
      </div>
    </div>
  );
}