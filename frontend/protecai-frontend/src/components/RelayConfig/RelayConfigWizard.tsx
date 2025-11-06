/**
 * 🔧 RELAY CONFIGURATION WIZARD
 * 
 * Interface hierárquica profissional para engenheiros de proteção.
 * Fluxo de trabalho intuitivo em 3 passos:
 * 
 * PASSO 1: Selecionar Fabricante
 * PASSO 2: Selecionar Modelo (filtrado por fabricante)
 * PASSO 3: Selecionar Relé (filtrado por fabricante + modelo)
 * 
 * Após seleção: Exibe dados completos + parâmetros + relatórios
 * 
 * Author: ProtecAI Team
 * Date: 2025-11-03
 */

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ============================================================================
// TYPES
// ============================================================================

interface Manufacturer {
  id: number;
  name: string;
  relay_count: number;
}

interface Model {
  id: number;
  name: string;
  manufacturer_id: number;
  relay_count: number;
}

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

export default function RelayConfigWizard() {
  // State - Step 1: Manufacturers
  const [manufacturers, setManufacturers] = useState<Manufacturer[]>([]);
  const [selectedManufacturerId, setSelectedManufacturerId] = useState<number | null>(null);

  // State - Step 2: Models
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);

  // State - Step 3: Equipment
  const [equipmentList, setEquipmentList] = useState<Equipment[]>([]);
  const [selectedEquipment, setSelectedEquipment] = useState<Equipment | null>(null);

  // State - Step 4: Settings
  const [settings, setSettings] = useState<RelaySetting[]>([]);

  // UI State
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<number | null>(null);
  const [justification, setJustification] = useState('');
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Refs to prevent unnecessary resets
  const previousManufacturerId = useRef<number | null>(null);
  const previousModelId = useRef<number | null>(null);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Load manufacturers on mount
  useEffect(() => {
    loadManufacturers();
  }, []);

  // Load models when manufacturer changes
  useEffect(() => {
    console.log('🔄 useEffect MANUFACTURER mudou:', selectedManufacturerId, 'anterior:', previousManufacturerId.current);
    
    // Only reset if manufacturer ACTUALLY changed (not first selection)
    const manufacturerChanged = previousManufacturerId.current !== null && 
                                previousManufacturerId.current !== selectedManufacturerId;
    
    if (selectedManufacturerId) {
      loadModels(selectedManufacturerId);
      
      // Only reset downstream if manufacturer changed (user switching, not selecting for first time)
      if (manufacturerChanged) {
        console.log('⚠️ Fabricante mudou - resetando modelo e equipamento');
        setSelectedModelId(null);
        setSelectedEquipment(null);
        setSettings([]);
      }
      
      previousManufacturerId.current = selectedManufacturerId;
    } else {
      setModels([]);
      previousManufacturerId.current = null;
    }
  }, [selectedManufacturerId]);

  // Load equipment when model changes
  useEffect(() => {
    console.log('🔄 useEffect MODEL mudou:', selectedModelId, 'anterior:', previousModelId.current, 'manufacturer:', selectedManufacturerId);
    
    // Only reset if model ACTUALLY changed (not first selection)
    const modelChanged = previousModelId.current !== null && 
                        previousModelId.current !== selectedModelId;
    
    if (selectedManufacturerId && selectedModelId) {
      loadEquipment(selectedManufacturerId, selectedModelId);
      
      // Only reset equipment if model changed (user switching, not selecting for first time)
      if (modelChanged) {
        console.log('⚠️ Modelo mudou - resetando equipamento');
        setSelectedEquipment(null);
        setSettings([]);
      }
      
      previousModelId.current = selectedModelId;
    } else {
      setEquipmentList([]);
      if (!selectedModelId) {
        previousModelId.current = null;
      }
    }
  }, [selectedModelId, selectedManufacturerId]);

  // Load settings when equipment changes
  useEffect(() => {
    console.log('🔄 useEffect selectedEquipment mudou:', selectedEquipment);
    if (selectedEquipment) {
      console.log('📋 Dados do equipamento:', {
        id: selectedEquipment.id,
        tag: selectedEquipment.equipment_tag,
        manufacturer_name: selectedEquipment.manufacturer_name,
        model_name: selectedEquipment.model_name,
        bay_name: selectedEquipment.bay_name,
        substation_name: selectedEquipment.substation_name
      });
      loadSettings(selectedEquipment.id);
    } else {
      setSettings([]);
    }
  }, [selectedEquipment]);

  // ============================================================================
  // API CALLS
  // ============================================================================

  const loadManufacturers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/api/relay-config/manufacturers`);
      setManufacturers(response.data.manufacturers || []);
    } catch (error: any) {
      showToast('error', `Erro ao carregar fabricantes: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async (manufacturerId: number) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${API_BASE_URL}/api/relay-config/models?manufacturer_id=${manufacturerId}`
      );
      setModels(response.data.models || []);
    } catch (error: any) {
      showToast('error', `Erro ao carregar modelos: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadEquipment = async (manufacturerId: number, modelId: number) => {
    try {
      setLoading(true);
      console.log('🔍 Carregando relés:', `manufacturer_id=${manufacturerId}, model_id=${modelId}`);
      const response = await axios.get(
        `${API_BASE_URL}/api/relay-config/relays?manufacturer_id=${manufacturerId}&model_id=${modelId}`
      );
      console.log('✅ Resposta recebida:', response.data);
      console.log('📊 Relés:', response.data.relays);
      setEquipmentList(response.data.relays || []);
      console.log('📋 Equipment list atualizada:', response.data.relays?.length || 0, 'itens');
    } catch (error: any) {
      console.error('❌ Erro ao carregar relés:', error);
      showToast('error', `Erro ao carregar equipamentos: ${error.message}`);
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
      
      if (selectedEquipment) {
        loadSettings(selectedEquipment.id);
      }
    } catch (error: any) {
      showToast('error', `Erro ao salvar: ${error.message}`);
    }
  };

  const generateReport = async (format: 'pdf' | 'excel' | 'csv') => {
    if (!selectedEquipment) return;

    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/relay-config/relay-setup-report/${selectedEquipment.id}`,
        { responseType: format === 'pdf' ? 'blob' : 'json' }
      );

      if (format === 'pdf') {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `relay_${selectedEquipment.equipment_tag}_setup.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      } else {
        console.log('Relatório gerado:', response.data);
        showToast('success', `Relatório ${format.toUpperCase()} gerado com sucesso!`);
      }
    } catch (error: any) {
      showToast('error', `Erro ao gerar relatório: ${error.message}`);
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
    setToasts((prev) => [...prev, newToast]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
    }, 5000);
  };

  const startEdit = (setting: RelaySetting) => {
    setEditingId(setting.id);
    setEditValue(setting.set_value);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValue(null);
    setJustification('');
  };

  const isValueValid = (value: number | null, min: number | null, max: number | null): boolean => {
    if (value === null) return true;
    if (min !== null && value < min) return false;
    if (max !== null && value > max) return false;
    return true;
  };

  const getValueColorClass = (value: number | null, min: number | null, max: number | null): string => {
    if (value === null) return 'text-gray-400';
    if (!isValueValid(value, min, max)) return 'text-red-600 font-bold';
    return 'text-green-600';
  };

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
          <span>🔧</span>
          <span>Configuração de Setup de Relés</span>
        </h1>
        <p className="text-gray-600 mt-2">
          Gerencie configurações de proteção dos relés da sua subestação
        </p>
      </div>

      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg text-white ${
              toast.type === 'success' ? 'bg-green-500' :
              toast.type === 'error' ? 'bg-red-500' :
              toast.type === 'warning' ? 'bg-yellow-500' :
              'bg-blue-500'
            }`}
          >
            {toast.message}
          </div>
        ))}
      </div>

      {/* Wizard Steps */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* STEP 1: Select Manufacturer */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              📍 PASSO 1: Selecione o Fabricante
            </label>
            <select
              value={selectedManufacturerId ?? ''}
              onChange={(e) => {
                const value = e.target.value;
                setSelectedManufacturerId(value ? Number(value) : null);
              }}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
              disabled={loading}
            >
              <option value="">-- Selecione um fabricante --</option>
              {manufacturers.map((mfr) => (
                <option key={mfr.id} value={mfr.id}>
                  {mfr.name} ({mfr.relay_count} relés)
                </option>
              ))}
            </select>
          </div>

          {/* STEP 2: Select Model */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              📍 PASSO 2: Selecione o Modelo
            </label>
            <select
              value={selectedModelId ?? ''}
              onChange={(e) => {
                const value = e.target.value;
                setSelectedModelId(value ? Number(value) : null);
              }}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg disabled:bg-gray-100"
              disabled={!selectedManufacturerId || loading}
            >
              <option value="">-- Selecione um modelo --</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} ({model.relay_count} relés)
                </option>
              ))}
            </select>
          </div>

          {/* STEP 3: Select Relay */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              📍 PASSO 3: Selecione o Relé
            </label>
            <select
              value={selectedEquipment?.id ?? ''}
              onChange={(e) => {
                const value = e.target.value;
                console.log('🔍 DEBUG onChange Relé:');
                console.log('  - value selecionado:', value, 'tipo:', typeof value);
                console.log('  - equipmentList.length:', equipmentList.length);
                console.log('  - equipmentList[0]:', equipmentList[0]);
                const eq = equipmentList.find(eq => {
                  console.log(`  - Comparando: eq.id=${eq.id} (${typeof eq.id}) === Number(${value})=${Number(value)} (${typeof Number(value)})`);
                  return eq.id === Number(value);
                });
                console.log('  - Resultado do find():', eq);
                setSelectedEquipment(eq || null);
              }}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg disabled:bg-gray-100"
              disabled={!selectedModelId || loading}
            >
              <option value="">-- Selecione um relé --</option>
              {equipmentList.map((eq) => (
                <option key={eq.id} value={eq.id}>
                  {eq.equipment_tag}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Progress Indicator */}
        <div className="mt-6 flex items-center justify-center gap-2">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
            selectedManufacturerId ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
          }`}>
            1
          </div>
          <div className={`w-16 h-1 ${selectedManufacturerId ? 'bg-green-500' : 'bg-gray-200'}`}></div>
          <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
            selectedModelId ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
          }`}>
            2
          </div>
          <div className={`w-16 h-1 ${selectedModelId ? 'bg-green-500' : 'bg-gray-200'}`}></div>
          <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
            selectedEquipment ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
          }`}>
            3
          </div>
        </div>
      </div>

      {/* Selected Relay Details & Settings */}
      {selectedEquipment && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          {/* Relay Info Panel */}
          <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              📊 RELÉ SELECIONADO: {selectedEquipment.equipment_tag}
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Fabricante:</span>
                <div className="font-semibold">{selectedEquipment.manufacturer_name || '❌ undefined'}</div>
              </div>
              <div>
                <span className="text-gray-600">Modelo:</span>
                <div className="font-semibold">{selectedEquipment.model_name || '❌ undefined'}</div>
              </div>
              <div>
                <span className="text-gray-600">Bay:</span>
                <div className="font-semibold">{selectedEquipment.bay_name || '❌ undefined'}</div>
              </div>
              <div>
                <span className="text-gray-600">Subestação:</span>
                <div className="font-semibold">{selectedEquipment.substation_name || '❌ undefined'}</div>
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
          </div>

          {/* Settings Table */}
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📋 Parâmetros de Proteção</h3>
          
          {loading ? (
            <div className="text-center py-8 text-gray-500">Carregando parâmetros...</div>
          ) : settings.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Nenhum parâmetro configurado para este relé
            </div>
          ) : (
            Object.entries(groupedSettings).map(([functionCode, functionSettings]) => (
              <div key={functionCode} className="mb-6">
                <h4 className="font-semibold text-gray-700 mb-2 bg-gray-100 px-3 py-2 rounded">
                  Função ANSI: {functionCode}
                </h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parâmetro</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unidade</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Limites</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {functionSettings.map((setting) => (
                        <tr key={setting.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm">{setting.parameter_code || '—'}</td>
                          <td className="px-4 py-3 text-sm">{setting.parameter_name || '—'}</td>
                          <td className="px-4 py-3 text-sm">
                            {editingId === setting.id ? (
                              <input
                                type="number"
                                value={editValue ?? ''}
                                onChange={(e) => setEditValue(e.target.value ? Number(e.target.value) : null)}
                                className="w-24 px-2 py-1 border border-gray-300 rounded"
                                step="0.01"
                              />
                            ) : (
                              <span className={getValueColorClass(setting.set_value, setting.min_limit, setting.max_limit)}>
                                {setting.set_value ?? '—'}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm">{setting.unit_of_measure || '—'}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">
                            [{setting.min_limit ?? '—'}, {setting.max_limit ?? '—'}]
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {setting.is_enabled ? (
                              <span className="text-green-600">✓ Habilitado</span>
                            ) : (
                              <span className="text-gray-400">✗ Desabilitado</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm">
                            {editingId === setting.id ? (
                              <div className="flex flex-col gap-2">
                                <input
                                  type="text"
                                  placeholder="Justificativa (obrigatória)"
                                  value={justification}
                                  onChange={(e) => setJustification(e.target.value)}
                                  className="px-2 py-1 border border-gray-300 rounded text-xs"
                                />
                                <div className="flex gap-1">
                                  <button
                                    onClick={() => saveSetting(setting.id, editValue)}
                                    className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs"
                                  >
                                    ✓ Salvar
                                  </button>
                                  <button
                                    onClick={cancelEdit}
                                    className="px-3 py-1 bg-gray-400 text-white rounded hover:bg-gray-500 text-xs"
                                  >
                                    ✗ Cancelar
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button
                                onClick={() => startEdit(setting)}
                                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs"
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
      )}

      {/* Empty State */}
      {!selectedEquipment && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <div className="text-6xl mb-4">🔧</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            Selecione um relé para começar
          </h3>
          <p className="text-gray-500">
            Use os campos acima para selecionar: Fabricante → Modelo → Relé
          </p>
        </div>
      )}
    </div>
  );
}
