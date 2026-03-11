import React from "react";

export default function EmptyState({ message = "Nenhum dado encontrado." }) {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
      <p className="text-sm text-gray-600">{message}</p>
    </div>
  );
}