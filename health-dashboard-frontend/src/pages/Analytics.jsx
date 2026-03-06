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

/* ---------------- UTIL ---------------- */

function fmt(n) {
  const v = Number(n || 0);
  return v.toLocaleString("pt-BR");
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

/* ---------------- PAGE ---------------- */

export default function Analytics() {
  const { token, tenant } = useAuth();
  const apiBase = "http://localhost:5000/api";

  const tenantScopeType = String(tenant?.scope_type || "BR").toUpperCase();
  const tenantScopeValue = String(tenant?.scope_value || "all");
  const isPrefeitura = tenantScopeType === "MUN";

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

  const ufColor = useCallback((ufLabel) => {
    let h = 0;
    const s = String(ufLabel || "");
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }, []);

  /* ---------------- FILTERS ---------------- */

  const [disease, setDisease] = useState("todas");
  const [uf, setUf] = useState("all");
  const [gran, setGran] = useState("week");
  const [deltaMode, setDeltaMode] = useState("yoy");

  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 2);
    return isoDate(d);
  });
  const [end, setEnd] = useState(() => isoDate(new Date()));

  useEffect(() => {
    if (isPrefeitura) setUf("all");
  }, [isPrefeitura]);

  /* ---------------- DATA ---------------- */

  const [analyticsData, setAnalyticsData] = useState(null);
  const [predTrends, setPredTrends] = useState([]);

  /* ---------------- LOADING ---------------- */

  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [loadingPred, setLoadingPred] = useState(false);
  const [exporting, setExporting] = useState(false);

  /* ---------------- ERRORS ---------------- */

  const [errAnalytics, setErrAnalytics] = useState("");
  const [errPred, setErrPred] = useState("");

  /* ---------------- QUERY STRING ---------------- */

  const qs = useMemo(() => {
    const params = new URLSearchParams();
    params.set("disease", disease || "all");
    params.set("uf", isPrefeitura ? "all" : (uf || "all"));
    params.set("start", start);
    params.set("end", end);
    params.set("gran", gran);
    params.set("delta_mode", deltaMode);
    return params.toString();
  }, [disease, uf, start, end, gran, deltaMode, isPrefeitura]);

  const authHeaders = useMemo(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  const fetchJson = useCallback(
    async (url) => {
      const res = await fetch(url, {
        headers: {
          ...authHeaders,
        },
        cache: "no-store",
      });

      const ct = res.headers.get("content-type") || "";
      const body = ct.includes("application/json") ? await res.json() : null;
      return { res, body };
    },
    [authHeaders]
  );

  /* ---------------- LOADERS ---------------- */

  const loadAnalytics = useCallback(async () => {
    if (!token) return;

    setLoadingAnalytics(true);
    setErrAnalytics("");

    try {
      const { res, body } = await fetchJson(`${apiBase}/analytics?${qs}`);

      if (res.status === 401) {
        setErrAnalytics("Não autorizado. Faça login novamente.");
        setAnalyticsData(null);
        return;
      }

      if (!res.ok) {
        setErrAnalytics(body?.error || `Erro ao carregar análises (HTTP ${res.status}).`);
        setAnalyticsData(null);
        return;
      }

      setAnalyticsData(body);
    } catch (e) {
      console.error(e);
      setErrAnalytics("Falha ao carregar análises.");
      setAnalyticsData(null);
    } finally {
      setLoadingAnalytics(false);
    }
  }, [token, fetchJson, apiBase, qs]);

  const loadPredictions = useCallback(async () => {
    if (!token) return;

    setLoadingPred(true);
    setErrPred("");

    try {
      const res = await fetch(`${apiBase}/predictions/trends?${qs}&horizon=12`, {
        headers: {
          ...authHeaders,
        },
        cache: "no-store",
      });

      if (res.status === 401) {
        setErrPred("Não autorizado para previsões.");
        setPredTrends([]);
        return;
      }

      if (!res.ok) {
        setErrPred(`Erro ao carregar previsão (HTTP ${res.status}).`);
        setPredTrends([]);
        return;
      }

      const body = await res.json();
      setPredTrends(Array.isArray(body) ? body : []);
    } catch (e) {
      console.error(e);
      setErrPred("Falha ao carregar previsão.");
      setPredTrends([]);
    } finally {
      setLoadingPred(false);
    }
  }, [token, apiBase, qs, authHeaders]);

  useEffect(() => {
    if (!token) return;

    const t = setTimeout(() => {
      loadAnalytics();
      loadPredictions();
    }, 250);

    return () => clearTimeout(t);
  }, [token, loadAnalytics, loadPredictions]);

  /* ---------------- EXPORT ---------------- */

  const exportCsv = useCallback(async () => {
    if (!token) {
      toast.error("Você precisa estar logado para exportar.");
      return;
    }

    setExporting(true);
    const url = `${apiBase}/analytics/export/csv?${qs}`;

    try {
      const res = await fetch(url, {
        headers: {
          ...authHeaders,
        },
        cache: "no-store",
      });

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

  /* ---------------- DROPDOWNS ---------------- */

  const diseases = isPrefeitura
    ? ["Dengue"]
    : ["Dengue", "Chikungunya", "Zika", "Coqueluche", "Rotavírus"];

  const ufs = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
  ];

  /* ---------------- DATA ADAPTERS ---------------- */

  const compareTitle = isPrefeitura
    ? "Casos no município"
    : uf === "all"
      ? "Top 10 UFs (casos)"
      : `Top 10 municípios de ${uf} (casos)`;

  const compareData = useMemo(() => {
    const rows = analyticsData?.comparatives || [];

    return rows.map((d) => {
      const label = d.city || d.label || d.uf || "—";
      return {
        label,
        cases: Number(d.count || d.cases || 0),
        short: String(label).length > 10 ? String(label).slice(0, 10) + "…" : String(label),
      };
    });
  }, [analyticsData]);

  const trendsData = useMemo(() => {
    const histRows = analyticsData?.cases_by_period || analyticsData?.cases_by_month || [];

    const hist = histRows.map((p) => ({
      bucket: String(p.period || p.month || ""),
      cases: Number(p.count || 0),
      cases_pred: null,
    }));

    const pred = predTrends.map((p) => ({
      bucket: String(p.bucket || ""),
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
  }, [analyticsData, predTrends]);

  const deltaTitle = "Δ (janela móvel)";

  const deltaValue = useMemo(() => {
    if (!analyticsData) return "—";
    if (analyticsData?.delta_label) return analyticsData.delta_label;
    if (analyticsData?.delta_vs_previous === null || analyticsData?.delta_vs_previous === undefined) {
      return "—";
    }
    return String(analyticsData.delta_vs_previous);
  }, [analyticsData]);

  const leaderLine = useMemo(() => {
    if (isPrefeitura) return "Escopo municipal aplicado automaticamente pelo tenant.";
    return null;
  }, [isPrefeitura]);

  const hasExecutiveSummary = Boolean(analyticsData?.executive_summary);

  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {isPrefeitura ? "Análises do Município" : "Análises"}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {isPrefeitura
                ? "Gráficos, estatísticas e indicadores do tenant prefeitura."
                : "Gráficos, estatísticas e indicadores."}
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
                  <option key={d} value={String(d).toLowerCase()}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {!isPrefeitura && (
              <div className="flex items-center gap-2">
                <label className="text-xs font-semibold text-gray-600">UF</label>
                <select
                  value={uf}
                  onChange={(e) => setUf(e.target.value)}
                  className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
                >
                  <option value="all">Todas</option>
                  {ufs.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
            )}

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

            {(loadingAnalytics || loadingPred) && (
              <span className="text-xs text-gray-500">Atualizando…</span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <KpiCard
            title="Casos no período"
            value={fmt(analyticsData?.cases_in_period)}
            loading={loadingAnalytics}
          />

          <KpiCard
            title={isPrefeitura ? "UF afetadas" : "UFs afetadas"}
            value={fmt(analyticsData?.uf_count)}
            loading={loadingAnalytics}
          />

          <KpiCard
            title={isPrefeitura ? "Município" : "Municípios afetados"}
            value={fmt(analyticsData?.municipality_count)}
            loading={loadingAnalytics}
          />

          <KpiCard
            title={deltaTitle}
            value={deltaValue}
            sub={leaderLine}
            loading={loadingAnalytics}
          />
        </div>

        {hasExecutiveSummary && (
          <div className="mt-6 rounded-2xl border border-gray-200 p-4 bg-gray-50">
            <div className="text-sm text-gray-500">🧠 Insight Executivo</div>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              <div>
                <span className="font-semibold">Tendência:</span>{" "}
                {analyticsData.executive_summary.trend}
              </div>
              <div>
                <span className="font-semibold">Risco:</span>{" "}
                {analyticsData.executive_summary.badge} {analyticsData.executive_summary.risk_level}
              </div>
              <div>
                <span className="font-semibold">Score:</span>{" "}
                {analyticsData.executive_summary.risk_score}/100
              </div>
              {typeof analyticsData.executive_summary.top_share === "number" && (
                <div>
                  <span className="font-semibold">Concentração:</span>{" "}
                  {analyticsData.executive_summary.top_share}%
                </div>
              )}
            </div>

            <div className="mt-3 text-sm text-gray-700">
              {analyticsData.executive_summary.alert}
            </div>
            <div className="text-sm text-gray-700">
              {analyticsData.executive_summary.recommendation}
            </div>
          </div>
        )}

        {errAnalytics && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-2">
            {errAnalytics}
          </div>
        )}

        {errPred && (
          <div className="mt-4 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-2">
            {errPred}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Comparativos</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">
              {compareTitle}
            </div>

            <div className="mt-4 h-[280px]">
              {loadingAnalytics ? (
                <div className="text-sm text-gray-500">Carregando…</div>
              ) : compareData.length === 0 ? (
                <div className="text-sm text-gray-500">Sem dados.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={compareData}
                    margin={{ top: 10, right: 10, bottom: 40, left: 10 }}
                  >
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
                          fill={isPrefeitura ? "#2563eb" : (uf === "all" ? ufColor(entry.label) : "#2563eb")}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="mt-2 text-xs text-gray-500">
              {isPrefeitura
                ? "Escopo municipal aplicado automaticamente pelo tenant."
                : "Dica: selecione uma UF para ver os top municípios."}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Tendências</div>
            <div className="mt-1 text-sm font-semibold text-gray-900">
              {isPrefeitura ? "Casos ao longo do tempo no município" : "Casos ao longo do tempo"}
            </div>

            <div className="mt-4 h-[280px]">
              {loadingAnalytics ? (
                <div className="text-sm text-gray-500">Carregando…</div>
              ) : trendsData.length === 0 ? (
                <div className="text-sm text-gray-500">Sem dados.</div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trendsData}
                    margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="bucket" hide />
                    <YAxis tickFormatter={(v) => fmt(v)} width={70} />
                    <RTooltip content={<ChartTooltip />} />

                    <Line
                      type="monotone"
                      dataKey="cases"
                      dot={false}
                      stroke="#2563eb"
                      connectNulls
                      name="Casos reais"
                    />

                    <Line
                      type="monotone"
                      dataKey="cases_pred"
                      dot={false}
                      stroke="#ef4444"
                      connectNulls
                      name="Previstos"
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
          Filtros ativos: doença=<span className="font-semibold">{disease}</span>,
          {!isPrefeitura && (
            <>
              {" "}uf=<span className="font-semibold">{uf}</span>,
            </>
          )}
          {" "}período=<span className="font-semibold">{start}</span>→
          <span className="font-semibold">{end}</span>, gran=
          <span className="font-semibold">{gran}</span>, Δ=
          <span className="font-semibold">{deltaMode}</span>
          {isPrefeitura && (
            <>
              {" "} | escopo=<span className="font-semibold">município IBGE = ({tenantScopeValue})</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}