import React from "react";
import DiseaseFilter from "./DiseaseFilter";
import UFSelector from "./UFSelector";
import DateRangeFilter from "./DateRangeFilter";
import GranularityFilter from "./GranularityFilter";

export default function FiltersBar({
  diseaseValue = "all",
  onDiseaseChange,
  diseaseOptions = [],

  ufValue = "all",
  onUFChange,
  ufOptions = [],
  hideUF = false,

  startDate = "",
  endDate = "",
  onStartDateChange,
  onEndDateChange,
  hideDateRange = false,

  granularityValue = "monthly",
  onGranularityChange,
  hideGranularity = false,

  loading = false,
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 bg-white p-3 rounded-lg shadow-sm border">
      <DiseaseFilter
        value={diseaseValue}
        onChange={onDiseaseChange}
        options={diseaseOptions}
        disabled={loading}
      />

      <UFSelector
        value={ufValue}
        onChange={onUFChange}
        options={ufOptions}
        hidden={hideUF}
        disabled={loading}
      />

      {!hideDateRange && (
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={onStartDateChange}
          onEndDateChange={onEndDateChange}
          disabled={loading}
        />
      )}

      {!hideGranularity && (
        <GranularityFilter
          value={granularityValue}
          onChange={onGranularityChange}
          disabled={loading}
        />
      )}
    </div>
  );
}