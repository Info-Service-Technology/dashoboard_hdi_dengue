// Maps.jsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { MapContainer, TileLayer, Marker, Popup, Tooltip, useMapEvents } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
});

// Tracker de viewport: pega zoom + bbox sempre que mover/zoomear
function MapViewportTracker({ onViewport }) {
  useMapEvents({
    moveend: (e) => {
      const map = e.target;
      const b = map.getBounds();
      onViewport({
        zoom: map.getZoom(),
        bbox: `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`,
      });
    },
    zoomend: (e) => {
      const map = e.target;
      const b = map.getBounds();
      onViewport({
        zoom: map.getZoom(),
        bbox: `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`,
      });
    },
  });
  return null;
}

export default function Maps() {
  const { token } = useAuth();

  const [healthData, setHealthData] = useState([]);
  const [selectedDisease, setSelectedDisease] = useState("all");
  const [selectedUF, setSelectedUF] = useState("all");

  const [loading, setLoading] = useState(false); // <-- NÃO começa true pra não travar
  const [error, setError] = useState("");

  const [viewport, setViewport] = useState({ zoom: 4, bbox: null });
  const level = viewport.zoom < 6 ? "uf" : "municipio";

  const reqSeq = useRef(0);
  const mapRef = useRef(null);

  const getMarkerColor = (disease) => {
    const colors = {
      Dengue: "#ef4444",
      Chikungunya: "#f97316",
      Zika: "#3b82f6",
      Coqueluche: "#a855f7",
      "Rotavírus": "#22c55e",
    };
    return colors[disease] || "#64748b";
  };

  // Ícone pequeno FIXO para UF (não tapa cliques)
  const ufIcon = useCallback((color) => {
    return L.divIcon({
      className: "",
      html: `
        <div style="
          width: 14px;
          height: 14px;
          border-radius: 9999px;
          background: ${color};
          border: 2px solid rgba(255,255,255,0.9);
          box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        "></div>
      `,
      iconSize: [14, 14],
      iconAnchor: [7, 7],
    });
  }, []);

  const fetchHealthData = useCallback(
    async ({ lvl, disease, bbox }) => {
      const mySeq = ++reqSeq.current;

      try {
        setError("");
        setLoading(true);

        if (!token) {
          setHealthData([]);
          return;
        }

        const baseUrl =
          lvl === "uf"
            ? "http://localhost:5000/api/maps/uf"
            : "http://localhost:5000/api/maps";

        const params = new URLSearchParams();
        params.set("disease", disease || "all");
        if (bbox) params.set("bbox", bbox); // bbox opcional

        const response = await fetch(`${baseUrl}?${params.toString()}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (mySeq !== reqSeq.current) return;

        if (response.status === 401) {
          setHealthData([]);
          setError("Não autorizado (token ausente/expirado). Faça login novamente.");
          return;
        }

        if (!response.ok) {
          setHealthData([]);
          setError(`Erro ao buscar mapa (HTTP ${response.status}).`);
          return;
        }

        const data = await response.json();
        setHealthData(Array.isArray(data) ? data : []);
      } catch (e) {
        console.error(e);
        setHealthData([]);
        setError("Erro ao buscar dados do mapa.");
      } finally {
        if (mySeq === reqSeq.current) setLoading(false);
      }
    },
    [token]
  );

  // Faz fetch sempre que mudar nível/doença/bbox, mas:
  // - se bbox ainda não existe, faz fetch SEM bbox (pra não travar)
  useEffect(() => {
    if (!token) {
      setHealthData([]);
      setLoading(false);
      return;
    }

    const t = setTimeout(() => {
      fetchHealthData({
        lvl: level,
        disease: selectedDisease,
        bbox: viewport.bbox || undefined, // fallback sem bbox
      });
    }, 250);

    return () => clearTimeout(t);
  }, [token, level, selectedDisease, viewport.bbox, fetchHealthData]);

  const safeHealthData = Array.isArray(healthData) ? healthData : [];

  const diseases = useMemo(() => {
    return Array.from(new Set(safeHealthData.map((i) => i.disease).filter(Boolean))).sort();
  }, [safeHealthData]);

  const ufs = useMemo(() => {
    return Array.from(new Set(safeHealthData.map((i) => i.state).filter(Boolean))).sort();
  }, [safeHealthData]);

  const filteredData = useMemo(() => {
    let data = safeHealthData;
    if (selectedDisease !== "all") data = data.filter((i) => i.disease === selectedDisease);
    if (selectedUF !== "all") data = data.filter((i) => i.state === selectedUF);
    return data;
  }, [safeHealthData, selectedDisease, selectedUF]);

  // Tabela por UF (na área/dados carregados)
  const table = useMemo(() => {
    const diseaseCols = Array.from(new Set(filteredData.map((i) => i.disease).filter(Boolean))).sort();

    const byUF = new Map();
    for (const item of filteredData) {
      const uf = item.state || "??";
      const dis = item.disease || "N/A";
      const cases = Number(item.cases || 0);

      if (!byUF.has(uf)) byUF.set(uf, { uf, total: 0 });
      const row = byUF.get(uf);

      row[dis] = (row[dis] || 0) + cases;
      row.total += cases;
    }

    const rows = Array.from(byUF.values()).sort((a, b) => (b.total || 0) - (a.total || 0));
    return { diseaseCols, rows };
  }, [filteredData]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900">Análise Geográfica</h1>

        <div className="flex flex-wrap items-center gap-3 bg-white p-2 rounded-lg shadow-sm border">
          <div className="flex items-center space-x-2">
            <label htmlFor="disease-filter" className="text-sm font-semibold text-gray-600">
              Doença:
            </label>
            <select
              id="disease-filter"
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
              className="bg-transparent focus:outline-none text-blue-600 font-bold"
            >
              <option value="all">Todas</option>
              {diseases.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <label htmlFor="uf-filter" className="text-sm font-semibold text-gray-600">
              UF:
            </label>
            <select
              id="uf-filter"
              value={selectedUF}
              onChange={(e) => setSelectedUF(e.target.value)}
              className="bg-transparent focus:outline-none text-blue-600 font-bold"
            >
              <option value="all">Todas</option>
              {ufs.map((uf) => (
                <option key={uf} value={uf}>
                  {uf}
                </option>
              ))}
            </select>
          </div>

          <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
            {level === "uf" ? "Visão UF" : "Visão Municípios"}
          </span>

          {loading && <span className="text-xs text-gray-500">Atualizando…</span>}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 p-3 rounded">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-xl p-4 border border-gray-100">
        <div className="h-[600px] rounded-lg overflow-hidden relative z-0">
          <MapContainer
            center={[-14.235, -51.9253]}
            zoom={4}
            style={{ height: "100%", width: "100%" }}
            whenCreated={(map) => {
              mapRef.current = map;
              // bbox inicial garantido (resolve o travamento)
              const b = map.getBounds();
              setViewport({
                zoom: map.getZoom(),
                bbox: `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`,
              });
            }}
          >
            <MapViewportTracker onViewport={setViewport} />

            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a>'
            />

            {/* UF: marker pequeno fixo + tooltip/popup (sem bolha gigante) */}
            {level === "uf" &&
              filteredData.map((item, idx) => {
                const color = getMarkerColor(item.disease);
                return (
                  <Marker
                    key={`${item.state}-${item.disease}-${idx}`}
                    position={[item.lat, item.lng]}
                    icon={ufIcon(color)}
                  >
                    <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                      <div className="text-xs">
                        <div className="font-bold">{item.state}</div>
                        <div>{item.disease}</div>
                        <div className="font-black">Casos: {item.cases}</div>
                      </div>
                    </Tooltip>

                    <Popup>
                      <div className="min-w-[170px]">
                        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">UF</div>
                        <div className="text-lg font-bold text-gray-900 leading-tight mb-2">{item.state}</div>
                        <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
                          <span className="text-sm text-gray-600">{item.disease}</span>
                          <span className="text-md font-black text-red-600">{item.cases}</span>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}

            {/* Município: cluster */}
            {level === "municipio" && (
              <MarkerClusterGroup
                chunkedLoading
                spiderfyOnMaxZoom
                showCoverageOnHover={false}
                removeOutsideVisibleBounds
                maxClusterRadius={50}
              >
                {filteredData.map((item, idx) => (
                  <Marker key={`${item.state}-${item.city}-${item.disease}-${idx}`} position={[item.lat, item.lng]}>
                    <Popup>
                      <div className="min-w-[170px]">
                        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Município</div>
                        <div className="text-lg font-bold text-gray-900 leading-tight mb-2">
                          {item.city} - {item.state}
                        </div>
                        <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
                          <span className="text-sm text-gray-600">{item.disease}</span>
                          <span className="text-md font-black text-red-600">{item.cases}</span>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                ))}
              </MarkerClusterGroup>
            )}
          </MapContainer>
        </div>

        {/* Tabela por UF */}
        <div className="mt-4 bg-white border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center justify-between">
            <div className="font-bold text-gray-900">Casos por UF</div>
            <div className="text-xs text-gray-600">
              Doença: <span className="font-semibold">{selectedDisease}</span> | UF:{" "}
              <span className="font-semibold">{selectedUF}</span>
            </div>
          </div>

          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="text-left">
                  <th className="px-4 py-2 font-semibold text-gray-700">UF</th>
                  {table.diseaseCols.map((d) => (
                    <th key={d} className="px-4 py-2 font-semibold text-gray-700">
                      {d}
                    </th>
                  ))}
                  <th className="px-4 py-2 font-semibold text-gray-900">Total</th>
                </tr>
              </thead>

              <tbody className="divide-y">
                {table.rows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-3 text-gray-600" colSpan={2 + table.diseaseCols.length}>
                      Sem dados para os filtros atuais.
                    </td>
                  </tr>
                ) : (
                  table.rows.map((row) => (
                    <tr key={row.uf} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-semibold text-gray-900">{row.uf}</td>
                      {table.diseaseCols.map((d) => (
                        <td key={`${row.uf}-${d}`} className="px-4 py-2 text-gray-700">
                          {row[d] ? row[d].toLocaleString("pt-BR") : "0"}
                        </td>
                      ))}
                      <td className="px-4 py-2 font-black text-gray-900">
                        {(row.total || 0).toLocaleString("pt-BR")}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="px-4 py-3 border-t text-xs text-gray-600">
            Dica: dê zoom para alternar UF ↔ Municípios. O bbox limita a consulta ao que está na tela (quando disponível).
          </div>
        </div>
      </div>
    </div>
  );
}