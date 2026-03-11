import React, { useMemo, useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { useTenant } from "../contexts/TenantContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar, Download } from "lucide-react";
import PageLoading from "../components/common/PageLoading";
import ErrorState from "../components/common/ErrorState";
import EmptyState from "../components/common/EmptyState";
import {
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import axios from "axios";

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#f59e0b",
  "#dc2626",
  "#7c3aed",
  "#0ea5e9",
  "#22c55e",
  "#e11d48",
];

const Dashboard = () => {
  const { user, isAdmin, token } = useAuth();
  const { tenantName, scopeType, isMunicipal, loadingTenant } = useTenant();

  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isPrefeitura = isMunicipal;

  useEffect(() => {
    let alive = true;

    const fetchDashboardData = async () => {
      try {
        if (!alive) return;

        setLoading(true);
        setError(null);

        if (!token) {
          setDashboardData(null);
          setError("Você precisa estar logado para ver o dashboard.");
          return;
        }

        const response = await axios.get("/api/dashboard", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!alive) return;

        setDashboardData(response.data);
      } catch (err) {
        console.error(err);

        if (!alive) return;

        setDashboardData(null);
        setError("Erro ao carregar dados do dashboard.");
      } finally {
        if (alive) setLoading(false);
      }
    };

    fetchDashboardData();

    return () => {
      alive = false;
    };
  }, [token, scopeType]);

  const { ufStackedData, diseaseKeys } = useMemo(() => {
    const rows = dashboardData?.cases_by_uf_disease;

    if (!Array.isArray(rows) || rows.length === 0) {
      return { ufStackedData: [], diseaseKeys: [] };
    }

    const diseases = Array.from(
      new Set(rows.map((r) => r.disease).filter(Boolean))
    ).sort();

    const pivot = new Map();

    for (const r of rows) {
      const uf = r.uf;
      const disease = r.disease;
      const count = Number(r.count || 0);

      if (!uf || !disease) continue;

      if (!pivot.has(uf)) {
        const base = { uf };
        for (const d of diseases) base[d] = 0;
        pivot.set(uf, base);
      }

      pivot.get(uf)[disease] = count;
    }

    const arr = Array.from(pivot.values()).map((row) => {
      const total = diseases.reduce((acc, d) => acc + (Number(row[d]) || 0), 0);
      return { ...row, __total: total };
    });

    arr.sort((a, b) => (b.__total || 0) - (a.__total || 0));
    const top10 = arr.slice(0, 10).map(({ __total, ...rest }) => rest);

    return { ufStackedData: top10, diseaseKeys: diseases };
  }, [dashboardData]);

  const cityData = useMemo(() => {
    return Array.isArray(dashboardData?.cases_by_city)
      ? dashboardData.cases_by_city
      : [];
  }, [dashboardData]);

  const cityName = useMemo(() => {
    if (!isPrefeitura) return "Brasil";
    return dashboardData?.scope?.city_name || cityData?.[0]?.city || tenantName || "Município";
  }, [isPrefeitura, dashboardData, cityData, tenantName]);

  if (loading || loadingTenant) {
    return <PageLoading message="Carregando dashboard..." />;
  }

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!dashboardData) {
    return <EmptyState message="Nenhum dado disponível para o dashboard." />;
  }

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">
            {isPrefeitura
              ? `Painel da Prefeitura - ${cityName}`
              : "Plataforma de Saúde - Health Data Insights"}
          </h1>
          <p className="text-gray-600">
            Bem-vindo, {user?.first_name} {user?.last_name}
          </p>
        </div>

        <div className="flex gap-3">
          <Badge variant="outline">
            <Calendar className="h-3 w-3 mr-1" />
            Atualizado hoje
          </Badge>

          {isPrefeitura && (
            <Badge variant="secondary">
              Município: {cityName}
            </Badge>
          )}

          {isAdmin && (
            <Button size="sm">
              <Download className="h-4 w-4 mr-1" />
              Exportar
            </Button>
          )}
        </div>
      </div>

      {/* CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Total de Casos</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {Number(dashboardData.total_cases || 0).toLocaleString("pt-BR")}
            <p className="text-xs text-muted-foreground">
              {isPrefeitura ? cityName : "Brasil"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Hospitalizações</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Number(dashboardData.hospitalization_count || 0).toLocaleString("pt-BR")}
            </div>
            <p className="text-xs text-muted-foreground">
              {dashboardData.hospitalization_rate ?? 0}% do total de casos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Óbitos Confirmados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Number(dashboardData.death_count || 0).toLocaleString("pt-BR")}
            </div>
            <p className="text-xs text-muted-foreground">
              Taxa de letalidade: {dashboardData.death_rate ?? 0}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Doenças Monitoradas</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {Array.isArray(dashboardData.cases_by_disease)
              ? dashboardData.cases_by_disease.length
              : 0}
            <p className="text-xs text-muted-foreground">
              {isPrefeitura ? cityName : "Brasil"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* GRÁFICOS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>
              {isPrefeitura
                ? `Evolução Mensal de Casos - ${cityName}`
                : "Evolução Mensal de Casos"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!Array.isArray(dashboardData.cases_by_month) || dashboardData.cases_by_month.length === 0 ? (
              <EmptyState message="Sem dados de evolução mensal." />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={dashboardData.cases_by_month}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    dataKey="count"
                    stroke="#2563eb"
                    fill="#2563eb"
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Distribuição por Doença</CardTitle>
          </CardHeader>
          <CardContent>
            {!Array.isArray(dashboardData.cases_by_disease) || dashboardData.cases_by_disease.length === 0 ? (
              <EmptyState message="Sem dados de distribuição por doença." />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={dashboardData.cases_by_disease}
                    dataKey="count"
                    nameKey="disease"
                    outerRadius={100}
                    label
                  >
                    {dashboardData.cases_by_disease.map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* BRASIL: CASOS POR UF */}
      {!isPrefeitura && (
        <Card>
          <CardHeader>
            <CardTitle>Casos por Unidade Federativa (por Doença)</CardTitle>
          </CardHeader>
          <CardContent>
            {!ufStackedData.length ? (
              <EmptyState message="Sem dados suficientes para UF x Doença." />
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={ufStackedData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="uf" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {diseaseKeys.map((disease, idx) => (
                    <Bar
                      key={disease}
                      dataKey={disease}
                      stackId="a"
                      name={disease}
                      fill={COLORS[idx % COLORS.length]}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}

            <p className="mt-2 text-xs text-muted-foreground">
              * Brasil - Mostrando Top 10 UFs por total.
            </p>
          </CardContent>
        </Card>
      )}

      {/* PREFEITURA: CASOS NO MUNICÍPIO */}
      {isPrefeitura && (
        <Card>
          <CardHeader>
            <CardTitle>Casos no município</CardTitle>
          </CardHeader>
          <CardContent>
            {cityData.length === 0 ? (
              <EmptyState message="Sem dados do município." />
            ) : (
              <div className="overflow-auto border rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr className="text-left">
                      <th className="px-4 py-3 font-semibold text-gray-700">Município</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">UF</th>
                      <th className="px-4 py-3 font-semibold text-gray-700">Casos</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {cityData.map((row, index) => (
                      <tr key={`${row.city}-${index}`} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-semibold text-gray-900">{row.city}</td>
                        <td className="px-4 py-3">{row.uf}</td>
                        <td className="px-4 py-3">
                          {Number(row.count || 0).toLocaleString("pt-BR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <p className="mt-2 text-xs text-muted-foreground">
              * Dados epidemiológicos do tenant prefeitura.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;