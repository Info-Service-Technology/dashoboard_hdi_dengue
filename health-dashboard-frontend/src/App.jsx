import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import DashboardLayout from './components/Layout/DashboardLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Maps from './pages/Maps';
import Predictions from './pages/Predictions';
import './App.css';

// Configurar axios base URL
import axios from 'axios';
// axios.defaults.baseURL = 'https://5000-iza1stnqhyn0nc0f25z37-06379296.manusvm.computer'; // Alterado para a URL pública do sandbox
axios.defaults.baseURL = 'http://localhost:5000'; // URL do backend local para desenvolvimento


function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Rotas públicas */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* Rotas privadas */}
          <Route path="/dashboard" element={
            <PrivateRoute>
              <DashboardLayout>
                <Dashboard />
              </DashboardLayout>
            </PrivateRoute>
          } />
          
          <Route path="/maps" element={
            <PrivateRoute>
              <DashboardLayout>
                <Maps />
              </DashboardLayout>
            </PrivateRoute>
          } />
          
          <Route path="/predictions" element={
            <PrivateRoute>
              <DashboardLayout>
                <Predictions />
              </DashboardLayout>
            </PrivateRoute>
          } />
          
          {/* Rota padrão */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* Rota 404 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

