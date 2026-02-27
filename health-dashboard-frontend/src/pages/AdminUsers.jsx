// src/pages/AdminUsers.jsx
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "sonner";

function fmt(n) {
  const v = Number(n || 0);
  return v.toLocaleString("pt-BR");
}

function Kpi({ title, value, icon }) {
  return (
    <div className="rounded-2xl border border-gray-200 p-4 bg-white flex items-center justify-between">
      <div>
        <div className="text-sm text-gray-500">{title}</div>
        <div className="text-2xl font-semibold mt-1 text-gray-900">{value}</div>
      </div>
      <div className="text-2xl">{icon}</div>
    </div>
  );
}

function Modal({ open, title, children, onClose }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-lg rounded-2xl bg-white border border-gray-200 shadow-sm">
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="text-sm font-semibold text-gray-900">{title}</div>
          <button
            onClick={onClose}
            className="text-sm px-3 py-1 rounded-lg border border-gray-200 hover:bg-gray-50"
          >
            Fechar
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

export default function AdminUsers() {
  const { token } = useAuth();
  const apiBase = "http://localhost:5000/api";

  const authHeaders = useMemo(() => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, [token]);

  // ⚠️ Ajuste conforme teu backend:
  // GET /api/admin/users -> [ { id, name, email, role, status, created_at, last_login } ]
  // POST /api/admin/users -> cria
  // PATCH /api/admin/users/:id/status -> { active: true/false }
  // DELETE /api/admin/users/:id -> remove
  const listEndpoint = `${apiBase}/admin/users`;

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [users, setUsers] = useState([]);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");

  const [openNew, setOpenNew] = useState(false);
  const [creating, setCreating] = useState(false);

  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("guest"); // admin|guest
  const [newPassword, setNewPassword] = useState("");

  const load = useCallback(async () => {
    if (!token) return;

    setLoading(true);
    setErr("");

    try {
      const res = await fetch(listEndpoint, { headers: authHeaders });
      const ct = res.headers.get("content-type") || "";

      if (!res.ok) {
        const body = ct.includes("application/json") ? await res.json() : null;
        setUsers([]);
        setErr(body?.error || `Falha ao carregar usuários (HTTP ${res.status}).`);
        return;
      }

      const body = ct.includes("application/json") ? await res.json() : null;
      setUsers(Array.isArray(body) ? body : []);
    } catch (e) {
      console.error(e);
      setUsers([]);
      setErr("Falha ao carregar usuários.");
    } finally {
      setLoading(false);
    }
  }, [token, listEndpoint, authHeaders]);

  useEffect(() => {
    if (!token) return;
    load();
  }, [token, load]);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    return users.filter((u) => {
      const hit =
        !s ||
        String(u.name || "").toLowerCase().includes(s) ||
        String(u.email || "").toLowerCase().includes(s);

      const role = String(u.role || "").toLowerCase();
      const roleOk = roleFilter === "all" ? true : role === roleFilter;

      return hit && roleOk;
    });
  }, [users, search, roleFilter]);

  const stats = useMemo(() => {
    const total = users.length;
    const admins = users.filter((u) => String(u.role).toLowerCase() === "admin").length;
    const active = users.filter((u) => (u.active ?? u.status) === true || String(u.status).toLowerCase() === "ativo").length;
    const inactive = total - active;
    return { total, admins, active, inactive };
  }, [users]);

  const toggleStatus = useCallback(
    async (u) => {
      if (!token) return;

      const current =
        (u.active ?? u.status) === true || String(u.status).toLowerCase() === "ativo";
      const next = !current;

      try {
        // PATCH /api/admin/users/:id/status
        const res = await fetch(`${listEndpoint}/${u.id}/status`, {
          method: "PATCH",
          headers: { ...authHeaders, "Content-Type": "application/json" },
          body: JSON.stringify({ active: next }),
        });

        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          const body = ct.includes("application/json") ? await res.json() : null;
          throw new Error(body?.error || `Falha ao atualizar status (HTTP ${res.status}).`);
        }

        toast.success(next ? "Usuário ativado." : "Usuário desativado.");
        load();
      } catch (e) {
        console.error(e);
        toast.error(e?.message || "Erro ao atualizar status.");
      }
    },
    [token, listEndpoint, authHeaders, load]
  );

  const removeUser = useCallback(
    async (u) => {
      if (!token) return;

      try {
        const res = await fetch(`${listEndpoint}/${u.id}`, {
          method: "DELETE",
          headers: authHeaders,
        });

        if (!res.ok) {
          const ct = res.headers.get("content-type") || "";
          const body = ct.includes("application/json") ? await res.json() : null;
          throw new Error(body?.error || `Falha ao remover (HTTP ${res.status}).`);
        }

        toast.success("Usuário removido.");
        load();
      } catch (e) {
        console.error(e);
        toast.error(e?.message || "Erro ao remover usuário.");
      }
    },
    [token, listEndpoint, authHeaders, load]
  );

  const createUser = useCallback(async () => {
    if (!token) return;

    if (!newName.trim() || !newEmail.trim() || !newPassword.trim()) {
      toast.error("Preencha nome, email e senha.");
      return;
    }

    setCreating(true);
    try {
      const res = await fetch(listEndpoint, {
        method: "POST",
        headers: { ...authHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName.trim(),
          email: newEmail.trim(),
          role: newRole,
          password: newPassword,
        }),
      });

      if (!res.ok) {
        const ct = res.headers.get("content-type") || "";
        const body = ct.includes("application/json") ? await res.json() : null;
        throw new Error(body?.error || `Falha ao criar (HTTP ${res.status}).`);
      }

      toast.success("Usuário criado.");
      setOpenNew(false);
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      setNewRole("guest");
      load();
    } catch (e) {
      console.error(e);
      toast.error(e?.message || "Erro ao criar usuário.");
    } finally {
      setCreating(false);
    }
  }, [token, listEndpoint, authHeaders, newName, newEmail, newPassword, newRole, load]);

  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Gerenciamento de Usuários</h1>
            <p className="text-sm text-gray-500 mt-1">Administração de acessos e perfis.</p>
          </div>

          <button
            onClick={() => setOpenNew(true)}
            className="text-sm bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700"
          >
            + Novo Usuário
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <Kpi title="Total de Usuários" value={fmt(stats.total)} icon="👥" />
          <Kpi title="Administradores" value={fmt(stats.admins)} icon="🛡️" />
          <Kpi title="Usuários Ativos" value={fmt(stats.active)} icon="✅" />
          <Kpi title="Usuários Inativos" value={fmt(stats.inactive)} icon="⛔" />
        </div>

        <div className="mt-6 flex flex-col md:flex-row md:items-center gap-3">
          <div className="flex-1">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar usuários..."
              className="w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-gray-600">Perfil</label>
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="text-sm bg-white border border-gray-200 rounded-lg px-2 py-2"
            >
              <option value="all">Todos</option>
              <option value="admin">Administrador</option>
              <option value="guest">Convidado</option>
            </select>
          </div>

          {loading && <div className="text-xs text-gray-500">Atualizando…</div>}
        </div>

        {err && (
          <div className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-2">
            {err}
          </div>
        )}

        <div className="mt-6 rounded-2xl border border-gray-200 overflow-hidden">
          <div className="p-4 bg-gray-50 border-b border-gray-200 text-sm font-semibold text-gray-900">
            Lista de Usuários
          </div>

          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-white sticky top-0">
                <tr className="text-left text-gray-600 border-b border-gray-200">
                  <th className="px-4 py-3">Usuário</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">Perfil</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Último login</th>
                  <th className="px-4 py-3">Ações</th>
                </tr>
              </thead>

              <tbody className="bg-white">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-gray-500">Carregando…</td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-gray-500">Sem usuários.</td>
                  </tr>
                ) : (
                  filtered.map((u) => {
                    const role = String(u.role || "guest").toLowerCase();
                    const isActive =
                      (u.active ?? u.status) === true || String(u.status).toLowerCase() === "ativo";

                    return (
                      <tr key={u.id} className="border-b border-gray-100">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-gray-900">{u.name || "—"}</div>
                          <div className="text-xs text-gray-500">
                            Criado em {u.created_at || "—"}
                          </div>
                        </td>

                        <td className="px-4 py-3 text-gray-900">{u.email || "—"}</td>

                        <td className="px-4 py-3">
                          <span
                            className={`text-xs px-2 py-1 rounded-full border ${
                              role === "admin"
                                ? "bg-blue-50 border-blue-100 text-blue-700"
                                : "bg-gray-50 border-gray-200 text-gray-700"
                            }`}
                          >
                            {role === "admin" ? "Administrador" : "Convidado"}
                          </span>
                        </td>

                        <td className="px-4 py-3">
                          <span
                            className={`text-xs px-2 py-1 rounded-full border ${
                              isActive
                                ? "bg-green-50 border-green-100 text-green-700"
                                : "bg-red-50 border-red-100 text-red-700"
                            }`}
                          >
                            {isActive ? "Ativo" : "Inativo"}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-gray-700">{u.last_login || "—"}</td>

                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => toggleStatus(u)}
                              className="text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
                            >
                              {isActive ? "Desativar" : "Ativar"}
                            </button>
                            <button
                              onClick={() => removeUser(u)}
                              className="text-xs px-3 py-2 rounded-lg border border-red-200 text-red-700 hover:bg-red-50"
                            >
                              Remover
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 text-xs text-gray-500">
          Endpoint atual: <span className="font-semibold">{listEndpoint}</span> (ajuste se necessário)
        </div>
      </div>

      <Modal open={openNew} title="Novo Usuário" onClose={() => setOpenNew(false)}>
        <div className="grid grid-cols-1 gap-3">
          <div>
            <label className="text-xs font-semibold text-gray-600">Nome</label>
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="mt-1 w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
              placeholder="Ex.: João Silva"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-gray-600">Email</label>
            <input
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="mt-1 w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
              placeholder="joao@saude.gov.br"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-gray-600">Perfil</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="mt-1 w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
              >
                <option value="admin">Administrador</option>
                <option value="guest">Convidado</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-600">Senha</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1 w-full text-sm bg-white border border-gray-200 rounded-lg px-3 py-2"
                placeholder="********"
              />
            </div>
          </div>

          <button
            onClick={createUser}
            disabled={creating}
            className="mt-2 text-sm bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-60"
          >
            {creating ? "Criando…" : "Criar usuário"}
          </button>

          <div className="text-xs text-gray-500">
            Se teu backend ainda não tiver esses endpoints, a UI está pronta — depois só plugamos o contrato.
          </div>
        </div>
      </Modal>
    </div>
  );
}