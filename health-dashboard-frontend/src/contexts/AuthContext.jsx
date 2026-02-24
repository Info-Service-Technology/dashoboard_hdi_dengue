// src/contexts/AuthContext.jsx
import { applyTheme } from '@/lib/theme';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);

  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // ✅ aplica token no axios
  useEffect(() => {
    if (token) axios.defaults.headers.common.Authorization = `Bearer ${token}`;
    else delete axios.defaults.headers.common.Authorization;
  }, [token]);

  // ✅ helper centralizado: busca /me, atualiza user+profile+tema
  const refreshMe = async () => {
    const { data } = await axios.get('/api/account/me');
    setUser(data.user ?? null);
    setProfile(data.profile ?? null);
    applyTheme(data.profile?.theme ?? 'light');
    return data;
  };

  // ✅ checa auth na carga e quando token muda
  useEffect(() => {
    let alive = true;

    const checkAuth = async () => {
      setLoading(true);

      if (!token) {
        setUser(null);
        setProfile(null);
        setLoading(false);
        return;
      }

      try {
        await refreshMe();
      } catch (error) {
        console.error('Token inválido:', error);
        if (alive) logout();
      } finally {
        if (alive) setLoading(false);
      }
    };

    checkAuth();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = async (email, password) => {
    try {
      const response = await axios.post('/api/auth/login', { email, password });
      const { access_token } = response.data;

      setToken(access_token);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      // ✅ já carrega profile + tema
      await refreshMe();

      return { success: true };
    } catch (error) {
      console.error('Erro no login:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Erro no login',
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post('/api/auth/register', userData);
      const { access_token } = response.data;

      setToken(access_token);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      await refreshMe();

      return { success: true };
    } catch (error) {
      console.error('Erro no registro:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Erro no registro',
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setProfile(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common.Authorization;

    // opcional: reseta tema para light
    applyTheme('light');
  };

  const updateProfile = async (profileData) => {
    try {
      await axios.put('/api/account/me', profileData);

      const me = await refreshMe();

      return { success: true, user: me.user, profile: me.profile };
    } catch (error) {
      console.error('Erro ao atualizar perfil:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Erro ao atualizar perfil',
      };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      await axios.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      return { success: true };
    } catch (error) {
      console.error('Erro ao alterar senha:', error);
      return {
        success: false,
        error: error.response?.data?.error || 'Erro ao alterar senha',
      };
    }
  };

  const value = useMemo(
    () => ({
      user,
      profile,
      token,
      loading,
      login,
      register,
      logout,
      updateProfile,
      changePassword,
      refreshMe, // ✅ útil para forçar refresh em páginas específicas
      isAuthenticated: !!token,
      isAdmin: user?.role === 'admin',
    }),
    [user, profile, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};