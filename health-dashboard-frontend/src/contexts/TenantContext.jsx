import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { useAuth } from "./AuthContext";

const TenantContext = createContext(null);

export const TenantProvider = ({ children }) => {
  const { token, user } = useAuth();

  const [tenant, setTenant] = useState(null);
  const [loadingTenant, setLoadingTenant] = useState(true);
  const [tenantError, setTenantError] = useState("");

  /**
   * Busca o tenant associado ao usuário autenticado
   */
  const fetchTenant = useCallback(async () => {
    if (!token) {
      setTenant(null);
      setTenantError("");
      setLoadingTenant(false);
      return;
    }

    try {
      setLoadingTenant(true);
      setTenantError("");

      const response = await fetch("/api/tenants/me", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Erro ao buscar tenant: ${response.status}`);
      }

      const contentType = response.headers.get("content-type") || "";

      if (!contentType.includes("application/json")) {
        const text = await response.text();
        console.error("Resposta não-JSON:", text.slice(0, 300));
        throw new Error("A resposta de /api/tenants/me não é JSON.");
      }

      const result = await response.json();
      const tenantData = result?.data || null;

      setTenant(tenantData);
    } catch (error) {
      console.error("Erro ao carregar tenant:", error);
      setTenantError("Não foi possível carregar os dados do tenant.");
      setTenant(null);
    } finally {
      setLoadingTenant(false);
    }
  }, [token]);

  useEffect(() => {
    fetchTenant();
  }, [fetchTenant]);

  /**
   * Deriva propriedades úteis do tenant
   */
  const derived = useMemo(() => {
    const scopeType = tenant?.scope_type || null;
    const scopeValue = tenant?.scope_value || null;

    const tenantType =
      scopeType === "MUN"
        ? "municipal"
        : scopeType === "UF"
        ? "state"
        : scopeType === "BR"
        ? "national"
        : null;

    return {
      scopeType,
      scopeValue,
      tenantType,
      isMunicipal: scopeType === "MUN",
      isState: scopeType === "UF",
      isNational: scopeType === "BR",
      isUnit: false,
    };
  }, [tenant]);

  /**
   * Valor exposto para toda a aplicação
   */
  const contextValue = useMemo(
    () => ({
      tenant,
      setTenant,
      refreshTenant: fetchTenant,

      loadingTenant,
      tenantError,

      tenantId: tenant?.tenant_id || null,
      tenantName: tenant?.tenant_name || "Tenant",
      tenantSlug: tenant?.slug || null,
      isActive: tenant?.is_active ?? false,

      scopeType: derived.scopeType,
      scopeValue: derived.scopeValue,
      tenantType: derived.tenantType,

      isMunicipal: derived.isMunicipal,
      isState: derived.isState,
      isNational: derived.isNational,
      isUnit: derived.isUnit,

      municipalityCode:
        derived.scopeType === "MUN" ? derived.scopeValue : null,

      stateCode:
        derived.scopeType === "UF" ? derived.scopeValue : null,

      tokenScopeType: tenant?.token_scope_type || null,
      tokenScopeValue: tenant?.token_scope_value || null,

      user,
    }),
    [tenant, loadingTenant, tenantError, derived, fetchTenant, user]
  );

  return (
    <TenantContext.Provider value={contextValue}>
      {children}
    </TenantContext.Provider>
  );
};

/**
 * Hook de acesso ao contexto
 */
export const useTenant = () => {
  const context = useContext(TenantContext);

  if (!context) {
    throw new Error("useTenant deve ser usado dentro de TenantProvider");
  }

  return context;
};