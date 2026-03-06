// src/services/adminUsersApi.js
import axios from "axios";

export async function fetchAdminUsers() {
  const { data } = await axios.get("/api/admin/users");
  return Array.isArray(data) ? data : [];
}

export async function fetchAdminTenants() {
  const { data } = await axios.get("/api/admin/tenants");
  return Array.isArray(data) ? data : [];
}

export async function createAdminUser(payload) {
  const { data } = await axios.post("/api/admin/users", payload);
  return data;
}

export async function updateAdminUser(userId, payload) {
  const { data } = await axios.put(`/api/admin/users/${userId}`, payload);
  return data;
}

export async function toggleAdminUserActive(userId, is_active) {
  const { data } = await axios.post(`/api/admin/users/${userId}/toggle-active`, { is_active });
  return data;
}

export async function resetAdminUserPassword(userId, password) {
  const { data } = await axios.post(`/api/admin/users/${userId}/reset-password`, { password });
  return data;
}