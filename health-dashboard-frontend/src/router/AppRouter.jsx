import { BrowserRouter, Routes, Route } from "react-router-dom";

import Dashboard from "../pages/Dashboard";
import Analytics from "../pages/Analytics";
import Maps from "../pages/Maps";
import DataExplorer from "../pages/DataExplorer";
import Predictions from "../pages/Predictions";
import Alerts from "../pages/Alerts";
import RiskIndex from "../pages/RiskIndex";
import Users from "../pages/Users";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>

        <Route path="/" element={<Dashboard />} />

        <Route path="/analytics" element={<Analytics />} />

        <Route path="/maps" element={<Maps />} />

        <Route path="/data" element={<DataExplorer />} />

        <Route path="/predictions" element={<Predictions />} />

        <Route path="/alerts" element={<Alerts />} />

        <Route path="/risk-index" element={<RiskIndex />} />

        <Route path="/users" element={<Users />} />

      </Routes>
    </BrowserRouter>
  );
}