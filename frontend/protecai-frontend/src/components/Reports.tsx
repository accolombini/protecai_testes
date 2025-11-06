import React, { useState, useEffect } from 'react';
import {
  DocumentTextIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
  CheckCircleIcon,
  ChartBarIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';

// ===== INTERFACES =====
interface RelayEquipment {
  id: string;
  source: string;
  tag_reference: string;
  serial_number: string;
  plant_reference: string | null;
  bay_position: string;
  status: string;
  description: string;
  model: {
    name: string;
    type: string;
    family: string;
  };
  manufacturer: {
    name: string;
    country: string;
  };
  created_at: string;
}

interface ReportMetadata {
  manufacturers: Array<{ code: string; name: string; count: number }>;
  models: Array<{ code: string; name: string; manufacturer_code: string; count: number }>;
  bays: Array<{ name: string; count: number }>;
  statuses: Array<{ code: string; label: string; count: number }>;
}

interface ReportFilters {
  manufacturer: string;
  status: string;
  model: string;
  busbar: string;  // Mapeia para bay no backend
}

type ReportType = 'overview' | 'all-relays' | 'by-manufacturer' | 'by-status' | 'custom';
type ExportFormat = 'csv' | 'xlsx' | 'pdf';

// ===== COMPONENTE PRINCIPAL =====
const Reports: React.FC = () => {
  // Estados
  const [selectedReport, setSelectedReport] = useState<ReportType>('overview');
  const [equipments, setEquipments] = useState<RelayEquipment[]>([]);
  const [metadata, setMetadata] = useState<ReportMetadata | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  
  const [filters, setFilters] = useState<ReportFilters>({
    manufacturer: '',
    status: '',
    model: '',
    busbar: ''
  });

  // ===== CARREGAMENTO INICIAL =====
  useEffect(() => {
    console.log('📊 INICIALIZANDO MÓDULO DE RELATÓRIOS...');
    loadMetadata();
    loadEquipments();
  }, []);

  // Carregar metadados
  const loadMetadata = async () => {
    try {
      console.log('🔍 Carregando metadados do backend...');
      const response = await fetch('http://localhost:8000/api/v1/reports/metadata');
      
      if (!response.ok) {
        throw new Error(`Erro HTTP: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('✅ Metadados carregados:', data);
      
      // O backend já retorna no formato correto
      setMetadata(data);
    } catch (error) {
      console.error('❌ Erro ao carregar metadados:', error);
    }
  };

  // Carregar equipamentos
  const loadEquipments = async () => {
    setLoading(true);
    try {
      console.log('🔍 Carregando equipamentos...');
      const response = await fetch('http://localhost:8000/api/v1/equipments/?page=1&size=100');
      
      if (!response.ok) {
        throw new Error(`Erro HTTP: ${response.status}`);
      }
      
      const result = await response.json();
      const equipmentData = result.data || [];
      
      console.log(`✅ ${equipmentData.length} equipamentos carregados`);
      setEquipments(equipmentData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('❌ Erro ao carregar equipamentos:', error);
    } finally {
      setLoading(false);
    }
  };

  // ===== FILTROS =====
  const getFilteredData = (): RelayEquipment[] => {
    return equipments.filter(eq => {
      if (filters.manufacturer && !eq.manufacturer.name.toLowerCase().includes(filters.manufacturer.toLowerCase())) {
        return false;
      }
      if (filters.status && eq.status !== filters.status) {
        return false;
      }
      if (filters.model && !eq.model.name.toLowerCase().includes(filters.model.toLowerCase())) {
        return false;
      }
      if (filters.busbar && eq.bay_position !== filters.busbar) {
        return false;
      }
      return true;
    });
  };

  const resetFilters = () => {
    setFilters({
      manufacturer: '',
      status: '',
      model: '',
      busbar: ''
    });
  };

  const activeFiltersCount = Object.values(filters).filter(v => v !== '').length;

  // ===== EXPORTAÇÃO =====
  const handleExport = async (format: ExportFormat, customFilters: Partial<ReportFilters> = {}) => {
    setExportLoading(true);
    try {
      console.log(`📥 Exportando para ${format.toUpperCase()}...`);
      
      // Construir query string
      const params = new URLSearchParams();
      const exportFilters = { ...filters, ...customFilters };
      
      Object.entries(exportFilters).forEach(([key, value]) => {
        if (value) params.append(key, String(value));
      });
      
      const url = `http://localhost:8000/api/v1/reports/export/${format}?${params.toString()}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Erro ao exportar: ${response.status}`);
      }
      
      // Extrair nome do arquivo do header Content-Disposition (case-insensitive)
      let filename = `relatorio_protecai_${new Date().toISOString().split('T')[0]}.${format}`;
      
      // Debug: listar TODOS os headers
      console.log('=== DEBUG: Headers recebidos ===');
      response.headers.forEach((value, key) => {
        console.log(`${key}: ${value}`);
      });
      console.log('================================');
      
      // Tentar ambas as versões do header (case-sensitive e lowercase)
      const contentDisposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
      
      if (contentDisposition) {
        console.log('✅ Content-Disposition header encontrado:', contentDisposition);
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        console.log('🔍 Resultado do regex match:', filenameMatch);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '').trim();
          console.log('✅ Filename final extraído:', filename);
        } else {
          console.error('❌ Regex não conseguiu extrair filename do header');
        }
      } else {
        console.error('❌ Header Content-Disposition NÃO encontrado, usando nome genérico');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      console.log(`✅ Exportação ${format.toUpperCase()} concluída com filename: ${filename}`);
    } catch (error) {
      console.error(`❌ Erro ao exportar ${format}:`, error);
      alert(`Erro ao exportar para ${format.toUpperCase()}`);
    } finally {
      setExportLoading(false);
    }
  };

  // ===== COMPONENTES UI =====
  const ExportButtons: React.FC<{ filterParams?: Partial<ReportFilters> }> = ({ filterParams = {} }) => (
    <div className="flex gap-2">
      <button
        onClick={() => handleExport('csv', filterParams)}
        disabled={exportLoading}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-md flex items-center gap-2 transition-colors"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
        Exportar CSV
      </button>
      <button
        onClick={() => handleExport('xlsx', filterParams)}
        disabled={exportLoading}
        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-md flex items-center gap-2 transition-colors"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
        Exportar Excel
      </button>
      <button
        onClick={() => handleExport('pdf', filterParams)}
        disabled={exportLoading}
        className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-md flex items-center gap-2 transition-colors"
      >
        <ArrowDownTrayIcon className="h-4 w-4" />
        Exportar PDF
      </button>
    </div>
  );

  const filteredData = getFilteredData();

  // ===== RENDERIZAÇÃO =====
  return (
    <div className="space-y-6">
      {/* Header Principal */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">
              Sistema de Relatórios - PETROBRAS
            </h1>
            <p className="text-gray-300">
              Exportação multi-formato de dados de relés de proteção
            </p>
          </div>
          <div className="flex items-center space-x-6">
            <div className="text-right">
              <div className="text-3xl font-bold text-blue-400">{equipments.length}</div>
              <div className="text-sm text-gray-400">Equipamentos Totais</div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-green-400">{filteredData.length}</div>
              <div className="text-sm text-gray-400">Filtrados</div>
            </div>
          </div>
        </div>
      </div>

      {/* 📄 NOVO: Relatório de Setup do Relé */}
      <div className="rounded-lg p-6 border border-blue-600 shadow-lg bg-blue-900">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-600 rounded-lg">
            <DocumentTextIcon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">📄 Relatório de Setup do Relé</h2>
            <p className="text-blue-200 text-sm">Gere relatórios profissionais de configuração de relés específicos</p>
          </div>
        </div>
        
        <div className="bg-blue-950/50 rounded-lg p-4 border border-blue-700">
          <p className="text-blue-100 mb-4">
            ⚙️ Para gerar relatórios de setup de um relé específico, acesse a aba <strong>"⚙️ Setup de Relés"</strong> no menu principal.
          </p>
          <div className="text-sm text-blue-200 space-y-2">
            <div className="flex items-start gap-2">
              <span>✓</span>
              <span>Selecione o relé desejado por TAG ou busca</span>
            </div>
            <div className="flex items-start gap-2">
              <span>✓</span>
              <span>Visualize todas as configurações e parâmetros</span>
            </div>
            <div className="flex items-start gap-2">
              <span>✓</span>
              <span>Gere relatórios em PDF, Excel ou CSV</span>
            </div>
            <div className="flex items-start gap-2">
              <span>✓</span>
              <span>Inclui dados completos: fabricante, modelo, bay, subestação</span>
            </div>
          </div>
        </div>
      </div>

      {/* Seletor de Tipo de Relatório */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-lg font-semibold text-white mb-4">Selecione o Tipo de Relatório</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <button
            onClick={() => setSelectedReport('overview')}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedReport === 'overview'
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-gray-600 hover:border-gray-500'
            }`}
          >
            <ChartBarIcon className="h-6 w-6 text-blue-400 mx-auto mb-2" />
            <div className="text-white font-medium text-sm">Visão Geral</div>
            <div className="text-gray-400 text-xs mt-1">Estatísticas</div>
          </button>

          <button
            onClick={() => setSelectedReport('all-relays')}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedReport === 'all-relays'
                ? 'border-green-500 bg-green-500/10'
                : 'border-gray-600 hover:border-gray-500'
            }`}
          >
            <CpuChipIcon className="h-6 w-6 text-green-400 mx-auto mb-2" />
            <div className="text-white font-medium text-sm">Todos os Relés</div>
            <div className="text-gray-400 text-xs mt-1">{equipments.length} registros</div>
          </button>

          <button
            onClick={() => setSelectedReport('by-manufacturer')}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedReport === 'by-manufacturer'
                ? 'border-purple-500 bg-purple-500/10'
                : 'border-gray-600 hover:border-gray-500'
            }`}
          >
            <FunnelIcon className="h-6 w-6 text-purple-400 mx-auto mb-2" />
            <div className="text-white font-medium text-sm">Por Fabricante</div>
            <div className="text-gray-400 text-xs mt-1">Agrupado</div>
          </button>

          <button
            onClick={() => setSelectedReport('by-status')}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedReport === 'by-status'
                ? 'border-yellow-500 bg-yellow-500/10'
                : 'border-gray-600 hover:border-gray-500'
            }`}
          >
            <CheckCircleIcon className="h-6 w-6 text-yellow-400 mx-auto mb-2" />
            <div className="text-white font-medium text-sm">Por Status</div>
            <div className="text-gray-400 text-xs mt-1">Operacional</div>
          </button>

          <button
            onClick={() => setSelectedReport('custom')}
            className={`p-4 rounded-lg border-2 transition-all ${
              selectedReport === 'custom'
                ? 'border-orange-500 bg-orange-500/10'
                : 'border-gray-600 hover:border-gray-500'
            }`}
          >
            <DocumentTextIcon className="h-6 w-6 text-orange-400 mx-auto mb-2" />
            <div className="text-white font-medium text-sm">Personalizado</div>
            <div className="text-gray-400 text-xs mt-1">{activeFiltersCount} filtros</div>
          </button>
        </div>
      </div>

      {/* TELA: Visão Geral */}
      {selectedReport === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-blue-900 rounded-lg p-6 border border-blue-700">
              <div className="flex items-center justify-between mb-4">
                <CpuChipIcon className="h-8 w-8 text-blue-400" />
                <span className="text-2xl font-bold text-white">{equipments.length}</span>
              </div>
              <h3 className="text-blue-200 font-medium">Total de Equipamentos</h3>
              <p className="text-blue-300 text-sm mt-2">Relés de proteção cadastrados</p>
            </div>

            <div className="bg-green-900 rounded-lg p-6 border border-green-700">
              <div className="flex items-center justify-between mb-4">
                <CheckCircleIcon className="h-8 w-8 text-green-400" />
                <span className="text-2xl font-bold text-white">
                  {equipments.filter(e => e.status === 'ACTIVE').length}
                </span>
              </div>
              <h3 className="text-green-200 font-medium">Equipamentos Ativos</h3>
              <p className="text-green-300 text-sm mt-2">Em operação normal</p>
            </div>

            <div className="bg-purple-900 rounded-lg p-6 border border-purple-700">
              <div className="flex items-center justify-between mb-4">
                <ChartBarIcon className="h-8 w-8 text-purple-400" />
                <span className="text-2xl font-bold text-white">
                  {metadata?.manufacturers.length || 0}
                </span>
              </div>
              <h3 className="text-purple-200 font-medium">Fabricantes</h3>
              <p className="text-purple-300 text-sm mt-2">Diferentes fornecedores</p>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold text-white">Exportar Dados Completos</h2>
              <ExportButtons />
            </div>
            <p className="text-gray-400 text-sm">
              Exporte todos os {equipments.length} equipamentos cadastrados no sistema em formato CSV, Excel ou PDF
            </p>
          </div>
        </div>
      )}

      {/* TELA: Todos os Relés */}
      {selectedReport === 'all-relays' && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-6 border-b border-gray-700">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold text-white mb-1">
                  Relatório Completo de Equipamentos
                </h2>
                <p className="text-sm text-gray-400">
                  {equipments.length} equipamentos • Atualizado em {lastUpdate.toLocaleTimeString('pt-BR')}
                </p>
              </div>
              <ExportButtons />
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Tag</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Serial</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Modelo</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Fabricante</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Barramento</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {equipments.slice(0, 20).map((eq) => (
                  <tr key={eq.id} className="hover:bg-gray-700/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                      {eq.tag_reference}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {eq.serial_number}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-300">
                      {eq.model.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {eq.manufacturer.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {eq.bay_position === 'Unknown' ? 'Desconhecido' : eq.bay_position || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        eq.status === 'ACTIVE' 
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                          : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                      }`}>
                        {eq.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {equipments.length > 20 && (
            <div className="p-4 bg-gray-700/50 text-center">
              <p className="text-sm text-gray-400">
                Mostrando 20 de {equipments.length} equipamentos. Exporte para ver todos os registros.
              </p>
            </div>
          )}
        </div>
      )}

      {/* TELA: Por Fabricante */}
      {selectedReport === 'by-manufacturer' && metadata && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-6 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white mb-4">Relatório por Fabricante</h2>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Selecione o Fabricante
                </label>
                <select
                  value={filters.manufacturer}
                  onChange={(e) => setFilters({ ...filters, manufacturer: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">-- Todos os fabricantes --</option>
                  {metadata.manufacturers.map(mfg => (
                    <option key={mfg.code} value={mfg.name}>
                      {mfg.name} ({mfg.count} equipamentos)
                    </option>
                  ))}
                </select>
              </div>
              <div className="pt-7">
                <ExportButtons filterParams={{ manufacturer: filters.manufacturer }} />
              </div>
            </div>
          </div>
          
          <div className="p-6">
            {filters.manufacturer ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircleIcon className="h-5 w-5" />
                  <span className="font-medium">Fabricante selecionado: {filters.manufacturer}</span>
                </div>
                <div className="text-gray-300">
                  {filteredData.length} equipamento(s) encontrado(s)
                </div>
              </div>
            ) : (
              <p className="text-gray-400">Selecione um fabricante para filtrar e exportar</p>
            )}
          </div>
        </div>
      )}

      {/* TELA: Por Status */}
      {selectedReport === 'by-status' && metadata && (
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <div className="p-6 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white mb-4">Relatório por Status Operacional</h2>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Selecione o Status
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
                >
                  <option value="">-- Todos os status --</option>
                  {metadata.statuses.map(status => (
                    <option key={status.code} value={status.code}>
                      {status.label} ({status.count} equipamentos)
                    </option>
                  ))}
                </select>
              </div>
              <div className="pt-7">
                <ExportButtons filterParams={{ status: filters.status }} />
              </div>
            </div>
          </div>
          
          <div className="p-6">
            {filters.status ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-400">
                  <CheckCircleIcon className="h-5 w-5" />
                  <span className="font-medium">Status selecionado: {filters.status}</span>
                </div>
                <div className="text-gray-300">
                  {filteredData.length} equipamento(s) com este status
                </div>
              </div>
            ) : (
              <p className="text-gray-400">Selecione um status para filtrar e exportar</p>
            )}
          </div>
        </div>
      )}

      {/* TELA: Personalizado */}
      {selectedReport === 'custom' && metadata && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FunnelIcon className="h-5 w-5 text-orange-400" />
                Filtros Personalizados - Configure Livremente
              </h2>
              <button
                onClick={resetFilters}
                className="px-3 py-1.5 text-sm font-medium text-white bg-gray-700 hover:bg-gray-600 border border-gray-600 hover:border-gray-500 rounded-md transition-colors"
              >
                🔄 Limpar Filtros
              </button>
            </div>
            
            <p className="text-sm text-gray-400 mb-4">
              Selecione apenas os filtros que deseja aplicar. Você pode usar nenhum, um ou vários filtros simultaneamente.
            </p>
            
            {/* Primeira Linha: Fabricante, Modelo, Status */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Fabricante <span className="text-gray-500">(opcional)</span>
                </label>
                <select
                  value={filters.manufacturer}
                  onChange={(e) => setFilters({ ...filters, manufacturer: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
                >
                  <option value="">-- Todos os fabricantes --</option>
                  {/* Mostrar apenas fabricantes com equipamentos (count > 0) */}
                  {metadata.manufacturers
                    .filter(m => m.count > 0)
                    .map(m => (
                    <option key={m.code} value={m.name}>{m.name} ({m.count})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Modelo <span className="text-gray-500">(opcional)</span>
                </label>
                <select
                  value={filters.model}
                  onChange={(e) => setFilters({ ...filters, model: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
                >
                  <option value="">-- Todos os modelos --</option>
                  {/* Mostrar apenas modelos com equipamentos (count > 0) */}
                  {metadata.models
                    .filter(m => m.count > 0)
                    .filter(m => !filters.manufacturer || m.manufacturer_code === metadata.manufacturers.find(mfg => mfg.name === filters.manufacturer)?.code)
                    .map(m => (
                    <option key={m.code} value={m.name}>{m.name} ({m.count})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Status Operacional <span className="text-gray-500">(opcional)</span>
                </label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
                >
                  <option value="">-- Todos os status --</option>
                  {metadata.statuses.map(s => (
                    <option key={s.code} value={s.code}>{s.label} ({s.count})</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Segunda Linha: Barramento */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Barramento <span className="text-gray-500">(opcional)</span>
                </label>
                <select
                  value={filters.busbar}
                  onChange={(e) => setFilters({ ...filters, busbar: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
                >
                  <option value="">-- Todos os barramentos --</option>
                  {metadata.bays.map(b => (
                    <option key={b.name} value={b.name}>{b.name} ({b.count})</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="mt-4 p-4 bg-gray-700/50 rounded-md">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-300">
                  <span className="font-medium text-white">{filteredData.length}</span> equipamento(s) encontrado(s)
                  {activeFiltersCount > 0 && (
                    <span className="ml-2 text-gray-400">• {activeFiltersCount} filtro(s) ativo(s)</span>
                  )}
                </div>
                <ExportButtons filterParams={filters} />
              </div>
            </div>
          </div>

          {/* Preview dos Dados Filtrados */}
          {filteredData.length > 0 && (
            <div className="bg-gray-800 rounded-lg border border-gray-700">
              <div className="p-6 border-b border-gray-700">
                <h3 className="text-lg font-semibold text-white">Preview dos Resultados</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Tag</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Modelo</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Fabricante</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {filteredData.slice(0, 10).map((eq) => (
                      <tr key={eq.id} className="hover:bg-gray-700/50">
                        <td className="px-6 py-4 text-sm text-white font-medium">{eq.tag_reference}</td>
                        <td className="px-6 py-4 text-sm text-gray-300">{eq.model.name}</td>
                        <td className="px-6 py-4 text-sm text-gray-300">{eq.manufacturer.name}</td>
                        <td className="px-6 py-4 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            eq.status === 'ACTIVE' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {eq.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredData.length > 10 && (
                <div className="p-4 bg-gray-700/50 text-center text-sm text-gray-400">
                  Mostrando 10 de {filteredData.length} resultados
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-gray-800 rounded-lg p-12 border border-gray-700 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-300 font-medium">Carregando dados...</p>
        </div>
      )}

      {/* Export Loading */}
      {exportLoading && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-8 border border-gray-700 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-white font-medium">Gerando arquivo...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;
