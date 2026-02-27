// src/pages/Data.jsx
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
  const { token } = useAuth();
  const apiBase = "http://localhost:5000/api";

  // filtros
  const [disease, setDisease] = useState("all");
  const [uf, setUf] = useState("all");
  const [q, setQ] = useState("");

  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 3);
    return isoDate(d);
  });
  const [end, setEnd] = useState(() => isoDate(new Date()));

  // paginação
  const [page, setPage] = useState(1); // 1-based
  const [pageSize, setPageSize] = useState(20);

  // dados
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);

  // estados
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [exporting, setExporting] = useState(false);

  const authHeaders = useMemo(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  // ⚠️ Ajuste este endpoint para o seu backend real:
  // Sugestão de contrato:
  // GET /api/data/cases?disease=...&uf=...&start=...&end=...&q=...&page=1&page_size=20
  // => { items: [...], total: 123 }
  const listEndpoint = `${apiBase}/data/cases`;

  const qs = useMemo(() => {
    const p = new URLSearchParams();
    p.set("disease", disease || "all");
    p.set("uf", uf || "all");
    p.set("start", start);
    p.set("end", end);
    if (q.trim()) p.set("q", q.trim());
    p.set("page", String(page));
    p.set("page_size", String(pageSize));
    return p.toString();
  }, [disease, uf, start, end, q, page, pageSize]);

  const load = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setErr("");

    try {
      const res = await fetch(`${listEndpoint}?${qs}`, { headers: authHeaders });
      const ct = res.headers.get("content-type") || "";

      if (!res.ok) {
        const body = ct.includes("application/json") ? await res.json() : null;
        setRows([]);
        setTotal(0);
        setErr(body?.error || `Falha ao carregar dados (HTTP ${res.status}).`);
        return;
      }

      const body = ct.includes("application/json") ? await res.json() : null;
      const items = Array.isArray(body?.items) ? body.items : Array.isArray(body) ? body : [];
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
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [token, load]);

  // reset page ao mudar filtros principais
  useEffect(() => {
    setPage(1);
  }, [disease, uf, start, end, q, pageSize]);

  const pages = useMemo(() => {
    const p = Math.max(1, Math.ceil((total || 0) / pageSize));
    return p;
  }, [total, pageSize]);

  const exportCsv = useCallback(async () => {
    if (!token) {
      toast.error("Você precisa estar logado para exportar.");
      return;
    }

    // ⚠️ Ajuste este endpoint se necessário:
    // GET /api/data/export/csv?...mesmos filtros...
    const exportUrl = `${apiBase}/data/export/csv?${qs}`;

    setExporting(true);
    try {
      const res = await fetch(exportUrl, { headers: authHeaders });
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

  // dropdowns (MVP)
  const diseases = ["Dengue", "Chikungunya", "Zika", "Coqueluche", "Rotavírus"];
  const ufs = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"
  ];

  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Dados</h1>
            <p className="text-sm text-gray-500 mt-1">
              Explore dados brutos (filtros, paginação, exportação).
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
                  <option key={d} value={d}>{d}</option>
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
                  <option key={u} value={u}>{u}</option>
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
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar (município, id, etc.)"
                className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2 w-[240px]"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-gray-600">Page size</label>
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

            {loading && <span className="text-xs text-gray-500">Atualizando…</span>}
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
                  <th className="px-4 py-3">ID Munic</th>
                  <th className="px-4 py-3">Observação</th>
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
                        {r.dt_notific || r.date || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.disease_name || r.disease || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.uf || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.municipality || r.city || r.name || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-900">
                        {r.id_municip || r.municipality_id || "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {r.note || r.obs || ""}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 text-xs text-gray-500">
          Endpoint atual: <span className="font-semibold">{listEndpoint}</span> (ajuste se necessário)
        </div>
      </div>
    </div>
  );
}