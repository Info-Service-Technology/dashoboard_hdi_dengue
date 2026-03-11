import React from "react";

export default function UFSelector({
  value = "all",
  onChange,
  options = [],
  disabled = false,
  hidden = false,
}) {
  if (hidden) return null;

  return (
    <div className="flex items-center space-x-2">
      <label className="text-sm font-semibold text-gray-600">UF:</label>

      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className="bg-transparent border rounded px-2 py-1 text-blue-600 font-bold focus:outline-none"
      >
        <option value="all">Todas</option>
        {options.map((uf) => (
          <option key={uf} value={uf}>
            {uf}
          </option>
        ))}
      </select>
    </div>
  );
}