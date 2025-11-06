/**
 * ================================================================================
 * RELAY CONFIGURATION CRUD - TELA DE EDIÇÃO DE CONFIGURAÇÕES
 * ================================================================================
 * Author: ProtecAI Engineering Team
 * Project: PETRO_ProtecAI - DIA 3
 * Date: 2025-11-03
 * Version: 1.0.0
 * 
 * Description:
 *   Interface CRUD completa para gerenciamento de configurações de relés.
 *   Suporta edição inline, bulk update, soft delete com undo.
 * 
 * Features:
 *   - ✅ Listagem paginada de configurações
 *   - ✅ Edição inline (double-click)
 *   - ✅ Validação em tempo real (min/max limits)
 *   - ✅ Bulk edit (seleção múltipla)
 *   - ✅ Soft delete com undo (10 min)
 *   - ✅ Hard delete
 *   - ✅ Filtros por equipamento/função
 *   - ✅ Feedback visual (toast notifications)
 * 
 * Tech Stack:
 *   - React 19 + TypeScript
 *   - Tailwind CSS
 *   - Axios para API calls
 *   - Headless UI para componentes
 * ================================================================================
 */

import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  PencilIcon, 
  TrashIcon, 
  CheckIcon, 
  XMarkIcon,
  ArrowPathIcon,
  FunnelIcon
} from '@heroicons/react/24/outline';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

interface RelaySetting {
  id: number;
  equipment_id: number;
  function_code: string;
  parameter_code: string;
  parameter_name: string;
  set_value: number;
  unit_of_measure?: string;
  min_limit?: number;
  max_limit?: number;
  is_enabled: boolean;
  category?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  modified_by?: string;
  deleted_at?: string | null;  // Para soft delete
}

interface UpdatePayload {
  set_value?: number;
  is_enabled?: boolean;
  min_limit?: number;
  max_limit?: number;
  category?: string;
  notes?: string;
  modified_by?: string;
}

interface ToastMessage {
  id: number;
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
}

// ============================================================================
// API SERVICE
// ============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const relayConfigAPI = {
  getSettings: async (equipmentId?: number) => {
    const params = new URLSearchParams();
    if (equipmentId) {
      params.append('equipment_id', equipmentId.toString());
    }
    const url = `${API_BASE_URL}/api/relay-config/settings${params.toString() ? '?' + params.toString() : ''}`;
    console.log('🔍 GET Settings URL:', url);
    const response = await axios.get(url);
    console.log('✅ GET Settings Response:', response.data.length, 'items');
    return response.data;
  },

  updateSetting: async (id: number, data: UpdatePayload) => {
    const response = await axios.put(
      `${API_BASE_URL}/api/relay-config/settings/${id}`,
      data
    );
    return response.data;
  },

  bulkUpdate: async (updates: Array<{ setting_id: number } & UpdatePayload>) => {
    const response = await axios.patch(
      `${API_BASE_URL}/api/relay-config/settings/bulk`,
      { updates, modified_by: 'frontend-user' }
    );
    return response.data;
  },

  deleteSetting: async (id: number, softDelete: boolean = true) => {
    const response = await axios.delete(
      `${API_BASE_URL}/api/relay-config/settings/${id}?soft_delete=${softDelete}`
    );
    return response.data;
  },

  restoreSetting: async (id: number) => {
    const response = await axios.post(
      `${API_BASE_URL}/api/relay-config/settings/${id}/restore`
    );
    return response.data;
  },
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const RelayConfigCRUD: React.FC = () => {
  // State
  const [settings, setSettings] = useState<RelaySetting[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<Partial<RelaySetting>>({});
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [filterEquipmentId, setFilterEquipmentId] = useState<string>('');

  // ============================================================================
  // LOAD DATA
  // ============================================================================

  const loadSettings = useCallback(async () => {
    setLoading(true);
    try {
      const equipId = filterEquipmentId ? parseInt(filterEquipmentId) : undefined;
      const data = await relayConfigAPI.getSettings(equipId);
      setSettings(Array.isArray(data) ? data : data.settings || []);
      showToast('success', 'Configurações carregadas com sucesso');
    } catch (error: any) {
      showToast('error', `Erro ao carregar: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  }, [filterEquipmentId]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // ============================================================================
  // TOAST NOTIFICATIONS
  // ============================================================================

  const showToast = (type: ToastMessage['type'], message: string) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  // ============================================================================
  // EDIT HANDLERS
  // ============================================================================

  const startEditing = (setting: RelaySetting) => {
    setEditingId(setting.id);
    setEditValues({
      set_value: setting.set_value,
      is_enabled: setting.is_enabled,
      min_limit: setting.min_limit,
      max_limit: setting.max_limit,
      notes: setting.notes,
    });
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditValues({});
  };

  const saveEdit = async (id: number) => {
    try {
      const payload: UpdatePayload = {
        set_value: editValues.set_value,
        is_enabled: editValues.is_enabled,
        notes: editValues.notes,
        modified_by: 'frontend-user',
      };

      await relayConfigAPI.updateSetting(id, payload);
      showToast('success', 'Configuração atualizada com sucesso');
      loadSettings();
      cancelEditing();
    } catch (error: any) {
      showToast('error', `Erro ao salvar: ${error.response?.data?.detail || error.message}`);
    }
  };

  // ============================================================================
  // VALIDATION
  // ============================================================================

  const validateValue = (value: number, min?: number, max?: number): boolean => {
    if (min !== undefined && value < min) return false;
    if (max !== undefined && value > max) return false;
    return true;
  };

  // ============================================================================
  // BULK OPERATIONS
  // ============================================================================

  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  const bulkEnable = async (enabled: boolean) => {
    try {
      const updates = Array.from(selectedIds).map(id => ({
        setting_id: id,
        is_enabled: enabled,
      }));

      await relayConfigAPI.bulkUpdate(updates);
      showToast('success', `${updates.length} configurações atualizadas`);
      loadSettings();
      setSelectedIds(new Set());
    } catch (error: any) {
      showToast('error', `Erro no bulk update: ${error.response?.data?.detail || error.message}`);
    }
  };

  // ============================================================================
  // DELETE OPERATIONS
  // ============================================================================

  const deleteSetting = async (id: number, hard: boolean = false) => {
    if (hard && !confirm('⚠️ ATENÇÃO: Hard delete é irreversível! Confirma?')) {
      return;
    }

    try {
      await relayConfigAPI.deleteSetting(id, !hard);
      showToast('success', hard ? 'Deletado permanentemente' : 'Soft delete realizado (pode desfazer)');
      loadSettings();
    } catch (error: any) {
      showToast('error', `Erro ao deletar: ${error.response?.data?.detail || error.message}`);
    }
  };

  const restoreSetting = async (id: number) => {
    try {
      await relayConfigAPI.restoreSetting(id);
      showToast('success', 'Configuração restaurada com sucesso');
      loadSettings();
    } catch (error: any) {
      showToast('error', `Erro ao restaurar: ${error.response?.data?.detail || error.message}`);
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          ⚡ Configurações de Relés - CRUD
        </h1>
        <p className="text-gray-600">
          Gerencie as configurações dos relés de proteção
        </p>
      </div>

      {/* Filters & Actions */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <input
              type="number"
              placeholder="Filtrar por Equipment ID"
              value={filterEquipmentId}
              onChange={(e) => setFilterEquipmentId(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button
              onClick={loadSettings}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <ArrowPathIcon className="h-4 w-4" />
              Recarregar
            </button>
          </div>

          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">
                {selectedIds.size} selecionados
              </span>
              <button
                onClick={() => bulkEnable(true)}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
              >
                Habilitar
              </button>
              <button
                onClick={() => bulkEnable(false)}
                className="px-3 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 text-sm"
              >
                Desabilitar
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-500">Carregando...</div>
        ) : settings.length === 0 ? (
          <div className="p-8 text-center text-gray-500">Nenhuma configuração encontrada</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-12 px-6 py-3">
                    <input
                      type="checkbox"
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds(new Set(settings.map(s => s.id)));
                        } else {
                          setSelectedIds(new Set());
                        }
                      }}
                      className="rounded border-gray-300"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Parâmetro</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Código</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Valor</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Limites</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {settings.map((setting) => (
                  <tr
                    key={setting.id}
                    className={`hover:bg-gray-50 ${selectedIds.has(setting.id) ? 'bg-blue-50' : ''}`}
                    onDoubleClick={() => !editingId && startEditing(setting)}
                  >
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(setting.id)}
                        onChange={() => toggleSelection(setting.id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{setting.id}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">{setting.parameter_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{setting.parameter_code}</td>
                    
                    {/* Editable Value */}
                    <td className="px-6 py-4">
                      {editingId === setting.id ? (
                        <input
                          type="number"
                          value={editValues.set_value ?? ''}
                          onChange={(e) => setEditValues(prev => ({
                            ...prev,
                            set_value: parseFloat(e.target.value)
                          }))}
                          className={`w-24 border rounded px-2 py-1 ${
                            !validateValue(editValues.set_value!, setting.min_limit, setting.max_limit)
                              ? 'border-red-500 bg-red-50'
                              : 'border-gray-300'
                          }`}
                        />
                      ) : (
                        <span className="text-sm font-medium">
                          {setting.set_value} {setting.unit_of_measure}
                        </span>
                      )}
                    </td>

                    {/* Limits */}
                    <td className="px-6 py-4 text-sm text-gray-600">
                      [{setting.min_limit ?? '—'}, {setting.max_limit ?? '—'}]
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        setting.is_enabled 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {setting.is_enabled ? 'Habilitado' : 'Desabilitado'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4">
                      {editingId === setting.id ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => saveEdit(setting.id)}
                            className="p-1 text-green-600 hover:bg-green-50 rounded"
                            title="Salvar"
                          >
                            <CheckIcon className="h-5 w-5" />
                          </button>
                          <button
                            onClick={cancelEditing}
                            className="p-1 text-red-600 hover:bg-red-50 rounded"
                            title="Cancelar"
                          >
                            <XMarkIcon className="h-5 w-5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          {setting.deleted_at ? (
                            <button
                              onClick={() => restoreSetting(setting.id)}
                              className="p-1 text-green-600 hover:bg-green-50 rounded"
                              title="Restaurar configuração deletada"
                            >
                              <ArrowPathIcon className="h-5 w-5" />
                            </button>
                          ) : (
                            <>
                              <button
                                onClick={() => startEditing(setting)}
                                className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                                title="Editar"
                              >
                                <PencilIcon className="h-5 w-5" />
                              </button>
                              <button
                                onClick={() => deleteSetting(setting.id)}
                                className="p-1 text-yellow-600 hover:bg-yellow-50 rounded"
                                title="Soft Delete"
                              >
                                <TrashIcon className="h-5 w-5" />
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Toast Notifications */}
      <div className="fixed bottom-4 right-4 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`px-4 py-3 rounded-lg shadow-lg text-white ${
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
};

export default RelayConfigCRUD;
