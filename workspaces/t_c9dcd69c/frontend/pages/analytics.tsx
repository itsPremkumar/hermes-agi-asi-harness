"""Analytics dashboard page."""
import React, { useState, useEffect } from "react";
import Head from "next/head";

interface AnalyticsSummary {
  total_servers: number;
  total_downloads: number;
  total_views: number;
  top_servers: Array<{ name: string; downloads: number }>;
  category_distribution: Record<string, number>;
  daily_events: Array<{ day: string; count: number }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      const resp = await fetch(`${API_BASE}/analytics`);
      const json = await resp.json();
      setData(json);
      setLoading(false);
    };
    fetchAnalytics();
  }, []);

  if (loading || !data) {
    return <main className="max-w-7xl mx-auto px-4 py-8"><p>Loading...</p></main>;
  }

  return (
    <>
      <Head>
        <title>Analytics — MCPHub</title>
      </Head>
      <main className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Registry Analytics</h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white border rounded-lg p-6">
            <p className="text-sm text-gray-500">Total Servers</p>
            <p className="text-3xl font-bold text-blue-600">{data.total_servers}</p>
          </div>
          <div className="bg-white border rounded-lg p-6">
            <p className="text-sm text-gray-500">Total Downloads</p>
            <p className="text-3xl font-bold text-green-600">{data.total_downloads}</p>
          </div>
          <div className="bg-white border rounded-lg p-6">
            <p className="text-sm text-gray-500">Total Views</p>
            <p className="text-3xl font-bold text-purple-600">{data.total_views}</p>
          </div>
        </div>

        {/* Top Servers */}
        <div className="bg-white border rounded-lg p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Top Servers by Downloads</h2>
          <div className="space-y-2">
            {data.top_servers.map((server, i) => (
              <div key={server.name} className="flex items-center gap-4">
                <span className="text-gray-400 w-6">{i + 1}.</span>
                <span className="flex-1 font-medium">{server.name}</span>
                <span className="text-gray-500">{server.downloads} downloads</span>
              </div>
            ))}
          </div>
        </div>

        {/* Category Distribution */}
        <div className="bg-white border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Category Distribution</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(data.category_distribution).map(([cat, count]) => (
              <div key={cat} className="flex items-center justify-between bg-gray-50 rounded p-3">
                <span className="text-sm font-medium">{cat}</span>
                <span className="text-sm text-gray-500">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
