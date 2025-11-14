import { useState, useEffect } from 'react';

interface FunctionSummary {
  summary: {
    total_functions: number;
    total_relays: number;
    total_models: number;
    unique_function_codes: number;
  };
  functions_by_code: Array<{
    code: string;
    description: string;
    relay_count: number;
    percentage: number;
  }>;
  functions_by_model: Array<{
    model: string;
    function_count: number;
  }>;
}

interface RelayFunction {
  id: number;
  relay_file: string;
  relay_model: string;
  function_code: string;
  function_description: string;
  detection_method: string;
  detection_timestamp: string;
}

const ActiveFunctions: React.FC = () => {
  const [summary, setSummary] = useState<FunctionSummary | null>(null);
  const [selectedRelay, setSelectedRelay] = useState<string>('');
  const [relayFunctions, setRelayFunctions] = useState<RelayFunction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Carregar resumo ao montar componente
  useEffect(() => {
    fetchSummary();
  }, []);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/v1/active-functions/summary');
      const data = await response.json();
      setSummary(data);
      setError('');
    } catch (err) {
      setError('Erro ao carregar resumo de funções ativas');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const searchRelayFunctions = async () => {
    if (!selectedRelay.trim()) {
      setError('Digite um ID de relé para buscar');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `http://localhost:8000/api/v1/relays/${encodeURIComponent(selectedRelay)}/active-functions`
      );
      
      if (!response.ok) {
        throw new Error('Relé não encontrado ou sem funções ativas');
      }
      
      const data = await response.json();
      setRelayFunctions(data.functions);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar funções do relé');
      setRelayFunctions([]);
    } finally {
      setLoading(false);
    }
  };

  const getFunctionColor = (code: string): string => {
    const colors: Record<string, string> = {
      '50/51': 'bg-blue-500',
      '50N/51N': 'bg-green-500',
      '27': 'bg-yellow-500',
      '59': 'bg-orange-500',
      '59N': 'bg-red-500',
    };
    return colors[code] || 'bg-gray-500';
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-white text-xl">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-blue-700 rounded-lg p-6 shadow-lg">
        <h1 className="text-3xl font-bold text-white mb-2">
          ⚡ Funções de Proteção Ativas
        </h1>
        <p className="text-blue-100">
          Visualização em tempo real das funções de proteção detectadas nos relés
        </p>
      </div>

      {/* Estatísticas Gerais */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-1">Total de Funções</div>
            <div className="text-3xl font-bold text-white">
              {summary.summary.total_functions}
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-1">Relés com Funções</div>
            <div className="text-3xl font-bold text-blue-400">
              {summary.summary.total_relays}
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-1">Modelos Diferentes</div>
            <div className="text-3xl font-bold text-green-400">
              {summary.summary.total_models}
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="text-gray-400 text-sm mb-1">Códigos ANSI Únicos</div>
            <div className="text-3xl font-bold text-purple-400">
              {summary.summary.unique_function_codes}
            </div>
          </div>
        </div>
      )}

      {/* Busca por Relé */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-bold text-white mb-4">
          🔍 Buscar Funções de um Relé Específico
        </h2>
        
        <div className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Digite ID do relé (ex: 00-MF-12, Tela 05)"
            value={selectedRelay}
            onChange={(e) => setSelectedRelay(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchRelayFunctions()}
            className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
          />
          <button
            onClick={searchRelayFunctions}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>

        {error && (
          <div className="bg-red-900/50 border border-red-700 text-red-200 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {relayFunctions.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-white mb-3">
              Funções encontradas: {relayFunctions.length}
            </h3>
            <div className="space-y-2">
              {relayFunctions.map((func) => (
                <div
                  key={func.id}
                  className="bg-gray-700 rounded-lg p-4 border border-gray-600 hover:border-blue-500 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={`${getFunctionColor(func.function_code)} text-white px-3 py-1 rounded-full text-sm font-bold`}>
                        {func.function_code}
                      </span>
                      <div>
                        <div className="text-white font-medium">{func.function_description}</div>
                        <div className="text-gray-400 text-sm">
                          Modelo: {func.relay_model} | Método: {func.detection_method}
                        </div>
                      </div>
                    </div>
                    <div className="text-gray-400 text-sm">
                      {new Date(func.detection_timestamp).toLocaleDateString('pt-BR')}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Distribuição por Código ANSI */}
      {summary && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">
            📊 Distribuição por Código ANSI
          </h2>
          <div className="space-y-3">
            {summary.functions_by_code.map((func) => (
              <div key={func.code} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300 font-medium">
                    <span className={`${getFunctionColor(func.code)} text-white px-2 py-0.5 rounded text-xs font-bold mr-2`}>
                      {func.code}
                    </span>
                    {func.description}
                  </span>
                  <span className="text-gray-400">
                    {func.relay_count} relés ({func.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className={`${getFunctionColor(func.code)} h-2 rounded-full transition-all duration-500`}
                    style={{ width: `${func.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Distribuição por Modelo */}
      {summary && (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">
            🏭 Distribuição por Modelo de Relé
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {summary.functions_by_model.map((model) => (
              <div
                key={model.model}
                className="bg-gray-700 rounded-lg p-4 border border-gray-600"
              >
                <div className="text-blue-400 font-medium mb-1">{model.model}</div>
                <div className="text-2xl font-bold text-white">
                  {model.function_count}
                  <span className="text-sm text-gray-400 ml-2">funções</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ActiveFunctions;
