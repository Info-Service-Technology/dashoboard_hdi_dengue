// src/pages/admin/Users.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, Pencil, Power } from "lucide-react";

import UserFormModal from "@/components/admin/UserFormModal";
import {
  createAdminUser,
  fetchAdminTenants,
  fetchAdminUsers,
  toggleAdminUserActive,
  updateAdminUser,
} from "@/services/adminUsersApi";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [tenants, setTenants] = useState([]);

  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create"); // create|edit
  const [selectedUser, setSelectedUser] = useState(null);

  const load = async () => {
    setError("");
    setLoading(true);
    try {
      const [u, t] = await Promise.all([fetchAdminUsers(), fetchAdminTenants()]);
      setUsers(u);
      setTenants(t);
    } catch (e) {
      setError(e?.response?.data?.error || e?.message || "Erro ao carregar usuários.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const term = String(q || "").trim().toLowerCase();
    if (!term) return users;

    return users.filter((u) => {
      const name = `${u.first_name || ""} ${u.last_name || ""}`.toLowerCase();
      const email = String(u.email || "").toLowerCase();
      return name.includes(term) || email.includes(term);
    });
  }, [users, q]);

  const openCreate = () => {
    setSelectedUser(null);
    setModalMode("create");
    setModalOpen(true);
  };

  const openEdit = (u) => {
    setSelectedUser(u);
    setModalMode("edit");
    setModalOpen(true);
  };

  const onSubmitModal = async (payload) => {
    // payload: {first_name,last_name,email,password?,role,is_active,tenant_slugs}
    if (modalMode === "create") {
      await createAdminUser(payload);
    } else {
      await updateAdminUser(selectedUser.id, {
        first_name: payload.first_name,
        last_name: payload.last_name,
        role: payload.role,
        is_active: payload.is_active,
        tenant_slugs: payload.tenant_slugs,
      });
    }
    await load();
  };

  const onToggleActive = async (u) => {
    setError("");
    try {
      await toggleAdminUserActive(u.id, !u.is_active);
      await load();
    } catch (e) {
      setError(e?.response?.data?.error || e?.message || "Erro ao alterar status.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Gerenciamento de Usuários</h1>
          <p className="text-sm text-gray-600">
            Modo Prefeitura: acesso é controlado por tenants (Brasil + prefeituras).
          </p>
        </div>

        <Button onClick={openCreate} className="gap-2">
          <Plus className="h-4 w-4" />
          Novo Usuário
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <CardTitle className="text-lg">Lista de Usuários</CardTitle>
          <div className="w-full md:w-[420px]">
            <Input
              placeholder="Buscar usuários (nome ou email)..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="text-sm text-gray-600">Carregando...</div>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-gray-600">Nenhum usuário encontrado.</div>
          ) : (
            <div className="overflow-auto border rounded-lg">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr className="text-left">
                    <th className="px-4 py-3 font-semibold text-gray-700">Usuário</th>
                    <th className="px-4 py-3 font-semibold text-gray-700">Email</th>
                    <th className="px-4 py-3 font-semibold text-gray-700">Perfil</th>
                    <th className="px-4 py-3 font-semibold text-gray-700">Status</th>
                    <th className="px-4 py-3 font-semibold text-gray-700">Tenants</th>
                    <th className="px-4 py-3 font-semibold text-gray-700">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filtered.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-gray-900">
                          {u.first_name} {u.last_name}
                        </div>
                        <div className="text-xs text-gray-500">ID: {u.id}</div>
                      </td>

                      <td className="px-4 py-3 text-gray-800">{u.email}</td>

                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold">
                          {u.role}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        {u.is_active ? (
                          <span className="inline-flex px-2 py-1 rounded-full bg-green-50 text-green-700 text-xs font-semibold">
                            Ativo
                          </span>
                        ) : (
                          <span className="inline-flex px-2 py-1 rounded-full bg-red-50 text-red-700 text-xs font-semibold">
                            Inativo
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {(Array.isArray(u.tenants) ? u.tenants : []).slice(0, 3).map((t) => (
                            <span key={t} className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
                              {t}
                            </span>
                          ))}
                          {Array.isArray(u.tenants) && u.tenants.length > 3 && (
                            <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
                              +{u.tenants.length - 3}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Button variant="outline" size="sm" className="gap-2" onClick={() => openEdit(u)}>
                            <Pencil className="h-4 w-4" />
                            Editar
                          </Button>

                          <Button
                            variant={u.is_active ? "destructive" : "default"}
                            size="sm"
                            className="gap-2"
                            onClick={() => onToggleActive(u)}
                          >
                            <Power className="h-4 w-4" />
                            {u.is_active ? "Desativar" : "Ativar"}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <UserFormModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        mode={modalMode}
        tenants={tenants}
        initialUser={selectedUser}
        onSubmit={onSubmitModal}
      />
    </div>
  );
}