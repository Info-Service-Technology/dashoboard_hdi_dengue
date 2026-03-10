// src/contexts/AuthContext.jsx
import { applyTheme } from "@/lib/theme";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import axios from "axios";

const AuthContext = createContext(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de um AuthProvider");
  return ctx;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [tenant, setTenant] = useState(null);

  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) axios.defaults.headers.common.Authorization = `Bearer ${token}`;
    else delete axios.defaults.headers.common.Authorization;
  }, [token]);

  const refreshMe = async () => {
    const { data } = await axios.get("/api/account/me");
    setUser(data.user ?? null);
    setProfile(data.profile ?? null);
    setTenant(data.tenant ?? null);
    applyTheme(data.profile?.theme ?? "light");
    return data;
  };

  useEffect(() => {
    let alive = true;

    const checkAuth = async () => {
      setLoading(true);

      if (!token) {
        setUser(null);
        setProfile(null);
        setTenant(null);
        setLoading(false);
        return;
      }

      try {
        await refreshMe();
      } catch (err) {
        console.error("Token inválido:", err);
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

  const login = async (email, password, tenantSlug = "br") => {
    try {
      const payload = {
        email,
        password,
        tenant_slug: (tenantSlug || "br").trim().toLowerCase(),
      };

      const response = await axios.post("/api/auth/login", payload);
      const { access_token } = response.data;

      setToken(access_token);
      localStorage.setItem("token", access_token);
      axios.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      await refreshMe();
      return { success: true };
    } catch (error) {
      console.error("Erro no login:", error);
      return {
        success: false,
        error: error.response?.data?.error || "Erro no login",
      };
    }
  };

  const register = async (userData) => {
    try {
      const payload = {
        ...userData,
        tenant_slug: (userData?.tenant_slug || "br").trim().toLowerCase(),
      };

      const response = await axios.post("/api/auth/register", payload);
      const { access_token } = response.data;

      setToken(access_token);
      localStorage.setItem("token", access_token);
      axios.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      await refreshMe();
      return { success: true };
    } catch (error) {
      console.error("Erro no registro:", error);
      return {
        success: false,
        error: error.response?.data?.error || "Erro no registro",
      };
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setProfile(null);
    setTenant(null);
    localStorage.removeItem("token");
    delete axios.defaults.headers.common.Authorization;
    applyTheme("light");
  };

  const updateProfile = async (profileData) => {
    try {
      await axios.put("/api/account/me", profileData);
      const me = await refreshMe();
      return { success: true, user: me.user, profile: me.profile, tenant: me.tenant };
    } catch (error) {
      console.error("Erro ao atualizar perfil:", error);
      return {
        success: false,
        error: error.response?.data?.error || "Erro ao atualizar perfil",
      };
    }
  };

  const changePassword = async (currentPassword, newPassword) => {
    try {
      await axios.post("/api/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      return { success: true };
    } catch (error) {
      console.error("Erro ao alterar senha:", error);
      return {
        success: false,
        error: error.response?.data?.error || "Erro ao alterar senha",
      };
    }
  };

  const tenantScope = useMemo(() => {
    const scopeType = (tenant?.scope_type || "BR").toUpperCase();
    const scopeValue = tenant?.scope_value || "all";
    return { scopeType, scopeValue, slug: tenant?.slug || "br" };
  }, [tenant]);

  const value = useMemo(
    () => ({
      user,
      profile,
      tenant,
      tenantScope,
      token,
      loading,
      login,
      register,
      logout,
      updateProfile,
      changePassword,
      refreshMe,
      isAuthenticated: !!token,
      isAdmin: user?.role === "admin",
    }),
    [user, profile, tenant, tenantScope, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};