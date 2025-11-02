import { useState } from 'react'
import TestComponent from './components/TestComponent'
import RealFileUpload from './components/RealFileUpload'
import SimpleAPITest from './components/SimpleAPITest'
import MainDashboard from './components/MainDashboard'
import Reports from './components/Reports'
import DatabaseSchema from './components/DatabaseSchema'

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'reports' | 'upload' | 'api' | 'database' | 'test'>('dashboard')

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 shadow-sm border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">P</span>
              </div>
              <h1 className="text-xl font-bold text-white">ProtecAI</h1>
              <span className="text-sm text-gray-300">Enterprise Protection Analysis</span>
            </div>
            
            {/* Navigation */}
            <nav className="flex space-x-4">
              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'dashboard'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                📊 Dashboard
              </button>
              <button
                onClick={() => setActiveTab('reports')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'reports'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                📄 Relatórios
              </button>
              <button
                onClick={() => setActiveTab('upload')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'upload'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                📁 Upload & Process
              </button>
              <button
                onClick={() => setActiveTab('api')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'api'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                🔗 API Integration
              </button>
              <button
                onClick={() => setActiveTab('database')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'database'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                💾 Database Schema
              </button>
              <button
                onClick={() => setActiveTab('test')}
                className={`px-4 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'test'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                🧪 System Test
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && <MainDashboard />}
        {activeTab === 'reports' && <Reports />}
        {activeTab === 'upload' && <RealFileUpload />}
        {activeTab === 'api' && <SimpleAPITest />}
        {activeTab === 'database' && <DatabaseSchema />}
        {activeTab === 'test' && <TestComponent />}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="text-center text-sm text-gray-400">
            ProtecAI System - Enterprise Relay Protection Analysis Platform
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
