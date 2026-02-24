import React from "react";

export default function AdminUsersPage() {
  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h1 className="text-xl font-semibold text-gray-900">Usuários</h1>
        <p className="text-sm text-gray-500 mt-1">
          Gestão de usuários (admin).
        </p>

        <div className="mt-6 rounded-2xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Placeholder: lista de usuários, ações (editar, reset senha, ativar/desativar).
        </div>
      </div>
    </div>
  );
}