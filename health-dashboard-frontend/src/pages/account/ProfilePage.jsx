import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { useAuth } from "../../contexts/AuthContext";
import { applyTheme } from "@/lib/theme";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

import { User, Shield, Save, Loader2, Mail, Phone, MapPin, Palette } from "lucide-react";

const USE_API = true;

// Ajuste se seu backend estiver em outro host/porta
const API_ORIGIN = "http://localhost:5000";

// Converte "/static/..." em "http://localhost:5000/static/..."
function normalizeAvatarUrl(url) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${API_ORIGIN}${url}`;
  return url;
}

export default function ProfilePage() {
  const { user, isAdmin } = useAuth();

  const base = useMemo(
    () => ({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      email: user?.email || "",
      role: user?.role || "guest",
      // user_profile
      phone: "",
      location: "",
      about: "",
      avatar_url: "",
      theme: "light", // light | dark | system
    }),
    [user]
  );

  const [form, setForm] = useState(base);
  const [loading, setLoading] = useState(USE_API);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const [avatarFile, setAvatarFile] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const previewUrlRef = useRef(""); // para revogar URL.createObjectURL

  const initials =
    `${(form.first_name?.[0] || "U")}${(form.last_name?.[0] || "").toUpperCase()}`.toUpperCase();

  const onChange = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  // Carregar dados
  useEffect(() => {
    let alive = true;

    const load = async () => {
      setError("");
      setLoading(true);

      try {
        const { data } = await axios.get("/api/account/me");
        if (!alive) return;

        const next = {
          first_name: data?.user?.first_name ?? "",
          last_name: data?.user?.last_name ?? "",
          email: data?.user?.email ?? "",
          role: data?.user?.role ?? "guest",
          phone: data?.profile?.phone ?? "",
          location: data?.profile?.location ?? "",
          about: data?.profile?.about ?? "",
          avatar_url: normalizeAvatarUrl(data?.profile?.avatar_url ?? ""),
          theme: data?.profile?.theme ?? "light",
        };

        setForm(next);
        applyTheme(next.theme);
      } catch (e) {
        if (!alive) return;
        setError("Não foi possível carregar seu perfil. Verifique o backend.");
      } finally {
        if (alive) setLoading(false);
      }
    };

    if (USE_API) load();
    else {
      setForm(base);
      applyTheme(base.theme);
      setLoading(false);
    }

    return () => {
      alive = false;
    };
  }, [base]);

  // Limpar preview URL ao desmontar / trocar arquivo
  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
        previewUrlRef.current = "";
      }
    };
  }, []);

  const handlePickAvatar = (e) => {
    const f = e.target.files?.[0] || null;

    setAvatarFile(f);

    // limpa preview antigo (evita vazamento)
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = "";
    }

    if (f) {
      const url = URL.createObjectURL(f);
      previewUrlRef.current = url;
      setAvatarPreview(url);
    } else {
      setAvatarPreview("");
    }
  };

  const refetchMe = async () => {
    const { data } = await axios.get("/api/account/me");
    const next = {
      first_name: data?.user?.first_name ?? "",
      last_name: data?.user?.last_name ?? "",
      email: data?.user?.email ?? "",
      role: data?.user?.role ?? "guest",
      phone: data?.profile?.phone ?? "",
      location: data?.profile?.location ?? "",
      about: data?.profile?.about ?? "",
      avatar_url: normalizeAvatarUrl(data?.profile?.avatar_url ?? ""),
      theme: data?.profile?.theme ?? "light",
    };
    setForm(next);
    applyTheme(next.theme);
  };

  const handleSave = async () => {
    setError("");
    setSaving(true);

    try {
      if (USE_API) {
        let avatar_url = form.avatar_url;

        // 1) Se tiver arquivo: upload e pega URL final
        if (avatarFile) {
          const fd = new FormData();
          fd.append("file", avatarFile);

          const up = await axios.post("/api/account/avatar", fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });

          avatar_url = normalizeAvatarUrl(up.data?.avatar_url || "");
        }

        // 2) Salva tudo
        await axios.put("/api/account/me", {
          first_name: form.first_name,
          last_name: form.last_name,
          phone: form.phone,
          location: form.location,
          about: form.about,
          theme: form.theme,
          avatar_url,
        });

        // 3) Atualiza state imediatamente (sem reload)
        setForm((s) => ({ ...s, avatar_url }));

        // limpa seleção/preview
        setAvatarFile(null);
        setAvatarPreview("");
        if (previewUrlRef.current) {
          URL.revokeObjectURL(previewUrlRef.current);
          previewUrlRef.current = "";
        }

        // 4) (Recomendado) Recarrega do backend p/ garantir consistência
        await refetchMe();
      }

      // aplica tema (mesmo que não use API)
      applyTheme(form.theme);
    } catch (e) {
      console.error(e);
      setError("Falha ao salvar. Tente novamente.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-0">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Perfil</h1>
            <p className="text-sm text-muted-foreground">
              Gerencie suas informações pessoais e preferências.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant={isAdmin ? "default" : "secondary"} className="gap-2">
              {isAdmin ? <Shield className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
              {isAdmin ? "Administrador" : "Convidado"}
            </Badge>

            <Button onClick={handleSave} disabled={loading || saving} className="gap-2">
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Salvar
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Coluna esquerda (Resumo) */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Conta</CardTitle>
              <CardDescription>Informações básicas</CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="rounded-xl border bg-muted/30 p-4 flex items-center gap-3">
                <div className="h-12 w-12 rounded-full border overflow-hidden bg-muted flex items-center justify-center">
                  {form.avatar_url ? (
                    <img
                      src={form.avatar_url}
                      alt="Avatar"
                      className="h-full w-full object-cover"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                  ) : (
                    <span className="text-sm font-semibold text-muted-foreground">{initials}</span>
                  )}
                </div>

                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">
                    {form.first_name} {form.last_name}
                  </div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1 truncate">
                    <Mail className="h-3.5 w-3.5" />
                    {form.email || "—"}
                  </div>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Telefone:</span>
                  <span className="font-medium">{form.phone || "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Local:</span>
                  <span className="font-medium">{form.location || "—"}</span>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-2 text-sm">
                <Palette className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Tema:</span>
                <span className="font-medium capitalize">{form.theme}</span>
              </div>
            </CardContent>
          </Card>

          {/* Coluna direita (Edição) */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Editar perfil</CardTitle>
              <CardDescription>Atualize seus dados (user + user_profile)</CardDescription>
            </CardHeader>

            <CardContent className="space-y-6">
              {/* Preferências */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2 md:col-span-2">
                  <Label>Foto (Upload)</Label>
                  <Input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handlePickAvatar}
                    disabled={loading || saving}
                  />

                  <div className="flex items-center gap-3 pt-2">
                    <div className="h-12 w-12 rounded-full border overflow-hidden bg-muted">
                      {(avatarPreview || form.avatar_url) ? (
                        <img
                          src={avatarPreview || form.avatar_url}
                          alt="Avatar"
                          className="h-full w-full object-cover"
                        />
                      ) : null}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      O preview aparece na hora; para persistir, clique em <b>Salvar</b>.
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="theme">Tema</Label>
                  <select
                    id="theme"
                    value={form.theme}
                    onChange={(e) => {
                      const nextTheme = e.target.value;
                      setForm((s) => ({ ...s, theme: nextTheme }));
                      applyTheme(nextTheme);
                    }}
                    disabled={loading || saving}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                  >
                    <option value="light">Claro</option>
                    <option value="dark">Escuro</option>
                    <option value="system">Sistema</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    “Sistema” segue a preferência do seu SO/navegador.
                  </p>
                </div>
              </div>

              <Separator />

              {/* Dados */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">Nome</Label>
                  <Input
                    id="first_name"
                    value={form.first_name}
                    onChange={onChange("first_name")}
                    disabled={loading || saving}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="last_name">Sobrenome</Label>
                  <Input
                    id="last_name"
                    value={form.last_name}
                    onChange={onChange("last_name")}
                    disabled={loading || saving}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input id="email" value={form.email} disabled />
                  <p className="text-xs text-muted-foreground">Email é somente leitura.</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Telefone</Label>
                  <Input
                    id="phone"
                    value={form.phone}
                    onChange={onChange("phone")}
                    disabled={loading || saving}
                    placeholder="(xx) xxxxx-xxxx"
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="location">Localização</Label>
                  <Input
                    id="location"
                    value={form.location}
                    onChange={onChange("location")}
                    disabled={loading || saving}
                    placeholder="Petrópolis - RJ"
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="about">Sobre</Label>
                  <Textarea
                    id="about"
                    value={form.about}
                    onChange={onChange("about")}
                    disabled={loading || saving}
                    rows={5}
                    placeholder="Conte um pouco sobre você e seu objetivo no sistema..."
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSave} disabled={loading || saving} className="gap-2">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Salvar alterações
                </Button>
              </div>

              {!USE_API && (
                <p className="text-xs text-muted-foreground">
                  * Modo UI: salvamento ainda não integrado ao backend. Troque <code>USE_API</code> para{" "}
                  <code>true</code>.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}