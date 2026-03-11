import React from "react";

const DEFAULT_OPTIONS = [
  { value: "daily", label: "Diária" },
  { value: "weekly", label: "Semanal" },
  { value: "monthly", label: "Mensal" },
];

export default function GranularityFilter({
  value = "monthly",
  onChange,
  options = DEFAULT_OPTIONS,
  disabled = false,
}) {
  return (
    <div className="flex items-center space-x-2">
      <label className="text-sm font-semibold text-gray-600">Granularidade:</label>

      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className="bg-transparent border rounded px-2 py-1 text-blue-600 font-bold focus:outline-none"
      >
        {options.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  );
}