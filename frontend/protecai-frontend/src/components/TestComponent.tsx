import React, { useState, useEffect } from 'react';
import { 
  CheckCircleIcon, 
  XCircleIcon,
  ArrowPathIcon,
  ServerIcon,
  CircleStackIcon,
  CodeBracketIcon,
  CpuChipIcon
} from '@heroicons/react/24/solid';

const TestComponent: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState({
    backend: { status: 'checking', message: '' },
    postgres: { status: 'checking', message: '' },
    apis: { status: 'checking', count: 0 },
    equipments: { status: 'checking', count: 0 }
  });
  const [testing, setTesting] = useState(false);

  const runSystemTests = async () => {
    setTesting(true);
    
    // Test 1: Backend Health
    try {
      const backendRes = await fetch('http://localhost:8000/health');
      if (backendRes.ok) {
        setSystemStatus(prev => ({ ...prev, backend: { status: 'success', message: 'Backend online' }}));
      } else {
        setSystemStatus(prev => ({ ...prev, backend: { status: 'error', message: 'Backend error' }}));
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, backend: { status: 'error', message: 'Backend offline' }}));
    }

    // Test 2: PostgreSQL via Equipment API
    try {
      const pgRes = await fetch('http://localhost:8000/api/v1/equipments/');
      if (pgRes.ok) {
        const data = await pgRes.json();
        setSystemStatus(prev => ({ 
          ...prev, 
          postgres: { status: 'success', message: 'PostgreSQL conectado' },
          equipments: { status: 'success', count: data.total || 0 }
        }));
      } else {
        setSystemStatus(prev => ({ ...prev, postgres: { status: 'error', message: 'PostgreSQL error' }}));
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, postgres: { status: 'error', message: 'PostgreSQL offline' }}));
    }

    // Test 3: OpenAPI Endpoints
    try {
      const openAPIRes = await fetch('http://localhost:8000/openapi.json');
      if (openAPIRes.ok) {
        const openapi = await openAPIRes.json();
        const endpointCount = Object.keys(openapi.paths || {}).length;
        setSystemStatus(prev => ({ ...prev, apis: { status: 'success', count: endpointCount }}));
      } else {
        setSystemStatus(prev => ({ ...prev, apis: { status: 'error', count: 0 }}));
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, apis: { status: 'error', count: 0 }}));
    }

    setTesting(false);
  };

  useEffect(() => {
    runSystemTests();
  }, []);

  const getStatusIcon = (status: string) => {
    if (status === 'checking') return <ArrowPathIcon className="h-6 w-6 text-yellow-500 animate-spin" />;
    if (status === 'success') return <CheckCircleIcon className="h-6 w-6 text-green-500" />;
    return <XCircleIcon className="h-6 w-6 text-red-500" />;
  };

  const getStatusBg = (status: string) => {
    if (status === 'checking') return 'bg-yellow-50 border-yellow-200';
    if (status === 'success') return 'bg-green-50 border-green-200';
    return 'bg-red-50 border-red-200';
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-2">
              🧪 ProtecAI - System Test
            </h1>
            <p className="text-gray-400 mt-1">
              Validação completa de todos os componentes do sistema
            </p>
          </div>
          <button
            onClick={runSystemTests}
            disabled={testing}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            {testing && <ArrowPathIcon className="h-5 w-5 animate-spin" />}
            {testing ? 'Testando...' : 'Executar Testes'}
          </button>
        </div>
      </div>

      {/* Test Results Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Backend Test */}
        <div className={`bg-white border-2 rounded-lg p-6 ${getStatusBg(systemStatus.backend.status)}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <ServerIcon className="h-8 w-8 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">FastAPI Backend</h3>
                <p className="text-gray-600 text-sm">http://localhost:8000</p>
              </div>
            </div>
            {getStatusIcon(systemStatus.backend.status)}
          </div>
          <div className="text-gray-700">
            <strong>Status:</strong> {systemStatus.backend.message}
          </div>
        </div>

        {/* PostgreSQL Test */}
        <div className={`bg-white border-2 rounded-lg p-6 ${getStatusBg(systemStatus.postgres.status)}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <CircleStackIcon className="h-8 w-8 text-blue-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">PostgreSQL Database</h3>
                <p className="text-gray-600 text-sm">protecai_db</p>
              </div>
            </div>
            {getStatusIcon(systemStatus.postgres.status)}
          </div>
          <div className="text-gray-700">
            <strong>Status:</strong> {systemStatus.postgres.message}
          </div>
        </div>

        {/* APIs Test */}
        <div className={`bg-white border-2 rounded-lg p-6 ${getStatusBg(systemStatus.apis.status)}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <CodeBracketIcon className="h-8 w-8 text-indigo-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">REST APIs</h3>
                <p className="text-gray-600 text-sm">OpenAPI 3.0</p>
              </div>
            </div>
            {getStatusIcon(systemStatus.apis.status)}
          </div>
          <div className="text-gray-700">
            <strong>Endpoints:</strong> {systemStatus.apis.count} confirmados
          </div>
        </div>

        {/* Equipments Test */}
        <div className={`bg-white border-2 rounded-lg p-6 ${getStatusBg(systemStatus.equipments.status)}`}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <CpuChipIcon className="h-8 w-8 text-green-600" />
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Relay Equipment</h3>
                <p className="text-gray-600 text-sm">Dados reais</p>
              </div>
            </div>
            {getStatusIcon(systemStatus.equipments.status)}
          </div>
          <div className="text-gray-700">
            <strong>Equipamentos:</strong> {systemStatus.equipments.count} carregados
          </div>
        </div>
      </div>

      {/* Tech Stack */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">
          📦 Stack Tecnológico
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">React 19.1.1</div>
            <div className="text-gray-400 text-sm">Frontend</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">TypeScript 5.9</div>
            <div className="text-gray-400 text-sm">Type Safety</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">Vite 7.1</div>
            <div className="text-gray-400 text-sm">Build Tool</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">Tailwind CSS</div>
            <div className="text-gray-400 text-sm">Styling</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">FastAPI</div>
            <div className="text-gray-400 text-sm">Backend</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">PostgreSQL 16</div>
            <div className="text-gray-400 text-sm">Database</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">SQLAlchemy</div>
            <div className="text-gray-400 text-sm">ORM</div>
          </div>
          <div className="bg-gray-700 px-4 py-3 rounded-lg text-center">
            <div className="text-white font-medium">Docker</div>
            <div className="text-gray-400 text-sm">Container</div>
          </div>
        </div>
      </div>

      {/* System Summary */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-semibold text-white mb-4">
          📊 Resumo do Sistema
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-700 p-4 rounded-lg">
            <div className="text-gray-400 text-sm mb-1">Arquitetura</div>
            <div className="text-white font-semibold">Multi-schema PostgreSQL</div>
          </div>
          <div className="bg-gray-700 p-4 rounded-lg">
            <div className="text-gray-400 text-sm mb-1">Schemas</div>
            <div className="text-white font-semibold">protec_ai, relay_configs, ml_gateway</div>
          </div>
          <div className="bg-gray-700 p-4 rounded-lg">
            <div className="text-gray-400 text-sm mb-1">Qualidade dos Dados</div>
            <div className="text-white font-semibold">100% reais - ZERO MOCKS</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestComponent;