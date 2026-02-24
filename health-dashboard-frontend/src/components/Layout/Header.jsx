// src/components/layout/Header.jsx  (ajuste o path conforme seu projeto)
import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Menu,
  Search,
  Bell,
  Settings,
  User,
  Shield,
  ChevronDown,
  LogOut,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";

// ✅ Ajuste se seu backend não estiver em localhost:5000
const API_ORIGIN = "http://localhost:5000";

// ✅ garante que /static/... venha do backend (5000), não do Vite (5173)
const normalizeAvatarUrl = (url) => {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/")) return `${API_ORIGIN}${url}`;
  return url;
};

const Header = ({ onMenuClick }) => {
  const navigate = useNavigate();
  const { user, profile, logout, isAdmin } = useAuth();

  // ✅ se a img falhar, cai nas iniciais
  const [avatarError, setAvatarError] = useState(false);

  // ✅ memoiza src correto
  const avatarSrc = useMemo(() => {
    setAvatarError(false); // reseta quando trocar avatar
    return normalizeAvatarUrl(profile?.avatar_url);
  }, [profile?.avatar_url]);

  const initials = useMemo(() => {
    const a = user?.first_name?.[0] || "U";
    const b = user?.last_name?.[0] || "";
    return `${a}${b}`.toUpperCase();
  }, [user?.first_name, user?.last_name]);

  const goProfile = () => navigate("/account/profile");
  const goSystem = () => navigate("/admin/system");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    // ✅ z-50 para ficar acima do mapa e outros layers
    <header className="bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left side */}
        <div className="flex items-center space-x-4">
          {/* Menu button for mobile */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onMenuClick}
            className="lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>

          {/* Search */}
          <div className="hidden md:flex items-center space-x-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Buscar dados, relatórios..."
                className="pl-10 w-64"
              />
            </div>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-4">
          {/* Notifications */}
          <Button variant="ghost" size="sm" className="relative">
            <Bell className="h-5 w-5" />
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs"
            >
              3
            </Badge>
          </Button>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center space-x-2">
                <div className="p-1 bg-gray-100 rounded-full">
                  {isAdmin ? (
                    <Shield className="h-4 w-4 text-blue-600" />
                  ) : (
                    <User className="h-4 w-4 text-gray-600" />
                  )}
                </div>
                <div className="hidden md:block text-left">
                  <div className="text-sm font-medium">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div className="text-xs text-gray-500 capitalize">
                    {user?.role === "admin" ? "Administrador" : "Convidado"}
                  </div>
                </div>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>

            {/* ✅ z-[9999] por segurança contra leaflet panes */}
            <DropdownMenuContent align="end" className="w-56 z-[9999]">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="text-xs text-gray-500">{user?.email}</p>
                  <Badge
                    variant={isAdmin ? "default" : "secondary"}
                    className="w-fit text-xs"
                  >
                    {isAdmin ? "Administrador" : "Convidado"}
                  </Badge>
                </div>
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={goProfile} className="gap-2">
                <div className="h-8 w-8 rounded-full overflow-hidden border bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  {avatarSrc && !avatarError ? (
                    <img
                      src={avatarSrc}
                      alt="Avatar"
                      className="h-full w-full object-cover"
                      onError={() => setAvatarError(true)}
                    />
                  ) : (
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">
                      {initials}
                    </span>
                  )}
                </div>
                <span>Perfil</span>
              </DropdownMenuItem>

              {/* ✅ Configurações só para admin */}
              {isAdmin && (
                <DropdownMenuItem onClick={goSystem}>
                  <Settings className="mr-2 h-4 w-4" />
                  <span>Sistema</span>
                </DropdownMenuItem>
              )}

              <DropdownMenuSeparator />

              <DropdownMenuItem
                onClick={handleLogout}
                className="text-red-600 focus:text-red-600"
              >
                <LogOut className="mr-2 h-4 w-4" />
                <span>Sair</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
};

export default Header;