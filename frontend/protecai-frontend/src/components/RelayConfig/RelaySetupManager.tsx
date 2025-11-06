/**
 * ⚙️ RELAY SETUP MANAGER
 * 
 * Interface profissional para engenheiros de proteção gerenciarem
 * configurações de relés (setup/parametrização).
 * 
 * FUNCIONALIDADES:
 * 1. Selecionar relé específico por TAG ou dropdown
 * 2. Visualizar setup completo com dados do equipamento
 * 3. Editar valores com validação automática
 * 4. Salvar com justificativa (audit trail)
 * 5. Gerar relatório profissional (PDF/Excel/CSV)
 * 6. Deletar relé com confirmação
 * 
 * Author: ProtecAI Team
 * Date: 2025-11-03
 */

import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================================================
// TYPES
// ============================================================================

interface Equipment {
  id: number;
  equipment_tag: string;
  manufacturer_name: string;
  model_name: string;
  bay_name: string;
  substation_name: string;
  has_settings: boolean;
}

interface RelaySetting {
  id: number;
  function_code: string;
  function_name: string;
  parameter_code: string;
  parameter_name: string;
  set_value: number | null;
  unit_of_measure: string;
  min_limit: number | null;
  max_limit: number | null;
  is_enabled: boolean;
  notes: string | null;
  updated_at: string;
  modified_by: string | null;
}

interface Toast {
  id: number;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function RelaySetupManager() {
  // State
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([]);
  const [selectedEquipment, setSelectedEquipment] = useState<Equipment | null>(null);
  const [settings, setSettings] = useState<RelaySetting[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<number | null>(null);
  const [justification, setJustification] = useState('');
  const [toasts, setToasts] = useState<Toast[]>([]);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  useEffect(() => {
    loadEquipmentList();
  }, []);

  useEffect(() => {
    if (selectedEquipment) {
      loadSettings(selectedEquipment.id);
    }
  }, [selectedEquipment]);

  // ============================================================================
  // API CALLS
  // ============================================================================

  const loadEquipmentList = async () => {
    try {
      setLoading(true);
      console.log('🔍 Carregando equipamentos de:', `${API_BASE_URL}/api/relay-config/equipment/list`);
      const response = await axios.get(`${API_BASE_URL}/api/relay-config/equipment/list`);
      console.log('✅ Resposta recebida:', response.data);
      setEquipmentList(response.data.equipment || []);
      console.log('📊 Equipment list atualizada:', response.data.equipment?.length || 0, 'itens');
    } catch (error: any) {
      console.error('❌ Erro ao carregar equipamentos:', error);
      showToast('error', `Erro ao carregar lista de equipamentos: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadSettings = async (equipmentId: number) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_BASE_URL}/api/relay-config/settings?equipment_id=${equipmentId}&limit=1000`
      );
      setSettings(response.data || []);
    } catch (error: any) {
      showToast('error', `Erro ao carregar configurações: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const saveSetting = async (settingId: number, newValue: number | null) => {
    if (!justification.trim()) {
      showToast('error', 'Justificativa é obrigatória para salvar alterações!');
      return;
    }

    try {
      await axios.put(`${API_BASE_URL}/api/relay-config/settings/${settingId}`, {
        set_value: newValue,
        notes: justification
      });
      
      showToast('success', 'Configuração atualizada com sucesso!');
      setEditingId(null);
      setJustification('');
      
      // Recarregar settings
      if (selectedEquipment) {
        loadSettings(selectedEquipment.id);
      }
    } catch (error: any) {
      showToast('error', `Erro ao salvar: ${error.message}`);
    }
  };

  const generateReport = async (format: 'pdf' | 'excel' | 'csv') => {
    if (!selectedEquipment) {
      showToast('error', 'Selecione um relé primeiro!');
      return;
    }

    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/relay-config/relay-setup-report/${selectedEquipment.id}?format=${format}`,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = format === 'excel' ? 'xlsx' : format;
      link.setAttribute('download', `setup_${selectedEquipment.equipment_tag}.${extension}`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showToast('success', `Relatório ${format.toUpperCase()} gerado com sucesso!`);
    } catch (error: any) {
      showToast('error', `Erro ao gerar relatório: ${error.message}`);
    }
  };

  const deleteRelay = async () => {
    if (!selectedEquipment) return;

    const confirmed = window.confirm(
      `⚠️ ATENÇÃO: Deseja realmente deletar o relé ${selectedEquipment.equipment_tag}?\n\nEsta ação irá remover todas as configurações associadas!`
    );

    if (!confirmed) return;

    try {
      await axios.delete(`${API_BASE_URL}/api/relay-config/equipment/${selectedEquipment.id}`);
      showToast('success', 'Relé deletado com sucesso!');
      
      setSelectedEquipment(null);
      setSettings([]);
      loadEquipmentList();
    } catch (error: any) {
      showToast('error', `Erro ao deletar: ${error.message}`);
    }
  };

  // ============================================================================
  // HELPERS
  // ============================================================================

  const showToast = (type: Toast['type'], message: string) => {
    const newToast: Toast = {
      id: Date.now(),
      type,
      message
    };
    setToasts(prev => [...prev, newToast]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== newToast.id));
    }, 5000);
  };

  const isValueValid = (value: number | null, min: number | null, max: number | null): boolean => {
    if (value === null) return true;
    if (min !== null && value < min) return false;
    if (max !== null && value > max) return false;
    return true;
  };

  const getValueColor = (value: number | null, min: number | null, max: number | null): string => {
    if (value === null) return 'text-gray-400';
    if (!isValueValid(value, min, max)) return 'text-red-600 font-bold';
    return 'text-green-600';
  };

  const filteredEquipment = equipmentList.filter(eq =>
    eq.equipment_tag.toLowerCase().includes(searchTerm.toLowerCase()) ||
    eq.bay_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    eq.manufacturer_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Group settings by function
  const groupedSettings = settings.reduce((acc, setting) => {
    const key = setting.function_code || 'Outros';
    if (!acc[key]) acc[key] = [];
    acc[key].push(setting);
    return acc;
  }, {} as Record<string, RelaySetting[]>);

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          <span>⚙️</span>
          <span>Configuração de Setup de Relés</span>
        </h1>
        <p className="text-gray-600 mt-1">
          Gerencie configurações de proteção dos relés da sua subestação
        </p>
      </div>

      {/* Step 1: Select Equipment */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span>📍</span>
          <span>PASSO 1: Selecione o Relé</span>
        </h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            🔍 Buscar por TAG, Bay ou Fabricante:
          </label>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Ex: 21-REL-87B-001, Bay 21, GE..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="max-h-64 overflow-y-auto border border-gray-200 rounded-lg">
          {loading ? (
            <div className="p-4 text-center text-gray-500">Carregando equipamentos...</div>
          ) : filteredEquipment.length === 0 ? (
            <div className="p-4 text-center text-gray-500">Nenhum equipamento encontrado</div>
          ) : (
            filteredEquipment.map((eq) => (
              <div
                key={eq.id}
                onClick={() => setSelectedEquipment(eq)}
                className={`p-4 cursor-pointer border-b border-gray-100 hover:bg-blue-50 transition-colors ${
                  selectedEquipment?.id === eq.id ? 'bg-blue-100 border-l-4 border-l-blue-600' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800">{eq.equipment_tag}</div>
                    <div className="text-sm text-gray-600">
                      {eq.manufacturer_name} {eq.model_name} | {eq.bay_name} | {eq.substation_name}
                    </div>
                  </div>
                  {eq.has_settings && (
                    <span className="text-green-600 text-sm">✓ Com configurações</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Step 2: View/Edit Settings */}
      {selectedEquipment && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              📊 RELÉ SELECIONADO: {selectedEquipment.equipment_tag}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Fabricante:</span>
                <div className="font-semibold">{selectedEquipment.manufacturer_name}</div>
              </div>
              <div>
                <span className="text-gray-600">Modelo:</span>
                <div className="font-semibold">{selectedEquipment.model_name}</div>
              </div>
              <div>
                <span className="text-gray-600">Bay:</span>
                <div className="font-semibold">{selectedEquipment.bay_name}</div>
              </div>
              <div>
                <span className="text-gray-600">Subestação:</span>
                <div className="font-semibold">{selectedEquipment.substation_name}</div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => generateReport('pdf')}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              <span>📄</span>
              <span>Gerar PDF</span>
            </button>
            <button
              onClick={() => generateReport('excel')}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <span>📊</span>
              <span>Exportar Excel</span>
            </button>
            <button
              onClick={() => generateReport('csv')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <span>📋</span>
              <span>Exportar CSV</span>
            </button>
            <button
              onClick={deleteRelay}
              className="flex items-center gap-2 px-4 py-2 bg-red-800 text-white rounded-lg hover:bg-red-900 transition-colors ml-auto"
            >
              <span>🗑️</span>
              <span>Deletar Relé</span>
            </button>
          </div>

          {/* Settings Table */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">📋 Parâmetros de Proteção</h3>
            
            {settings.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                Nenhuma configuração encontrada para este relé
              </div>
            ) : (
              Object.entries(groupedSettings).map(([functionCode, functionSettings]) => (
                <div key={functionCode} className="mb-6">
                  <h4 className="font-semibold text-gray-700 mb-2 bg-gray-100 p-2 rounded">
                    Função ANSI: {functionCode}
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Parâmetro</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Unidade</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Limites</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                          <th className="p-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {functionSettings.map((setting) => (
                          <tr key={setting.id} className="hover:bg-gray-50">
                            <td className="p-3 text-sm font-mono">{setting.parameter_code}</td>
                            <td className="p-3 text-sm">{setting.parameter_name}</td>
                            <td className="p-3 text-sm">
                              {editingId === setting.id ? (
                                <input
                                  type="number"
                                  step="0.01"
                                  value={editValue ?? ''}
                                  onChange={(e) => setEditValue(e.target.value ? parseFloat(e.target.value) : null)}
                                  className="w-24 px-2 py-1 border border-blue-500 rounded focus:ring-2 focus:ring-blue-500"
                                  autoFocus
                                />
                              ) : (
                                <span className={getValueColor(setting.set_value, setting.min_limit, setting.max_limit)}>
                                  {setting.set_value ?? '—'}
                                </span>
                              )}
                            </td>
                            <td className="p-3 text-sm text-gray-600">{setting.unit_of_measure || '—'}</td>
                            <td className="p-3 text-sm text-gray-600">
                              [{setting.min_limit ?? '—'}, {setting.max_limit ?? '—'}]
                            </td>
                            <td className="p-3 text-sm">
                              {setting.is_enabled ? (
                                <span className="text-green-600">✓ Habilitado</span>
                              ) : (
                                <span className="text-gray-400">○ Desabilitado</span>
                              )}
                            </td>
                            <td className="p-3 text-sm">
                              {editingId === setting.id ? (
                                <button
                                  onClick={() => saveSetting(setting.id, editValue)}
                                  className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                  💾 Salvar
                                </button>
                              ) : (
                                <button
                                  onClick={() => {
                                    setEditingId(setting.id);
                                    setEditValue(setting.set_value);
                                  }}
                                  className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                                >
                                  ✏️ Editar
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Justification Input */}
          {editingId && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💬 Justificativa da alteração (obrigatório):
              </label>
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Ex: Ajuste de seletividade conforme estudo de coordenação..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
            </div>
          )}
        </div>
      )}

      {/* Toast Notifications */}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`p-4 rounded-lg shadow-lg text-white max-w-md ${
              toast.type === 'success' ? 'bg-green-600' :
              toast.type === 'error' ? 'bg-red-600' :
              toast.type === 'warning' ? 'bg-yellow-600' :
              'bg-blue-600'
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  );
}
