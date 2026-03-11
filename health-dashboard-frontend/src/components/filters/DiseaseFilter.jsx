import React from "react";

export default function DiseaseFilter({
  value = "all",
  onChange,
  options = [],
  label = "Doença",
  disabled = false,
}) {
  return (
    <div className="flex items-center space-x-2">
      <label className="text-sm font-semibold text-gray-600">{label}:</label>

      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className="bg-transparent border rounded px-2 py-1 text-blue-600 font-bold focus:outline-none"
      >
        <option value="all">Todas</option>
        {options.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
    </div>
  );
}