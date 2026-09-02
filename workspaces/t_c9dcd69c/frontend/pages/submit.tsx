"""Server submission page."""
import React, { useState } from "react";
import Head from "next/head";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function SubmitPage() {
  const [form, setForm] = useState({
    name: "",
    description: "",
    author: "",
    repository_url: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const resp = await fetch(`${API_BASE}/submissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!resp.ok) throw new Error("Submission failed");
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (submitted) {
    return (
      <main className="max-w-2xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl font-bold text-green-600 mb-4">✓ Submitted!</h1>
        <p className="text-gray-600">
          Your server has been submitted for review. You'll be notified once it's approved.
        </p>
      </main>
    );
  }

  return (
    <>
      <Head>
        <title>Submit Server — MCPHub</title>
      </Head>
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Submit an MCP Server</h1>
        <p className="text-gray-600 mb-8">
          Share your MCP server with the community. All submissions are reviewed before being listed.
        </p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1">Server Name *</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full border rounded px-3 py-2"
              placeholder="MyAwesomeServer"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full border rounded px-3 py-2 h-24"
              placeholder="What does your server do?"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Author *</label>
            <input
              type="text"
              required
              value={form.author}
              onChange={(e) => setForm({ ...form, author: e.target.value })}
              className="w-full border rounded px-3 py-2"
              placeholder="Your name or GitHub username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Repository URL</label>
            <input
              type="url"
              value={form.repository_url}
              onChange={(e) => setForm({ ...form, repository_url: e.target.value })}
              className="w-full border rounded px-3 py-2"
              placeholder="https://github.com/you/your-server"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700"
          >
            Submit for Review
          </button>
        </form>
      </main>
    </>
  );
}
