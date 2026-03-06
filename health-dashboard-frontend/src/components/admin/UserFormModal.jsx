// src/components/admin/UserFormModal.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";

function normalizeEmail(v) {
  return String(v || "").trim().toLowerCase();
}

export default function UserFormModal({
  open,
  onOpenChange,
  mode, // "create" | "edit"
  tenants, // [{slug,name}]
  initialUser, // null | user obj
  onSubmit, // async(payload)
}) {
  const isCreate = mode === "create";

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("guest");
  const [isActive, setIsActive] = useState(true);
  const [tenantSlugs, setTenantSlugs] = useState(["br"]);
  const [password, setPassword] = useState("");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Carrega dados quando abre / muda initialUser
  useEffect(() => {
    if (!open) return;

    setError("");
    if (!initialUser) {
      setFirstName("");
      setLastName("");
      setEmail("");
      setRole("guest");
      setIsActive(true);
      setTenantSlugs(["br"]);
      setPassword("");
      return;
    }

    setFirstName(initialUser.first_name || "");
    setLastName(initialUser.last_name || "");
    setEmail(initialUser.email || "");
    setRole(initialUser.role || "guest");
    setIsActive(!!initialUser.is_active);

    const initialTenants = Array.isArray(initialUser.tenants) ? initialUser.tenants : [];
    // garante "br" se existir na lista disponível
    const hasBr = initialTenants.includes("br");
    setTenantSlugs(initialTenants.length ? initialTenants : (hasBr ? ["br"] : ["br"]));

    setPassword("");
  }, [open, initialUser]);

  const tenantOptions = useMemo(() => {
    // garante br no topo se existir
    const list = Array.isArray(tenants) ? tenants.slice() : [];
    list.sort((a, b) => {
      if (a.slug === "br") return -1;
      if (b.slug === "br") return 1;
      return String(a.name || a.slug).localeCompare(String(b.name || b.slug));
    });
    return list;
  }, [tenants]);

  const toggleTenant = (slug) => {
    setTenantSlugs((prev) => {
      const set = new Set(prev);
      if (set.has(slug)) set.delete(slug);
      else set.add(slug);

      // Guardrail: sempre pelo menos 1 tenant (recomendo manter br, mas não obrigo)
      if (set.size === 0) set.add("br");

      return Array.from(set);
    });
  };

  const handleSave = async () => {
    setError("");

    const fn = String(firstName || "").trim();
    const ln = String(lastName || "").trim();
    const em = normalizeEmail(email);

    if (!fn || !ln) {
      setError("Nome e sobrenome são obrigatórios.");
      return;
    }
    if (!em || !em.includes("@")) {
      setError("Email inválido.");
      return;
    }
    if (isCreate && String(password || "").length < 6) {
      setError("Senha deve ter pelo menos 6 caracteres.");
      return;
    }

    const payload = {
      first_name: fn,
      last_name: ln,
      email: em,
      role,
      is_active: !!isActive,
      tenant_slugs: tenantSlugs,
    };
    if (isCreate) payload.password = password;

    setSaving(true);
    try {
      await onSubmit(payload);
      onOpenChange(false);
    } catch (e) {
      const msg = e?.response?.data?.error || e?.message || "Erro ao salvar usuário.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{isCreate ? "Novo Usuário" : "Editar Usuário"}</DialogTitle>
          <DialogDescription>
            Configure acesso, tenants e status. (Modo Prefeitura: o escopo do usuário vem do tenant.)
          </DialogDescription>
        </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Nome</Label>
            <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="Ex: Vinicius" />
          </div>
          <div className="space-y-2">
            <Label>Sobrenome</Label>
            <Input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Ex: Lima" />
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label>Email</Label>
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@prefeitura.gov.br"
              disabled={!isCreate} // edit não troca email por padrão
            />
            {!isCreate && (
              <div className="text-xs text-gray-500">
                Email é chave do usuário. Se precisar trocar, fazemos endpoint específico depois.
              </div>
            )}
          </div>

          {isCreate && (
            <div className="space-y-2 sm:col-span-2">
              <Label>Senha</Label>
              <Input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="mínimo 6 caracteres" />
            </div>
          )}

          <div className="space-y-2">
            <Label>Perfil</Label>
            <select
              className="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="guest">guest</option>
              <option value="admin">admin</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label>Status</Label>
            <select
              className="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
              value={isActive ? "1" : "0"}
              onChange={(e) => setIsActive(e.target.value === "1")}
            >
              <option value="1">Ativo</option>
              <option value="0">Inativo</option>
            </select>
          </div>

          <div className="space-y-2 sm:col-span-2">
            <Label>Tenants permitidos</Label>

            <div className="border rounded-lg p-3 max-h-40 overflow-auto space-y-2">
              {tenantOptions.length === 0 ? (
                <div className="text-sm text-gray-600">Nenhum tenant carregado.</div>
              ) : (
                tenantOptions.map((t) => (
                  <label key={t.slug} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={tenantSlugs.includes(t.slug)}
                      onChange={() => toggleTenant(t.slug)}
                    />
                    <span className="font-medium">{t.name}</span>
                    <span className="text-gray-500">({t.slug})</span>
                  </label>
                ))
              )}
            </div>

            <div className="text-xs text-gray-500">
              Usuário só verá no Login os tenants que estiverem marcados aqui.
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}