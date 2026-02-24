import React from "react";

export default function Data() {
  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h1 className="text-xl font-semibold text-gray-900">Dados</h1>
        <p className="text-sm text-gray-500 mt-1">
          Explorer para dados brutos (filtros, paginação, exportação).
        </p>

        <div className="mt-6 rounded-2xl border border-dashed border-gray-300 p-6 text-sm text-gray-500">
          Placeholder: aqui você pode colocar uma tabela (DataGrid) com filtros por doença, UF, período etc.
        </div>
      </div>
    </div>
  );
}