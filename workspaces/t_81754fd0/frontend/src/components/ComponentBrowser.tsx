import { useState, useEffect } from 'react';
import { fetchComponents } from '../services/api';
import type { Component } from '../types';

const CATEGORIES = [
  'layout', 'navigation', 'form', 'display',
  'feedback', 'data', 'media', 'overlay',
];

export function ComponentBrowser() {
  const [components, setComponents] = useState<Component[]>([]);
  const [total, setTotal] = useState(0);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadComponents();
  }, [category, search]);

  const loadComponents = async () => {
    setLoading(true);
    try {
      const data = await fetchComponents(category, search);
      setComponents(data.components);
      setTotal(data.total);
    } catch {
      setComponents([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Component Library
          <span className="text-sm font-normal text-gray-500 ml-2">
            {total} components
          </span>
        </h2>
      </div>

      <div className="flex gap-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search components..."
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {components.map((comp) => (
            <div
              key={comp.id}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <h3 className="text-sm font-medium">{comp.name}</h3>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                  {comp.category}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{comp.description}</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {comp.tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
