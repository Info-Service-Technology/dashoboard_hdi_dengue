import React from "react";

export default function Analytics() {
  return (
    <div className="p-6">
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <h1 className="text-xl font-semibold text-gray-900">Análises</h1>
        <p className="text-sm text-gray-500 mt-1">
          Área para gráficos, estatísticas e indicadores.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">KPI</div>
            <div className="text-2xl font-semibold mt-1">—</div>
          </div>
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Comparativos</div>
            <div className="text-2xl font-semibold mt-1">—</div>
          </div>
          <div className="rounded-2xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">Tendências</div>
            <div className="text-2xl font-semibold mt-1">—</div>
          </div>
        </div>
      </div>
    </div>
  );
}