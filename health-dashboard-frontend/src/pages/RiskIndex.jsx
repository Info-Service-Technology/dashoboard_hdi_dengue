import React, { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const RiskIndex = () => {
  const { token } = useAuth();

  const [riskData, setRiskData] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRiskIndex = async () => {
    try {
      const response = await fetch("/api/risk-index", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const result = await response.json();

      setRiskData(result.data || []);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskIndex();
  }, []);

  if (loading) return <div className="p-6">Calculando índice de risco...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Índice de Risco Epidemiológico</h1>

      <div className="grid gap-4">
        {riskData.map((item) => (
          <div
            key={item.region_code}
            className="border p-4 rounded bg-gray-50"
          >
            <h2 className="font-bold">{item.city}</h2>

            <p>Doença: {item.disease}</p>

            <p className="text-lg font-semibold">
              Risk Score: {item.risk_score}
            </p>

            <p>Nível: {item.risk_level}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RiskIndex;