import { useState } from 'react';
import { GenerationPanel } from './components/GenerationPanel';
import { PreviewPanel } from './components/PreviewPanel';
import { ComponentBrowser } from './components/ComponentBrowser';
import { ExportPanel } from './components/ExportPanel';
import type { GenerationResult } from './types';

export default function App() {
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [activeTab, setActiveTab] = useState<'generate' | 'components'>('generate');

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold text-blue-600">UIGenerator</h1>
          <p className="text-sm text-gray-500">AI-Powered UI Generation</p>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200 px-6">
        <div className="max-w-7xl mx-auto flex gap-6">
          <button
            onClick={() => setActiveTab('generate')}
            className={`py-3 px-1 border-b-2 text-sm font-medium ${
              activeTab === 'generate'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Generate
          </button>
          <button
            onClick={() => setActiveTab('components')}
            className={`py-3 px-1 border-b-2 text-sm font-medium ${
              activeTab === 'components'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Components
          </button>
        </div>
      </nav>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        {activeTab === 'generate' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <GenerationPanel onResult={setResult} />
              {result && <ExportPanel result={result} />}
            </div>
            <PreviewPanel result={result} />
          </div>
        ) : (
          <ComponentBrowser />
        )}
      </main>
    </div>
  );
}
