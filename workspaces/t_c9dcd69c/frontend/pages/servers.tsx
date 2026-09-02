"""Servers listing page."""
import React, { useState, useEffect } from "react";
import Head from "next/head";

interface Server {
  id: string;
  name: string;
  slug: string;
  description: string;
  author: string;
  github_stars: number;
  downloads: number;
  mcp_transport: string;
  category: string;
  tags: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function ServersPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("newest");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchServers = async () => {
      setLoading(true);
      const params = new URLSearchParams({
        page: String(page),
        per_page: "24",
        sort,
      });
      if (category) params.set("category", category);
      
      const resp = await fetch(`${API_BASE}/servers?${params}`);
      const data = await resp.json();
      setServers(data.servers || []);
      setTotal(data.total || 0);
      setLoading(false);
    };
    fetchServers();
  }, [page, category, sort]);

  const totalPages = Math.ceil(total / 24);

  return (
    <>
      <Head>
        <title>Browse Servers — MCPHub</title>
      </Head>
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Browse MCP Servers</h1>
        
        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="">All Categories</option>
            <option value="developer-tools">Developer Tools</option>
            <option value="data">Data</option>
            <option value="productivity">Productivity</option>
            <option value="search">Search</option>
            <option value="ai-ml">AI/ML</option>
            <option value="security">Security</option>
            <option value="database">Database</option>
            <option value="cloud">Cloud</option>
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            className="border rounded px-3 py-2"
          >
            <option value="newest">Newest</option>
            <option value="stars">Most Stars</option>
            <option value="downloads">Most Downloads</option>
            <option value="health">Best Health</option>
          </select>
        </div>

        {loading ? (
          <p className="text-center py-12">Loading...</p>
        ) : (
          <>
            <p className="text-gray-600 mb-4">{total} servers</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {servers.map((server) => (
                <div key={server.id} className="bg-white border rounded-lg p-4 hover:shadow-md transition">
                  <h3 className="font-semibold text-blue-600 mb-1">{server.name}</h3>
                  <p className="text-sm text-gray-600 mb-2 line-clamp-2">{server.description}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>⭐ {server.github_stars}</span>
                    <span>⬇ {server.downloads}</span>
                  </div>
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {server.tags?.slice(0, 3).map((tag) => (
                      <span key={tag} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            <div className="flex justify-center gap-2 mt-8">
              {Array.from({ length: Math.min(totalPages, 10) }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setPage(i + 1)}
                  className={`px-3 py-1 rounded ${
                    page === i + 1 ? "bg-blue-600 text-white" : "bg-gray-100"
                  }`}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </>
        )}
      </main>
    </>
  );
}
