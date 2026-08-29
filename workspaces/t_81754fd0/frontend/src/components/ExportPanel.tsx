import { useState } from 'react';
import { exportUI } from '../services/api';
import type { GenerationResult } from '../types';

interface Props {
  result: GenerationResult;
}

export function ExportPanel({ result }: Props) {
  const [framework, setFramework] = useState(result.framework);
  const [minify, setMinify] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportedCode, setExportedCode] = useState('');

  const handleExport = async () => {
    setExporting(true);
    try {
      const resp = await exportUI(result.id, framework, minify);
      setExportedCode(resp.code);
    } catch {
      setExportedCode('Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(exportedCode);
  };

  const handleDownload = () => {
    const blob = new Blob([exportedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `export-${framework}.${framework === 'react' ? 'tsx' : framework === 'vue' ? 'vue' : framework === 'angular' ? 'ts' : 'html'}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <h2 className="text-lg font-semibold">Export</h2>

      <div className="flex gap-4">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Framework
          </label>
          <select
            value={framework}
            onChange={(e) => setFramework(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
          >
            <option value="react">React</option>
            <option value="vue">Vue</option>
            <option value="angular">Angular</option>
            <option value="html_css">HTML + CSS</option>
          </select>
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={minify}
              onChange={(e) => setMinify(e.target.checked)}
              className="rounded"
            />
            Minify
          </label>
        </div>
      </div>

      <button
        onClick={handleExport}
        disabled={exporting}
        className="w-full bg-green-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
      >
        {exporting ? 'Exporting...' : 'Export Code'}
      </button>

      {exportedCode && (
        <div className="space-y-2">
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded hover:bg-gray-200"
            >
              Copy
            </button>
            <button
              onClick={handleDownload}
              className="text-xs bg-gray-100 text-gray-700 px-3 py-1 rounded hover:bg-gray-200"
            >
              Download
            </button>
          </div>
          <pre className="p-3 text-xs bg-gray-900 text-green-400 rounded max-h-[200px] overflow-auto">
            {exportedCode.slice(0, 1000)}
            {exportedCode.length > 1000 && '...'}
          </pre>
        </div>
      )}
    </div>
  );
}
