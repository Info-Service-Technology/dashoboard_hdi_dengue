import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";

function isoDate(d) {
  const pad = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fmt(n) {
  const v = Number(n || 0);
  return v.toLocaleString("pt-BR");
}

export default function Data() {
  const { token, tenant } = useAuth();
  const apiBase = "http://localhost:5000/api";

  const tenantScopeType = String(tenant?.scope_type || "BR").toUpperCase();
  const tenantScopeValue = String(tenant?.scope_value || "all");
  const isPrefeitura = tenantScopeType === "MUN";

  const [disease, setDisease] = useState(isPrefeitura ? "dengue" : "all");
  const [uf, setUf] = useState("all");
  const [q, setQ] = useState("");

  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 3);
    return isoDate(d);
  });
  const [end, setEnd] = useState(() => isoDate(new Date()));

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  const [diseases, setDiseases] = useState(isPrefeitura ? ["Dengue"] : []);
  const [ufs, setUfs] = useState(isPrefeitura ? ["RJ"] : []);

  const [loading, setLoading] = useState(false);
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [err, setErr] = useState("");
  const [exporting, setExporting] = useState(false);

  const authHeaders = useMemo(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  const listEndpoint = `${apiBase}/data/cases`;

  useEffect(() => {
    if (isPrefeitura) setUf("all");
  }, [isPrefeitura]);

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    p.set("disease", disease || "all");
    p.set("uf", isPrefeitura ? "all" : (uf || "all"));
    p.set("start", start);
    p.set("end", end);
    if (q.trim()) p.set("search", q.trim());
    p.set("page", String(page));
    p.set("page_size", String(pageSize));
    return p.toString();
  }, [disease, uf, start, end, q, page, pageSize, isPrefeitura]);

  const loadMeta = useCallback(async () => {
    if (!token) return;

    setLoadingMeta(true);
    try {
      const res = await fetch(`${apiBase}/data/meta`, {
        headers: authHeaders,
        cache: "no-store",
      });

      if (!res.ok) return;

      const body = await res.json();
      setDiseases(Array.isArray(body?.diseases) ? body.diseases : []);
      setUfs(Array.isArray(body?.ufs) ? body.ufs : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingMeta(false);
    }
  }, [token, apiBase, authHeaders]);

  const load = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setErr("");

    try {
      const res = await fetch(`${listEndpoint}?${qs}`, {
        headers: authHeaders,
        cache: "no-store",
      });
      const ct = res.headers.get("content-type") || "";

      if (!res.ok) {
        const body = ct.includes("application/json") ? await res.json() : null;
        setRows([]);
        setTotal(0);
        setErr(body?.error || `Falha ao carregar dados (HTTP ${res.status}).`);
        return;
      }

      const body = ct.includes("application/json") ? await res.json() : null;
      const items = Array.isArray(body?.items) ? body.items : [];
      const t = Number(body?.total ?? items.length ?? 0);

      setRows(items);
      setTotal(t);
    } catch (e) {
      console.error(e);
      setRows([]);
      setTotal(0);
      setErr("Falha ao carregar dados.");
    } finally {
      setLoading(false);
    }
  }, [token, listEndpoint, qs, authHeaders]);

  useEffect(() => {
    if (!token) return;
    loadMeta();
  }, [token, loadMeta]);

  useEffect(() => {
    if (!token) return;
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [token, load]);

  useEffect(() => {
    setPage(1);
  }, [disease, uf, start, end, q, pageSize]);

  const pages = useMemo(() => {
    return Math.max(1, Math.ceil((total || 0) / pageSize));
  }, [total, pageSize]);

  const exportCsv = useCallback(async () => {
    if (!token) {
      toast.error("Você precisa estar logado para exportar.");
      return;
    }

    const exportUrl = `${apiBase}/data/export/csv?${qs}`;

    setExporting(true);
    try {
      const res = await fetch(exportUrl, {
        headers: authHeaders,
        cache: "no-store",
      });

      if (!res.ok) {
        let msg = `Falha ao exportar (HTTP ${res.status}).`;
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
      const filename = match?.[1] || "hdi_data.csv";

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

  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {isPrefeitura ? "Dados do Município" : "Dados"}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {isPrefeitura
                ? "Explore os dados epidemiológicos do município."
                : "Explore dados brutos com filtros, paginação e exportação."}
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
                {!isPrefeitura && <option value="all">Todas</option>}
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
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder={isPrefeitura ? "Buscar no município" : "Buscar (município, doença, etc.)"}
                className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 w-[240px]"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Itens</label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-1"
              >
                {[10, 20, 50, 100].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>

            <button
              onClick={exportCsv}
              disabled={exporting}
              className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 hover:bg-gray-50 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {exporting ? "Exportando…" : "Exportar CSV"}
            </button>

            {(loading || loadingMeta) && (
              <span className="text-xs text-gray-500">Atualizando…</span>
            )}
          </div>
        </div>

        {err && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-2">
            {err}
          </div>
        )}

        <div className="mt-6 rounded-2xl border border-gray-200 overflow-hidden">
          <div className="flex items-center justify-between p-4 bg-gray-50 border-b border-gray-200">
            <div className="text-sm text-gray-700">
              Registros: <span className="font-semibold">{fmt(total)}</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 disabled:opacity-50"
              >
                ←
              </button>
              <div className="text-sm text-gray-700">
                Página <span className="font-semibold">{page}</span> de{" "}
                <span className="font-semibold">{pages}</span>
              </div>
              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page >= pages || loading}
                className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 disabled:opacity-50"
              >
                →
              </button>
            </div>
          </div>

          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white sticky top-0">
                <tr className="text-left text-gray-600 border-b border-gray-200">
                  <th className="px-4 py-3">Data</th>
                  <th className="px-4 py-3">Doença</th>
                  <th className="px-4 py-3">UF</th>
                  <th className="px-4 py-3">Município</th>
                  <th className="px-4 py-3">IBGE</th>
                  <th className="px-4 py-3">
                    {isPrefeitura ? "Casos" : "Observação"}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white">
                {loading ? (
                  <tr>
                    <td className="px-4 py-6 text-gray-500" colSpan={6}>
                      Carregando…
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-6 text-gray-500" colSpan={6}>
                      Sem dados.
                    </td>
                  </tr>
                ) : (
                  rows.map((r, idx) => (
                    <tr key={r.id || idx} className="border-b border-gray-100">
                      <td className="px-4 py-3 text-gray-900">
                        {r.dt_notific || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.disease_name || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.uf || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.municipality || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.ibge || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {isPrefeitura ? fmt(r.count) : (r.note || "")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 text-xs text-gray-500">
          Filtros ativos: doença=<span className="font-semibold">{disease}</span>,
          {!isPrefeitura && (
            <>
              {" "}uf=<span className="font-semibold">{uf}</span>,
            </>
          )}
          {" "}período=<span className="font-semibold">{start}</span>→
          <span className="font-semibold">{end}</span>
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