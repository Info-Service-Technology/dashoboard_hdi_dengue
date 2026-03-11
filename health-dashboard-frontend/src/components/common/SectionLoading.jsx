import React from "react";

export default function SectionLoading({ message = "Carregando dados..." }) {
  return (
    <div className="w-full rounded-lg border bg-white p-8 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
        <p className="text-sm text-gray-500">{message}</p>
      </div>
    </div>
  );
}