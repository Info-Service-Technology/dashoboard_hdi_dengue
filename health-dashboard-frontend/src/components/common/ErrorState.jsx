import React from "react";

export default function ErrorState({ message = "Ocorreu um erro ao carregar os dados." }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <p className="text-sm text-red-700">{message}</p>
    </div>
  );
}