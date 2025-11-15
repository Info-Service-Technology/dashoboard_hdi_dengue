import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Activity, 
  TrendingUp, 
  Users, 
  AlertTriangle,
  BarChart3,
  Map,
  Calendar,
  Download
} from 'lucide-react';
import {
  LineChart,
  Line,
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
  const { user, isAdmin } = useAuth();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Dados simulados para demonstração
  const mockData = {
    total_cases: 1000,
    hospitalization_rate: 15.2,
    death_rate: 2.1,
    cases_by_disease: [
      { disease: 'Dengue', count: 500 },
      { disease: 'Chikungunya', count: 200 },
      { disease: 'Coqueluche', count: 100 },
      { disease: 'Zika', count: 150 },
      { disease: 'Rotavírus', count: 50 }
    ],
    cases_by_month: [
      { month: '2024-01', count: 45 },
      { month: '2024-02', count: 52 },
      { month: '2024-03', count: 78 },
      { month: '2024-04', count: 95 },
      { month: '2024-05', count: 120 },
      { month: '2024-06', count: 140 },
      { month: '2024-07', count: 165 },
      { month: '2024-08', count: 180 },
      { month: '2024-09', count: 155 },
      { month: '2024-10', count: 135 },
      { month: '2024-11', count: 110 },
      { month: '2024-12', count: 85 }
    ],
    cases_by_uf: [
      { uf: 'SP', count: 250 },
      { uf: 'RJ', count: 180 },
      { uf: 'MG', count: 150 },
      { uf: 'BA', count: 120 },
      { uf: 'PR', count: 100 },
      { uf: 'RS', count: 80 },
      { uf: 'SC', count: 70 },
      { uf: 'GO', count: 50 }
    ]
  };

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Simular carregamento
        await new Promise(resolve => setTimeout(resolve, 1000));
        setDashboardData(mockData);
      } catch (err) {
        setError('Erro ao carregar dados do dashboard');
        console.error('Erro:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Dashboard de Análise Preditiva
          </h1>
          <p className="text-gray-600 mt-1">
            Bem-vindo, {user?.first_name}! Aqui está um resumo dos dados de saúde.
          </p>
        </div>
        <div className="flex items-center space-x-3 mt-4 sm:mt-0">
          <Badge variant="outline" className="flex items-center space-x-1">
            <Calendar className="h-3 w-3" />
            <span>Última atualização: Hoje</span>
          </Badge>
          {isAdmin && (
            <Button size="sm" className="flex items-center space-x-2">
              <Download className="h-4 w-4" />
              <span>Exportar</span>
            </Button>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total de Casos</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.total_cases?.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              +12% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Hospitalização</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.hospitalization_rate}%</div>
            <p className="text-xs text-muted-foreground">
              -2.1% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taxa de Óbitos</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.death_rate}%</div>
            <p className="text-xs text-muted-foreground">
              -0.5% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Doenças Monitoradas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData?.cases_by_disease?.length}</div>
            <p className="text-xs text-muted-foreground">
              Arboviroses e outras doenças
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evolução Temporal */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Evolução Temporal dos Casos</span>
            </CardTitle>
            <CardDescription>
              Número de casos notificados por mês
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={dashboardData?.cases_by_month}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#0088FE" 
                  fill="#0088FE" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Distribuição por Doença */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>Distribuição por Doença</span>
            </CardTitle>
            <CardDescription>
              Proporção de casos por tipo de doença
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={dashboardData?.cases_by_disease}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ disease, percent }) => `${disease} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {dashboardData?.cases_by_disease?.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Geographic Distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Map className="h-5 w-5" />
            <span>Distribuição Geográfica</span>
          </CardTitle>
          <CardDescription>
            Casos por Unidade Federativa (Top 8)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dashboardData?.cases_by_uf}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="uf" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#00C49F" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Atividades Recentes</CardTitle>
          <CardDescription>
            Últimas atualizações do sistema
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-blue-100 rounded-full">
                <Activity className="h-4 w-4 text-blue-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Novos casos de Dengue registrados</p>
                <p className="text-xs text-gray-500">45 novos casos em São Paulo - há 2 horas</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-green-100 rounded-full">
                <TrendingUp className="h-4 w-4 text-green-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Relatório mensal gerado</p>
                <p className="text-xs text-gray-500">Análise de arboviroses - há 4 horas</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="p-2 bg-yellow-100 rounded-full">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Alerta epidemiológico</p>
                <p className="text-xs text-gray-500">Aumento de casos de Chikungunya no RJ - há 6 horas</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;

