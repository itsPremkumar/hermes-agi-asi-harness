import { useState } from 'react';
import { generateUI } from '../services/api';
import type { GenerationResult } from '../types';

interface Props {
  onResult: (result: GenerationResult) => void;
}

const EXAMPLES = [
  'A login form with email input, password input, and submit button',
  'A responsive navbar with logo, links, and search bar',
  'A dashboard with sidebar navigation and metric cards',
  'A contact form with name, email, message, and send button',
  'A pricing section with three tier cards',
];

export function GenerationPanel({ onResult }: Props) {
  const [description, setDescription] = useState('');
  const [framework, setFramework] = useState('react');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!description.trim()) return;
    setLoading(true);
    setError('');
    try {
      const result = await generateUI(description, framework);
      onResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
      <h2 className="text-lg font-semibold">Generate UI</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the UI you want to generate..."
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          rows={4}
        />
      </div>

      <div>
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

      <button
        onClick={handleGenerate}
        disabled={loading || !description.trim()}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Generating...' : 'Generate'}
      </button>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <div className="border-t border-gray-100 pt-3">
        <p className="text-xs text-gray-500 mb-2">Try an example:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setDescription(ex)}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded hover:bg-gray-200"
            >
              {ex.length > 40 ? ex.slice(0, 40) + '...' : ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
