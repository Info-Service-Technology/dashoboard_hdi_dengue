import React, { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const Alerts = () => {
  const { token } = useAuth();

  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    try {
      const response = await fetch("/api/alerts", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const result = await response.json();

      setAlerts(result.data || []);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  if (loading) return <div className="p-6">Carregando alertas...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Alertas Epidemiológicos</h1>

      {alerts.length === 0 && (
        <div className="text-gray-500">
          Nenhum alerta epidemiológico no momento.
        </div>
      )}

      <div className="grid gap-4">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className="border p-4 rounded bg-yellow-50 border-yellow-300"
          >
            <h2 className="font-bold">{alert.disease}</h2>

            <p>Município: {alert.city}</p>

            <p>Casos atuais: {alert.current_cases}</p>

            <p>Esperado: {alert.expected_cases}</p>

            <p className="text-red-600 font-semibold">
              Nível: {alert.alert_level}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Alerts;