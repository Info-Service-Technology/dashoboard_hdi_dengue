import React from "react";

export default function DateRangeFilter({
  startDate = "",
  endDate = "",
  onStartDateChange,
  onEndDateChange,
  disabled = false,
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-semibold text-gray-600">Período:</span>

      <input
        type="date"
        value={startDate}
        onChange={(e) => onStartDateChange?.(e.target.value)}
        disabled={disabled}
        className="border rounded px-2 py-1 text-sm"
      />

      <span className="text-sm text-gray-500">até</span>

      <input
        type="date"
        value={endDate}
        onChange={(e) => onEndDateChange?.(e.target.value)}
        disabled={disabled}
        className="border rounded px-2 py-1 text-sm"
      />
    </div>
  );
}