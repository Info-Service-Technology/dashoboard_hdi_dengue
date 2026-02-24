import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { 
  Activity, 
  BarChart3, 
  Map, 
  Users, 
  Settings, 
  LogOut,
  Home,
  TrendingUp,
  Database,
  Shield,
  User
} from 'lucide-react';

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();

  const menuItems = [
    {
      title: 'Dashboard',
      icon: Home,
      path: '/dashboard',
      description: 'Visão geral dos dados'
    },
    {
      title: 'Análises',
      icon: BarChart3,
      path: '/analytics',
      description: 'Gráficos e estatísticas'
    },
    {
      title: 'Mapas',
      icon: Map,
      path: '/maps',
      description: 'Visualização geográfica'
    },
    {
      title: 'Dados',
      icon: Database,
      path: '/data',
      description: 'Explorar dados brutos'
    },
    {
      title: 'Predições',
      icon: TrendingUp,
      path: '/predictions',
      description: 'Análise preditiva'
    }
  ];

  const adminItems = [
    {
      title: 'Usuários',
      icon: Users,
      path: '/admin/users',
      description: 'Gerenciar usuários'
    },
    {
      title: 'Sistema',
      icon: Settings,
      path: '/admin/system',
      description: 'Configurações'
    }
  ];

  const isActive = (path) =>
  location.pathname === path || location.pathname.startsWith(path + '/');
  const handleLogout = () => {
    logout();
    onClose?.();
  };

  return (
    <>
      {/* Overlay para mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed top-0 left-0 h-full w-64 bg-white border-r border-gray-200 z-50 transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0 lg:static lg:z-auto
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  Dashboard Saúde
                </h1>
                <p className="text-xs text-gray-500">Análise Preditiva</p>
              </div>
            </div>
          </div>

          {/* User Info */}
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gray-100 rounded-full">
                {isAdmin ? (
                  <Shield className="h-4 w-4 text-blue-600" />
                ) : (
                  <User className="h-4 w-4 text-gray-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-gray-500 capitalize">
                  {user?.role === 'admin' ? 'Administrador' : 'Convidado'}
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2">
                Principal
              </p>
              {menuItems.map((item) => {
                const Icon = item.icon;
                return (
                  {
                    title: 'Perfil',
                    icon: User,
                    path: '/account/profile',
                    description: 'Minha conta'
                  },
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={onClose}
                    className={`
                      flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition-colors
                      ${isActive(item.path)
                        ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                      }
                    `}
                  >
                    <Icon className="h-5 w-5" />
                    <div className="flex-1">
                      <div className="font-medium">{item.title}</div>
                      <div className="text-xs text-gray-400">{item.description}</div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Admin Section */}
            {isAdmin && (
              <div className="space-y-1 pt-4">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-2">
                  Administração
                </p>
                {adminItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={onClose}
                      className={`
                        flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition-colors
                        ${isActive(item.path)
                          ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-600'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                        }
                      `}
                    >
                      <Icon className="h-5 w-5" />
                      <div className="flex-1">
                        <div className="font-medium">{item.title}</div>
                        <div className="text-xs text-gray-400">{item.description}</div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <Button
              variant="ghost"
              onClick={handleLogout}
              className="w-full justify-start text-gray-600 hover:text-red-600 hover:bg-red-50"
            >
              <LogOut className="h-4 w-4 mr-3" />
              Sair
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Sidebar;

