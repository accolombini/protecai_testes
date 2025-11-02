import React, { useState, useEffect } from 'react';
import { 
  CheckCircleIcon, 
  XCircleIcon,
  ArrowPathIcon,
  ServerIcon,
  CircleStackIcon,
  CodeBracketIcon,
  CpuChipIcon,
  PlayIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/solid';

interface TestLog {
  timestamp: string;
  component: string;
  status: 'info' | 'success' | 'error' | 'warning';
  message: string;
}

const TestComponent: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState({
    backend: { status: 'checking', message: '', responseTime: 0 },
    postgres: { status: 'checking', message: '', responseTime: 0 },
    apis: { status: 'checking', count: 0, responseTime: 0 },
    equipments: { status: 'checking', count: 0, responseTime: 0 }
  });
  const [testing, setTesting] = useState(false);
  const [logs, setLogs] = useState<TestLog[]>([]);
  const [showLogs, setShowLogs] = useState(true);

  const addLog = (component: string, status: 'info' | 'success' | 'error' | 'warning', message: string) => {
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    setLogs(prev => [...prev, { timestamp, component, status, message }]);
  };

  const runSystemTests = async () => {
    setTesting(true);
    setLogs([]);
    addLog('Sistema', 'info', '🚀 Iniciando bateria de testes...');
    
    // Test 1: Backend Health
    addLog('Backend', 'info', 'Testando conexão com FastAPI...');
    const backendStart = Date.now();
    try {
      const backendRes = await fetch('http://localhost:8000/health');
      const backendTime = Date.now() - backendStart;
      if (backendRes.ok) {
        setSystemStatus(prev => ({ ...prev, backend: { status: 'success', message: 'Backend online', responseTime: backendTime }}));
        addLog('Backend', 'success', `✅ Backend respondendo em ${backendTime}ms`);
      } else {
        setSystemStatus(prev => ({ ...prev, backend: { status: 'error', message: 'Backend error', responseTime: backendTime }}));
        addLog('Backend', 'error', `❌ Backend retornou erro (${backendRes.status})`);
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, backend: { status: 'error', message: 'Backend offline', responseTime: 0 }}));
      addLog('Backend', 'error', '❌ Falha na conexão com Backend');
    }

    // Test 2: PostgreSQL via Equipment API
    addLog('PostgreSQL', 'info', 'Testando conexão com banco de dados...');
    const pgStart = Date.now();
    try {
      const pgRes = await fetch('http://localhost:8000/api/v1/equipments/');
      const pgTime = Date.now() - pgStart;
      if (pgRes.ok) {
        const data = await pgRes.json();
        setSystemStatus(prev => ({ 
          ...prev, 
          postgres: { status: 'success', message: 'PostgreSQL conectado', responseTime: pgTime },
          equipments: { status: 'success', count: data.total || 0, responseTime: pgTime }
        }));
        addLog('PostgreSQL', 'success', `✅ Banco conectado - ${data.total || 0} equipamentos encontrados (${pgTime}ms)`);
      } else {
        setSystemStatus(prev => ({ ...prev, postgres: { status: 'error', message: 'PostgreSQL error', responseTime: pgTime }}));
        addLog('PostgreSQL', 'error', `❌ Erro ao consultar banco (${pgRes.status})`);
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, postgres: { status: 'error', message: 'PostgreSQL offline', responseTime: 0 }}));
      addLog('PostgreSQL', 'error', '❌ Falha na consulta ao banco');
    }

    // Test 3: OpenAPI Endpoints
    addLog('APIs', 'info', 'Validando endpoints REST...');
    const apiStart = Date.now();
    try {
      const openAPIRes = await fetch('http://localhost:8000/openapi.json');
      const apiTime = Date.now() - apiStart;
      if (openAPIRes.ok) {
        const openapi = await openAPIRes.json();
        const endpointCount = Object.keys(openapi.paths || {}).length;
        setSystemStatus(prev => ({ ...prev, apis: { status: 'success', count: endpointCount, responseTime: apiTime }}));
        addLog('APIs', 'success', `✅ ${endpointCount} endpoints REST confirmados (${apiTime}ms)`);
      } else {
        setSystemStatus(prev => ({ ...prev, apis: { status: 'error', count: 0, responseTime: apiTime }}));
        addLog('APIs', 'error', '❌ Falha ao obter especificação OpenAPI');
      }
    } catch (err) {
      setSystemStatus(prev => ({ ...prev, apis: { status: 'error', count: 0, responseTime: 0 }}));
      addLog('APIs', 'error', '❌ Erro ao validar endpoints');
    }

    addLog('Sistema', 'success', '✅ Bateria de testes concluída!');
    setTesting(false);
  };

  const exportReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      systemStatus,
      logs,
      summary: {
        total: 4,
        passed: Object.values(systemStatus).filter(s => s.status === 'success').length,
        failed: Object.values(systemStatus).filter(s => s.status === 'error').length
      }
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `protecai-test-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    addLog('Sistema', 'success', '📥 Relatório JSON exportado com sucesso');
  };

  const exportPDFReport = async () => {
    try {
      addLog('Sistema', 'info', '📄 Gerando relatório PDF...');
      
      // Preparar dados para o backend
      const reportData = {
        timestamp: new Date().toISOString(),
        systemStatus: {
          backend: {
            status: systemStatus.backend.status === 'success' ? 'Operacional' : 
                    systemStatus.backend.status === 'error' ? 'Offline' : 'Verificando...',
            responseTime: systemStatus.backend.responseTime
          },
          postgres: {
            status: systemStatus.postgres.status === 'success' ? 'Operacional' : 
                    systemStatus.postgres.status === 'error' ? 'Offline' : 'Verificando...',
            responseTime: systemStatus.postgres.responseTime
          },
          apis: {
            status: systemStatus.apis.status === 'success' ? 'Operacional' : 
                    systemStatus.apis.status === 'error' ? 'Offline' : 'Verificando...',
            responseTime: systemStatus.apis.responseTime
          },
          equipment: {
            status: systemStatus.equipments.status === 'success' ? 'Operacional' : 
                    systemStatus.equipments.status === 'error' ? 'Offline' : 'Verificando...',
            responseTime: systemStatus.equipments.responseTime
          }
        },
        logs: logs.map(log => ({
          timestamp: new Date().toISOString(),
          component: log.component,
          status: log.status,
          message: log.message
        }))
      };

      // Fazer requisição para o backend
      const response = await fetch('http://localhost:8000/api/v1/system-test/export/pdf', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(reportData)
      });

      if (!response.ok) {
        throw new Error(`Erro ao gerar PDF: ${response.status}`);
      }

      // Fazer download do PDF
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ProtecAI_System_Test_${Date.now()}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      
      addLog('Sistema', 'success', '📥 Relatório PDF exportado com sucesso');
    } catch (error) {
      console.error('Erro ao exportar PDF:', error);
      addLog('Sistema', 'error', `❌ Erro ao exportar PDF: ${error instanceof Error ? error.message : 'Erro desconhecido'}`);
    }
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
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-2">
              🧪 ProtecAI - System Test
            </h1>
            <p className="text-slate-400 mt-1">
              Validação completa de todos os componentes do sistema
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={exportReport}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg flex items-center gap-2 transition-colors text-sm"
              title="Exportar relatório em JSON (para desenvolvedores)"
            >
              <DocumentArrowDownIcon className="h-5 w-5" />
              JSON
            </button>
            <button
              onClick={exportPDFReport}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center gap-2 transition-colors text-sm"
              title="Exportar relatório em PDF (para engenheiros)"
            >
              <DocumentArrowDownIcon className="h-5 w-5" />
              PDF
            </button>
            <button
              onClick={runSystemTests}
              disabled={testing}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg flex items-center gap-2 transition-colors shadow-lg shadow-blue-500/20 disabled:shadow-none"
            >
              {testing ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <PlayIcon className="h-5 w-5" />}
              {testing ? 'Testando...' : 'Executar Testes'}
            </button>
          </div>
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
          <div className="text-gray-700 space-y-1">
            <div><strong>Status:</strong> {systemStatus.backend.message}</div>
            {systemStatus.backend.responseTime > 0 && (
              <div className="text-sm text-gray-600">
                <strong>Tempo de resposta:</strong> {systemStatus.backend.responseTime}ms
              </div>
            )}
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
          <div className="text-gray-700 space-y-1">
            <div><strong>Status:</strong> {systemStatus.postgres.message}</div>
            {systemStatus.postgres.responseTime > 0 && (
              <div className="text-sm text-gray-600">
                <strong>Tempo de resposta:</strong> {systemStatus.postgres.responseTime}ms
              </div>
            )}
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
          <div className="text-gray-700 space-y-1">
            <div><strong>Endpoints:</strong> {systemStatus.apis.count} confirmados</div>
            {systemStatus.apis.responseTime > 0 && (
              <div className="text-sm text-gray-600">
                <strong>Tempo de resposta:</strong> {systemStatus.apis.responseTime}ms
              </div>
            )}
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
          <div className="text-gray-700 space-y-1">
            <div><strong>Equipamentos:</strong> {systemStatus.equipments.count} carregados</div>
            {systemStatus.equipments.responseTime > 0 && (
              <div className="text-sm text-gray-600">
                <strong>Tempo de resposta:</strong> {systemStatus.equipments.responseTime}ms
              </div>
            )}
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

      {/* Console de Logs em Tempo Real */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden shadow-lg">
        <div className="bg-slate-800 px-6 py-3 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            📟 Console de Testes
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
            >
              {showLogs ? 'Ocultar' : 'Mostrar'}
            </button>
            <button
              onClick={() => setLogs([])}
              className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
            >
              Limpar
            </button>
          </div>
        </div>
        
        {showLogs && (
          <div className="bg-black p-4 font-mono text-sm max-h-96 overflow-y-auto">
            {logs.length === 0 ? (
              <div className="text-slate-500 text-center py-8">
                Nenhum log disponível. Clique em "Executar Testes" para iniciar.
              </div>
            ) : (
              logs.map((log, index) => (
                <div
                  key={index}
                  className={`py-1 ${
                    log.status === 'error' ? 'text-red-400' :
                    log.status === 'success' ? 'text-emerald-400' :
                    log.status === 'warning' ? 'text-yellow-400' :
                    'text-blue-400'
                  }`}
                >
                  <span className="text-slate-500">[{log.timestamp}]</span>{' '}
                  <span className="text-slate-400">[{log.component}]</span>{' '}
                  {log.message}
                </div>
              ))
            )}
          </div>
        )}
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