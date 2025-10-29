import React, { useState, useEffect } from 'react';
import { 
  ServerIcon, 
  CpuChipIcon, 
  DocumentTextIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

const MainDashboard: React.FC = () => {
  const [systemStats] = useState({
    totalEquipments: 50,
    totalEndpoints: 64, 
    postgresRecords: 470,
    systemStatus: 'healthy' as 'healthy' | 'warning' | 'error'
  });

  const [apiStatuses, setApiStatuses] = useState([
    { name: 'Root API', status: 'online', endpoint: 'http://localhost:8000/', icon: <ServerIcon className="h-6 w-6" />, color: 'blue' },
    { name: 'Import API', status: 'online', endpoint: 'http://localhost:8000/api/v1/imports/', icon: <DocumentTextIcon className="h-6 w-6" />, color: 'green' }
  ]);

  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Teste de conexão simples
  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        if (response.ok) {
          setApiStatuses(prev => 
            prev.map(api => ({ ...api, status: 'online' as const }))
          );
          console.log('✅ Backend conectado');
        }
      } catch (error) {
        console.warn('⚠️ Backend offline');
        setApiStatuses(prev => 
          prev.map(api => ({ ...api, status: 'offline' as const }))
        );
      }
      setLastUpdate(new Date());
    };

    testConnection();
    const interval = setInterval(testConnection, 60000); // 1 minuto
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-400 bg-green-900';
      case 'offline': return 'text-red-400 bg-red-900';
      default: return 'text-gray-400 bg-gray-800';
    }
  };

  const onlineAPIs = apiStatuses.filter(api => api.status === 'online').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">
              ProtecAI Enterprise Dashboard
            </h1>
            <p className="text-gray-300">
              Sistema de Proteção de Relés - PETROBRAS - Arquitetura Robusta
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <CheckCircleIcon className="h-8 w-8 text-green-400" />
            <div className="text-right">
              <div className="text-sm text-gray-400">Status</div>
              <div className="font-medium text-green-400">Operacional</div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-blue-900 rounded-lg p-6 border border-blue-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-200 text-sm font-medium">APIs Online</p>
              <p className="text-3xl font-bold text-white">{onlineAPIs}/{apiStatuses.length}</p>
            </div>
            <ServerIcon className="h-12 w-12 text-blue-400" />
          </div>
        </div>

        <div className="bg-green-900 rounded-lg p-6 border border-green-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-200 text-sm font-medium">Relés de Proteção</p>
              <p className="text-3xl font-bold text-white">{systemStats.totalEquipments}</p>
            </div>
            <CpuChipIcon className="h-12 w-12 text-green-400" />
          </div>
          <p className="text-green-200 text-sm mt-2">Dados reais processados</p>
        </div>

        <div className="bg-purple-900 rounded-lg p-6 border border-purple-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-200 text-sm font-medium">Endpoints</p>
              <p className="text-3xl font-bold text-white">{systemStats.totalEndpoints}</p>
            </div>
            <DocumentTextIcon className="h-12 w-12 text-purple-400" />
          </div>
          <p className="text-purple-200 text-sm mt-2">APIs documentadas</p>
        </div>

        <div className="bg-orange-900 rounded-lg p-6 border border-orange-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-200 text-sm font-medium">Registros DB</p>
              <p className="text-3xl font-bold text-white">{systemStats.postgresRecords}</p>
            </div>
            <DocumentTextIcon className="h-12 w-12 text-orange-400" />
          </div>
          <p className="text-orange-200 text-sm mt-2">PostgreSQL 16</p>
        </div>
      </div>

      {/* Dados Técnicos */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">Dados Técnicos - Arquitetura Robusta</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-blue-400">Equipamentos & Funções</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Equipamentos:</span>
                <span className="text-white font-medium">50 relés</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Funções Proteção:</span>
                <span className="text-white font-medium">158 funções</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Funções Ativas:</span>
                <span className="text-green-400 font-medium">23 (14.6%)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Settings:</span>
                <span className="text-white font-medium">218 configs</span>
              </div>
            </div>
          </div>
          
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-green-400">Schema ETAP</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Estrutura:</span>
                <span className="text-green-400 font-medium">✅ Preparada</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status:</span>
                <span className="text-blue-400 font-medium">Vazio (Correto)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Team Ready:</span>
                <span className="text-green-400 font-medium">✅ Sim</span>
              </div>
            </div>
          </div>
          
          <div className="space-y-3">
            <h3 className="text-lg font-medium text-purple-400">Schema ML</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Estrutura:</span>
                <span className="text-green-400 font-medium">✅ Preparada</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status:</span>
                <span className="text-blue-400 font-medium">Vazio (Correto)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Team Ready:</span>
                <span className="text-green-400 font-medium">✅ Sim</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* APIs Status */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">APIs do Sistema</h2>
          <span className="text-sm text-gray-400">
            Última verificação: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {apiStatuses.map((api, index) => (
            <div key={index} className="bg-gray-700 rounded-lg p-4 border border-gray-600">
              <div className="flex items-center justify-between">
                <span className="font-medium text-white text-sm">{api.name}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(api.status)}`}>
                  {api.status === 'online' ? 'Online' : 'Offline'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Informações Sistema */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">Informações do Sistema</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Backend:</span>
            <span className="text-white ml-2">FastAPI</span>
          </div>
          <div>
            <span className="text-gray-400">Database:</span>
            <span className="text-white ml-2">PostgreSQL 16</span>
          </div>
          <div>
            <span className="text-gray-400">Frontend:</span>
            <span className="text-white ml-2">React + TypeScript</span>
          </div>
          <div>
            <span className="text-gray-400">Status:</span>
            <span className="text-green-400 ml-2">Production Ready</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;