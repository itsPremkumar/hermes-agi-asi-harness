"""Frontend pages for MCPHub."""
import React from "react";
import Head from "next/head";
import { useState } from "react";

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
  health_score: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function Home() {
  const [query, setQuery] = useState("");
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams({ q: query, per_page: "20" });
      const resp = await fetch(`${API_BASE}/search?${params}`);
      const data = await resp.json();
      setServers(data.results || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error("Search failed:", err);
    }
    setLoading(false);
  };

  return (
    <>
      <Head>
        <title>MCPHub — Universal MCP Server Registry</title>
        <meta name="description" content="Discover, install, and manage MCP servers" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-blue-600">MCPHub</span>
              <span className="text-sm text-gray-500">v1.0.0</span>
            </div>
            <nav className="flex gap-4">
              <a href="/" className="text-gray-700 hover:text-blue-600">Home</a>
              <a href="/servers" className="text-gray-700 hover:text-blue-600">Servers</a>
              <a href="/submit" className="text-gray-700 hover:text-blue-600">Submit</a>
              <a href="/analytics" className="text-gray-700 hover:text-blue-600">Analytics</a>
            </nav>
          </div>
        </header>

        {/* Hero */}
        <section className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white py-20">
          <div className="max-w-4xl mx-auto text-center px-4">
            <h1 className="text-5xl font-bold mb-4">Universal MCP Server Registry</h1>
            <p className="text-xl text-blue-100 mb-8">
              Discover, install, and manage 500+ MCP servers for AI agents
            </p>
            <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl mx-auto">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search MCP servers..."
                className="flex-1 px-4 py-3 rounded-lg text-gray-900 text-lg"
              />
              <button
                type="submit"
                className="px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50"
              >
                Search
              </button>
            </form>
          </div>
        </section>

        {/* Results */}
        <section className="max-w-7xl mx-auto px-4 py-12">
          {loading && <p className="text-center text-gray-500">Loading...</p>}
          
          {!loading && servers.length > 0 && (
            <>
              <p className="text-gray-600 mb-4">{total} servers found</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {servers.map((server) => (
                  <div key={server.id} className="bg-white rounded-lg shadow p-6 hover:shadow-md transition">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-lg font-semibold text-blue-600">{server.name}</h3>
                      <span className="text-xs bg-gray-100 px-2 py-1 rounded">{server.mcp_transport}</span>
                    </div>
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">{server.description}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span>⭐ {server.github_stars}</span>
                      <span>⬇ {server.downloads}</span>
                      <span>by {server.author}</span>
                    </div>
                    <div className="mt-3 flex gap-1 flex-wrap">
                      {server.tags?.map((tag) => (
                        <span key={tag} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {!loading && servers.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500 text-lg">Search for MCP servers or browse by category</p>
            </div>
          )}
        </section>

        {/* Footer */}
        <footer className="bg-white border-t py-8">
          <div className="max-w-7xl mx-auto px-4 text-center text-gray-500">
            <p>MCPHub v1.0.0 — Built with FastAPI, Next.js, PostgreSQL, Redis</p>
            <p className="mt-2">
              <a href="/docs" className="text-blue-600 hover:underline">API Docs</a>
              {" | "}
              <a href="https://github.com/itsPremkumar/mcphub" className="text-blue-600 hover:underline">GitHub</a>
            </p>
          </div>
        </footer>
      </main>
    </>
  );
}
