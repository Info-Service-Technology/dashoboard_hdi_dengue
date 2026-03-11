import React, { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

const DataExplorer = () => {
  const { token } = useAuth();

  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);

      const response = await fetch("/api/data", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      const result = await response.json();

      setData(result.data || []);
      setLoading(false);
    } catch (err) {
      setError("Erro ao carregar dados.");
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) return <div className="p-6">Carregando dados...</div>;

  if (error) return <div className="p-6 text-red-500">{error}</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Data Explorer</h1>

      <div className="overflow-auto">
        <table className="min-w-full border border-gray-200">
          <thead className="bg-gray-100">
            <tr>
              <th className="p-2 border">Data</th>
              <th className="p-2 border">Doença</th>
              <th className="p-2 border">UF</th>
              <th className="p-2 border">Município</th>
              <th className="p-2 border">Casos</th>
            </tr>
          </thead>

          <tbody>
            {data.map((row, index) => (
              <tr key={index} className="text-center">
                <td className="border p-2">{row.date}</td>
                <td className="border p-2">{row.disease}</td>
                <td className="border p-2">{row.uf}</td>
                <td className="border p-2">{row.city}</td>
                <td className="border p-2">{row.cases}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataExplorer;