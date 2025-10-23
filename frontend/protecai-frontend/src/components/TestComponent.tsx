import React from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid';

interface TestComponentProps {}

const TestComponent: React.FC<TestComponentProps> = () => {
  return (
    <div className="min-h-screen bg-linear-to-br from-protec-50 to-protec-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h1 className="text-4xl font-bold text-protec-800 mb-6">
            🔧 ProtecAI Frontend
          </h1>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Status Cards */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-status-active mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-green-800">React + Vite + TS</h3>
                  <p className="text-green-600">✅ Configurado com sucesso</p>
                </div>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-protec-500 mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-blue-800">Tailwind CSS</h3>
                  <p className="text-blue-600">🎨 Styles carregados</p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-purple-500 mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-purple-800">Heroicons</h3>
                  <p className="text-purple-600">🎯 Ícones disponíveis</p>
                </div>
              </div>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-8 w-8 text-status-warning mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-yellow-800">API Integration</h3>
                  <p className="text-yellow-600">⏳ Próximo passo</p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 p-6 bg-protec-50 rounded-lg border border-protec-200">
            <h2 className="text-xl font-semibold text-protec-800 mb-4">
              📦 Dependências Instaladas
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
              <span className="bg-white px-3 py-1 rounded-full">React 19.1.1</span>
              <span className="bg-white px-3 py-1 rounded-full">TypeScript 5.9.3</span>
              <span className="bg-white px-3 py-1 rounded-full">Vite 7.1.7</span>
              <span className="bg-white px-3 py-1 rounded-full">Tailwind CSS</span>
              <span className="bg-white px-3 py-1 rounded-full">React Router</span>
              <span className="bg-white px-3 py-1 rounded-full">Axios</span>
              <span className="bg-white px-3 py-1 rounded-full">Socket.IO</span>
              <span className="bg-white px-3 py-1 rounded-full">HeadlessUI</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TestComponent;