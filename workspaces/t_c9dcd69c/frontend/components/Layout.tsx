"""Layout component for MCPHub frontend."""
import React from "react";
import Link from "next/link";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-white border-b px-4 py-3 flex items-center justify-between">
        <Link href="/" className="text-xl font-bold text-blue-600">
          MCPHub
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href="/servers" className="text-gray-600 hover:text-blue-600">
            Servers
          </Link>
          <Link href="/submit" className="text-gray-600 hover:text-blue-600">
            Submit
          </Link>
          <Link href="/analytics" className="text-gray-600 hover:text-blue-600">
            Analytics
          </Link>
        </div>
      </nav>
      <main className="flex-1">{children}</main>
      <footer className="bg-white border-t py-4 text-center text-sm text-gray-500">
        MCPHub v1.0.0 — Universal MCP Server Registry
      </footer>
    </div>
  );
}
