import { useState } from 'react';
import type { GenerationResult } from '../types';

interface Props {
  result: GenerationResult | null;
}

type CodeTab = 'html' | 'css' | 'jsx' | 'vue' | 'angular';

export function PreviewPanel({ result }: Props) {
  const [activeTab, setActiveTab] = useState<CodeTab>('html');
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');

  if (!result) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6 flex items-center justify-center min-h-[400px]">
        <p className="text-gray-400 text-sm">
          Generated UI will appear here
        </p>
      </div>
    );
  }

  const codeMap: Record<CodeTab, string> = {
    html: result.html_code,
    css: result.css_code,
    jsx: result.jsx_code,
    vue: result.vue_code,
    angular: result.angular_code,
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('preview')}
            className={`text-xs px-3 py-1 rounded ${
              viewMode === 'preview'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Preview
          </button>
          <button
            onClick={() => setViewMode('code')}
            className={`text-xs px-3 py-1 rounded ${
              viewMode === 'code'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Code
          </button>
        </div>
        <span className="text-xs text-gray-400">
          {result.framework}
        </span>
      </div>

      {viewMode === 'preview' ? (
        <div className="p-4 min-h-[400px] bg-gray-50">
          <iframe
            srcDoc={result.html_code}
            title="Preview"
            className="w-full h-[500px] border-0 bg-white rounded"
            sandbox="allow-same-origin"
          />
        </div>
      ) : (
        <div>
          <div className="flex border-b border-gray-200">
            {Object.keys(codeMap).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab as CodeTab)}
                className={`text-xs px-3 py-2 ${
                  activeTab === tab
                    ? 'border-b-2 border-blue-600 text-blue-600'
                    : 'text-gray-500'
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>
          <pre className="p-4 text-xs overflow-auto max-h-[500px] bg-gray-900 text-green-400">
            <code>{codeMap[activeTab]}</code>
          </pre>
        </div>
      )}

      {result.components_used.length > 0 && (
        <div className="border-t border-gray-200 px-4 py-2">
          <p className="text-xs text-gray-500">
            Components: {result.components_used.join(', ')}
          </p>
        </div>
      )}
    </div>
  );
}
