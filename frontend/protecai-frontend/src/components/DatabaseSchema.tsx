import React, { useState, useEffect } from 'react';
import {
  CircleStackIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  TableCellsIcon,
  KeyIcon,
  Bars3BottomLeftIcon
} from '@heroicons/react/24/outline';

interface Column {
  column_name: string;
  data_type: string;
  is_nullable: string;
  column_default: string | null;
  is_primary_key: boolean;
  is_foreign_key: boolean;
}

interface Table {
  table_name: string;
  row_count: number;
  columns: Column[];
}

interface Schema {
  schema_name: string;
  tables: Table[];
}

interface DatabaseInfo {
  database_name: string;
  schemas: Schema[];
}

const DatabaseSchema: React.FC = () => {
  const [dbInfo, setDbInfo] = useState<DatabaseInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set(['protec_ai', 'relay_configs']));
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchDatabaseSchema();
  }, []);

  const fetchDatabaseSchema = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/v1/database/schema');
      if (!response.ok) {
        throw new Error('Falha ao carregar estrutura do banco');
      }
      const data = await response.json();
      setDbInfo(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
    } finally {
      setLoading(false);
    }
  };

  const toggleSchema = (schemaName: string) => {
    const newExpanded = new Set(expandedSchemas);
    if (newExpanded.has(schemaName)) {
      newExpanded.delete(schemaName);
    } else {
      newExpanded.add(schemaName);
    }
    setExpandedSchemas(newExpanded);
  };

  const toggleTable = (tableKey: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(tableKey)) {
      newExpanded.delete(tableKey);
    } else {
      newExpanded.add(tableKey);
    }
    setExpandedTables(newExpanded);
  };

  const getDataTypeColor = (dataType: string): string => {
    if (dataType.includes('int') || dataType.includes('serial')) return 'text-blue-400';
    if (dataType.includes('varchar') || dataType.includes('text')) return 'text-green-400';
    if (dataType.includes('timestamp') || dataType.includes('date')) return 'text-purple-400';
    if (dataType.includes('boolean')) return 'text-yellow-400';
    if (dataType.includes('numeric') || dataType.includes('decimal')) return 'text-cyan-400';
    return 'text-slate-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <CircleStackIcon className="h-12 w-12 text-blue-500 animate-pulse mx-auto mb-4" />
          <p className="text-slate-400">Carregando estrutura do banco de dados...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
        <h3 className="text-red-400 font-semibold mb-2">Erro ao Carregar Schema</h3>
        <p className="text-red-300 text-sm">{error}</p>
        <button
          onClick={fetchDatabaseSchema}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition-colors"
        >
          Tentar Novamente
        </button>
      </div>
    );
  }

  if (!dbInfo) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 shadow-lg">
        <div className="flex items-center gap-4">
          <div className="bg-slate-700/50 p-3 rounded-lg">
            <CircleStackIcon className="h-7 w-7 text-slate-300" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">
              Estrutura do Banco de Dados
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Database: <span className="text-blue-400 font-medium">{dbInfo.database_name}</span> • 
              {' '}{dbInfo.schemas.length} schema(s) • 
              {' '}{dbInfo.schemas.reduce((acc, s) => acc + s.tables.length, 0)} tabela(s)
            </p>
          </div>
        </div>
      </div>

      {/* Schemas List */}
      <div className="space-y-4">
        {dbInfo.schemas.map((schema) => (
          <div key={schema.schema_name} className="bg-slate-800 rounded-xl border border-slate-700 shadow-lg overflow-hidden">
            {/* Schema Header */}
            <div
              onClick={() => toggleSchema(schema.schema_name)}
              className="bg-slate-900/50 p-4 cursor-pointer hover:bg-slate-900/70 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                {expandedSchemas.has(schema.schema_name) ? (
                  <ChevronDownIcon className="h-5 w-5 text-slate-400" />
                ) : (
                  <ChevronRightIcon className="h-5 w-5 text-slate-400" />
                )}
                <Bars3BottomLeftIcon className="h-5 w-5 text-emerald-400" />
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold text-white">
                      {schema.schema_name}
                    </h3>
                    {schema.schema_name === 'public' && schema.tables.length === 0 && (
                      <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-md" title="Schema padrão do PostgreSQL - vazio indica boa organização">
                        Vazio (Padrão)
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">
                    {schema.tables.length} tabela(s)
                  </p>
                </div>
              </div>
              <div className="text-xs text-slate-500 font-mono">
                SCHEMA
              </div>
            </div>

            {/* Tables List */}
            {expandedSchemas.has(schema.schema_name) && (
              <div className="divide-y divide-slate-700">
                {schema.tables.map((table) => {
                  const tableKey = `${schema.schema_name}.${table.table_name}`;
                  const isExpanded = expandedTables.has(tableKey);

                  return (
                    <div key={tableKey}>
                      {/* Table Header */}
                      <div
                        onClick={() => toggleTable(tableKey)}
                        className="p-4 cursor-pointer hover:bg-slate-700/30 transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3">
                          {isExpanded ? (
                            <ChevronDownIcon className="h-4 w-4 text-slate-400" />
                          ) : (
                            <ChevronRightIcon className="h-4 w-4 text-slate-400" />
                          )}
                          <TableCellsIcon className="h-5 w-5 text-blue-400" />
                          <div>
                            <h4 className="text-sm font-medium text-slate-200">
                              {table.table_name}
                            </h4>
                            <p className="text-xs text-slate-500">
                              {table.columns.length} coluna(s) • {table.row_count.toLocaleString()} registro(s)
                            </p>
                          </div>
                        </div>
                        <div className="text-xs text-slate-500 font-mono">
                          TABLE
                        </div>
                      </div>

                      {/* Columns List */}
                      {isExpanded && (
                        <div className="bg-slate-900/30 px-4 py-3">
                          <div className="space-y-2">
                            {table.columns.map((column, idx) => (
                              <div
                                key={idx}
                                className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg hover:bg-slate-800/80 transition-colors"
                              >
                                <div className="flex items-center gap-3 flex-1">
                                  {column.is_primary_key && (
                                    <KeyIcon className="h-4 w-4 text-yellow-400" title="Primary Key" />
                                  )}
                                  {column.is_foreign_key && (
                                    <KeyIcon className="h-4 w-4 text-purple-400" title="Foreign Key" />
                                  )}
                                  <span className="text-sm font-mono text-slate-200">
                                    {column.column_name}
                                  </span>
                                </div>
                                <div className="flex items-center gap-4 text-xs">
                                  <span className={`font-mono font-semibold ${getDataTypeColor(column.data_type)}`}>
                                    {column.data_type}
                                  </span>
                                  {column.is_nullable === 'YES' ? (
                                    <span className="text-slate-500 px-2 py-0.5 bg-slate-700/50 rounded">
                                      nullable
                                    </span>
                                  ) : (
                                    <span className="text-red-400 px-2 py-0.5 bg-red-500/10 rounded">
                                      NOT NULL
                                    </span>
                                  )}
                                  {column.column_default && (
                                    <span className="text-slate-500 font-mono text-xs">
                                      default: {column.column_default}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DatabaseSchema;
