import React, { useMemo, useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Calendar, Download } from 'lucide-react';
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
  ResponsiveContainer
} from 'recharts';
import axios from 'axios';

const Dashboard = () => {
  const { user, isAdmin, token } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Paleta simples (vai ciclar se tiver mais doenças)
  const COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#0ea5e9', '#22c55e', '#e11d48'];

  useEffect(() => {
    let alive = true;

    const fetchDashboardData = async () => {
      try {
        if (!alive) return;
        setLoading(true);
        setError(null);

        if (!token) {
          setDashboardData(null);
          setError('Você precisa estar logado para ver o dashboard.');
          setLoading(false); // ✅ evita ficar preso no spinner
          return;
        }

        // ✅ usa Bearer (JWT)
        const response = await axios.get('http://localhost:5000/api/dashboard', {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!alive) return;
        setDashboardData(response.data);
      } catch (err) {
        console.error(err);
        if (!alive) return;
        setError('Erro ao carregar dados do dashboard');
      } finally {
        if (alive) setLoading(false);
      }
    };

    fetchDashboardData();
    return () => { alive = false; };
  }, [token]);

  // =========================
  // ✅ UF x Doença (stacked)
  // =========================
  const { ufStackedData, diseaseKeys } = useMemo(() => {
    const rows = dashboardData?.cases_by_uf_disease;
    if (!Array.isArray(rows) || rows.length === 0) {
      return { ufStackedData: [], diseaseKeys: [] };
    }

    // Lista de doenças presentes no dataset (ordenada p/ consistência)
    const diseases = Array.from(new Set(rows.map(r => r.disease).filter(Boolean))).sort();

    // Pivot: { RJ: { uf:"RJ", Dengue: 10, Zika: 2, ... }, ... }
    const pivot = new Map();

    for (const r of rows) {
      const uf = r.uf;
      const disease = r.disease;
      const count = Number(r.count || 0);

      if (!uf || !disease) continue;

      if (!pivot.has(uf)) {
        // inicializa com 0 para todas as doenças (evita undefined no gráfico)
        const base = { uf };
        for (const d of diseases) base[d] = 0;
        pivot.set(uf, base);
      }

      pivot.get(uf)[disease] = count;
    }

    // transforma em array e calcula total p/ ordenar top 10 UFs
    const arr = Array.from(pivot.values()).map((row) => {
      const total = diseases.reduce((acc, d) => acc + (Number(row[d]) || 0), 0);
      return { ...row, __total: total };
    });

    // Ordena por total desc e limita top 10
    arr.sort((a, b) => (b.__total || 0) - (a.__total || 0));
    const top10 = arr.slice(0, 10).map(({ __total, ...rest }) => rest); // ✅ remove total do dataset do gráfico

    return { ufStackedData: top10, diseaseKeys: diseases };
  }, [dashboardData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-600">
        <AlertTriangle className="mr-2" />
        {error}
      </div>
    );
  }

  if (!dashboardData) return null;

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Plataforma de Saúde - Health Data Insights</h1>
          <p className="text-gray-600">Bem-vindo, {user?.first_name} {user?.last_name}</p>
        </div>

        <div className="flex gap-3">
          <Badge variant="outline">
            <Calendar className="h-3 w-3 mr-1" />
            Atualizado hoje
          </Badge>

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
            {dashboardData.total_cases}
            <p className="text-xs text-muted-foreground">
              Brasil
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Hospitalizações</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.hospitalization_count}</div>
            <p className="text-xs text-muted-foreground">
              {dashboardData.hospitalization_rate}% do total de casos
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Óbitos Confirmados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.death_count}</div>
            <p className="text-xs text-muted-foreground">
              Taxa de letalidade: {dashboardData.death_rate}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Doenças Monitoradas</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {Array.isArray(dashboardData.cases_by_disease) ? dashboardData.cases_by_disease.length : 0}
            <p className="text-xs text-muted-foreground">
              Brasil
            </p>
          </CardContent>
        </Card>
      </div>

      {/* GRÁFICOS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* EVOLUÇÃO MENSAL */}
        <Card>
          <CardHeader>
            <CardTitle>Evolução Mensal de Casos</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={dashboardData.cases_by_month || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Area dataKey="count" stroke="#2563eb" fill="#2563eb" fillOpacity={0.3} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* DOENÇAS */}
        <Card>
          <CardHeader>
            <CardTitle>Distribuição por Doença</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={dashboardData.cases_by_disease || []}
                  dataKey="count"
                  nameKey="disease"
                  outerRadius={100}
                  label
                >
                  {(dashboardData.cases_by_disease || []).map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* ✅ CASOS POR UF (STACKED POR DOENÇA) */}
      <Card>
        <CardHeader>
          <CardTitle>Casos por Unidade Federativa (por Doença)</CardTitle>
        </CardHeader>
        <CardContent>
          {!ufStackedData.length ? (
            <div className="text-sm text-muted-foreground">
              Sem dados suficientes para UF x Doença. Verifique se o backend retorna <code>cases_by_uf_disease</code>.
            </div>
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
            * Brasil - Mostrando Top 10 UFs por total (somando todas as doenças).
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;