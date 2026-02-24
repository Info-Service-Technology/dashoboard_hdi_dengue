import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../../contexts/AuthContext";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { Save, Loader2, Settings2, RefreshCw, Map } from "lucide-react";

const USE_API = true; // 🔥 troque para true quando endpoints estiverem prontos

export default function SystemSettingsPage() {
  const { isAdmin } = useAuth();

  const [loading, setLoading] = useState(USE_API);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [cfg, setCfg] = useState({
    app_name: "Dashboard Saúde",
    default_language: "pt-BR",
    timezone: "America/Sao_Paulo",
    enable_notifications: true,
    enable_audit_log: true,
    data_refresh_minutes: 15,
    maps_default_zoom: 6
  });

  const onChange = (k) => (e) => {
    const v = e?.target?.value;
    setCfg((s) => ({ ...s, [k]: v }));
  };

  const onToggle = (k) => (checked) => setCfg((s) => ({ ...s, [k]: !!checked }));

  useEffect(() => {
    let alive = true;

    const load = async () => {
      setError("");
      setLoading(true);
      try {
        // Sugestão:
        // GET /api/system/settings  -> cfg
        const { data } = await axios.get("/api/system/settings");
        if (!alive) return;
        setCfg({
          app_name: data?.app_name ?? "Dashboard Saúde",
          default_language: data?.default_language ?? "pt-BR",
          timezone: data?.timezone ?? "America/Sao_Paulo",
          enable_notifications: !!data?.enable_notifications,
          enable_audit_log: !!data?.enable_audit_log,
          data_refresh_minutes: Number(data?.data_refresh_minutes ?? 15),
          maps_default_zoom: Number(data?.maps_default_zoom ?? 6),
        });
      } catch (e) {
        if (!alive) return;
        setError("Não foi possível carregar as configurações do sistema.");
      } finally {
        if (alive) setLoading(false);
      }
    };

    if (USE_API) load();

    return () => { alive = false; };
  }, []);

  const handleSave = async () => {
    setError("");
    setSaving(true);
    try {
      if (USE_API) {
        // Sugestão:
        // PUT /api/system/settings  -> cfg
        await axios.put("/api/system/settings", {
          ...cfg,
          data_refresh_minutes: Number(cfg.data_refresh_minutes),
          maps_default_zoom: Number(cfg.maps_default_zoom),
        });
      }
    } catch (e) {
      setError("Falha ao salvar configurações.");
    } finally {
      setSaving(false);
    }
  };

  // Segurança extra (mas sua rota já usa adminOnly)
  if (!isAdmin) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Você não tem permissão para acessar esta página.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="p-0">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Sistema</h1>
            <p className="text-sm text-muted-foreground">
              Configurações globais da plataforma (admin).
            </p>
          </div>

          <Button onClick={handleSave} disabled={loading || saving} className="gap-2">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Salvar
          </Button>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Geral */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                Geral
              </CardTitle>
              <CardDescription>Preferências padrão e comportamento do sistema</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="app_name">Nome do sistema</Label>
                <Input
                  id="app_name"
                  value={cfg.app_name}
                  onChange={onChange("app_name")}
                  disabled={loading}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="default_language">Idioma padrão</Label>
                  <Input
                    id="default_language"
                    value={cfg.default_language}
                    onChange={onChange("default_language")}
                    disabled={loading}
                    placeholder="pt-BR"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">Timezone</Label>
                  <Input
                    id="timezone"
                    value={cfg.timezone}
                    onChange={onChange("timezone")}
                    disabled={loading}
                    placeholder="America/Sao_Paulo"
                  />
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between rounded-xl border p-4">
                <div className="space-y-1">
                  <div className="text-sm font-medium">Notificações</div>
                  <div className="text-xs text-muted-foreground">Habilitar avisos no sistema</div>
                </div>
                <Switch checked={cfg.enable_notifications} onCheckedChange={onToggle("enable_notifications")} />
              </div>

              <div className="flex items-center justify-between rounded-xl border p-4">
                <div className="space-y-1">
                  <div className="text-sm font-medium">Auditoria</div>
                  <div className="text-xs text-muted-foreground">Registrar ações administrativas</div>
                </div>
                <Switch checked={cfg.enable_audit_log} onCheckedChange={onToggle("enable_audit_log")} />
              </div>
            </CardContent>
          </Card>

          {/* Dados e Mapas */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="h-5 w-5" />
                Dados e mapas
              </CardTitle>
              <CardDescription>Atualização automática e comportamento do mapa</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="data_refresh_minutes">Refresh (min)</Label>
                <Input
                  id="data_refresh_minutes"
                  type="number"
                  min={1}
                  value={cfg.data_refresh_minutes}
                  onChange={onChange("data_refresh_minutes")}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Intervalo de atualização automática do dashboard.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="maps_default_zoom">Zoom padrão do mapa</Label>
                <Input
                  id="maps_default_zoom"
                  type="number"
                  min={1}
                  max={18}
                  value={cfg.maps_default_zoom}
                  onChange={onChange("maps_default_zoom")}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground flex items-center gap-2">
                  <Map className="h-4 w-4" />
                  Controle inicial do Leaflet.
                </p>
              </div>

              <Separator />

              {!USE_API && (
                <p className="text-xs text-muted-foreground">
                  * Modo UI: salvamento ainda não integrado ao backend. Troque <code>USE_API</code> para <code>true</code> quando criar os endpoints.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}