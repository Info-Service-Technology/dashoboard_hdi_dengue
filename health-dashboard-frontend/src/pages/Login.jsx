import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Eye, EyeOff, Activity } from "lucide-react";

const API_BASE = "http://localhost:5000/api";

const isValidEmail = (v) => {
  const s = String(v || "").trim();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s);
};

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // ✅ TENANT (somente 1 state)
  const [tenants, setTenants] = useState([{ slug: "br", name: "Brasil" }]);
  const [tenantSlug, setTenantSlug] = useState("br");
  const [loadingTenants, setLoadingTenants] = useState(false);

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login, token } = useAuth();
  const navigate = useNavigate();

  // evita race condition
  const reqIdRef = useRef(0);

  const canQueryTenants = useMemo(() => isValidEmail(email), [email]);

  useEffect(() => {
    if (token) navigate("/dashboard");
  }, [token, navigate]);

  useEffect(() => {
    setError("");

    if (!canQueryTenants) {
      setTenants([{ slug: "br", name: "Brasil" }]);
      setTenantSlug("br");
      return;
    }

    const id = ++reqIdRef.current;

    const t = setTimeout(async () => {
      setLoadingTenants(true);
      try {
        const url = `${API_BASE}/auth/tenants?email=${encodeURIComponent(
          email.trim().toLowerCase()
        )}`;
        const res = await fetch(url);
        const body = await res.json();

        if (id !== reqIdRef.current) return;

        const list = Array.isArray(body) ? body : [];
        // sempre inclui Brasil como default
        const merged = [{ slug: "br", name: "Brasil" }, ...list.filter((x) => x?.slug && x.slug !== "br")];

        setTenants(merged);

        // se tenant atual não existir, volta pro br
        if (!merged.some((x) => x.slug === tenantSlug)) {
          setTenantSlug("br");
        }
      } catch (e) {
        console.error(e);
        if (id !== reqIdRef.current) return;
        setTenants([{ slug: "br", name: "Brasil" }]);
        setTenantSlug("br");
      } finally {
        if (id === reqIdRef.current) setLoadingTenants(false);
      }
    }, 350);

    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email, canQueryTenants]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const chosenTenant = String(tenantSlug || "br").trim().toLowerCase();

    const result = await login(email.trim().toLowerCase(), password, chosenTenant);

    if (result.success) navigate("/dashboard");
    else setError(result.error);

    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center space-x-2">
            <Activity className="h-8 w-8 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">Health Data Insights</h1>
          </div>
          <p className="text-gray-600">Plataforma Inteligente de Saúde</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Entrar na Plataforma</CardTitle>
            <CardDescription>Acesse o dashboard com escopo autorizado</CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Email */}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="seu@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                {loadingTenants && <div className="text-xs text-gray-500">Carregando tenants…</div>}
              </div>

              {/* Tenant */}
              <div className="space-y-2">
                <Label htmlFor="tenant">Tenant (escopo)</Label>
                <select
                  id="tenant"
                  value={tenantSlug}
                  onChange={(e) => setTenantSlug(e.target.value)}
                  className="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
                  disabled={!canQueryTenants || loadingTenants}
                  title={!canQueryTenants ? "Digite um email válido para carregar tenants." : undefined}
                >
                  {tenants.map((t) => (
                    <option key={t.slug} value={t.slug}>
                      {t.name} ({t.slug})
                    </option>
                  ))}
                </select>
                <div className="text-xs text-gray-500">
                  Selecione o escopo permitido para seu usuário.
                </div>
              </div>

              {/* Password */}
              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Sua senha"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Entrando..." : "Entrar"}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                Não tem uma conta?{" "}
                <Link to="/register" className="text-blue-600 hover:underline">
                  Registre-se
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="text-center text-xs text-gray-500">
          <p>Plataforma Inteligente de Análise em Saúde</p>
          <p>Dados baseados no SINAN/DATASUS</p>
        </div>
      </div>
    </div>
  );
}