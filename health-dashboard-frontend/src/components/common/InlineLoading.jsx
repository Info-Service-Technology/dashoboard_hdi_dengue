import React from "react";

export default function InlineLoading({ message = "Atualizando..." }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-gray-500">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
      {message}
    </span>
  );
}