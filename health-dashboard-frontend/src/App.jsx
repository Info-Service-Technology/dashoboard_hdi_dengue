import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import DashboardLayout from './components/Layout/DashboardLayout';
import { Toaster } from "sonner";
import Login from './pages/Login';
import Register from './pages/Register';

import Dashboard from './pages/Dashboard';
import Maps from './pages/Maps';
import Predictions from './pages/Predictions';

// ✅ NOVAS PÁGINAS
import Analytics from './pages/Analytics';
import Data from './pages/Data';
import ProfilePage from './pages/account/ProfilePage';
import SystemSettingsPage from './pages/system/SystemSettingsPage';
import Users from './pages/Users';

import './App.css';

import axios from 'axios';
axios.defaults.baseURL = 'http://localhost:5000';

const PrivatePage = ({ children }) => (
  <PrivateRoute>
    <DashboardLayout>{children}</DashboardLayout>
  </PrivateRoute>
);

const AdminPage = ({ children }) => (
  <PrivateRoute adminOnly>
    <DashboardLayout>{children}</DashboardLayout>
  </PrivateRoute>
);

function App() {
  return (
    <AuthProvider>
      <Toaster richColors position="top-right" />
      <Router>
        <Routes>
          {/* Públicas */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Privadas (menu principal) */}
          <Route path="/dashboard" element={<PrivatePage><Dashboard /></PrivatePage>} />
          <Route path="/analytics" element={<PrivatePage><Analytics /></PrivatePage>} />
          <Route path="/maps" element={<PrivatePage><Maps /></PrivatePage>} />
          <Route path="/data" element={<PrivatePage><Data /></PrivatePage>} />
          <Route path="/predictions" element={<PrivatePage><Predictions /></PrivatePage>} />

          {/* Privada (perfil) */}
          <Route path="/account/profile" element={<PrivatePage><ProfilePage /></PrivatePage>} />

          {/* Admin */}
          <Route path="/admin/users" element={<AdminPage><Users /></AdminPage>} />
          
          <Route path="/admin/system" element={<AdminPage><SystemSettingsPage /></AdminPage>} />

          {/* Default */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* 404 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;