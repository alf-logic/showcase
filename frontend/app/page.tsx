"use client";

import { useState } from "react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface FunctionInfo {
  name: string;
  file: string;
  line: number;
  args: string[];
}

interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
  functions?: FunctionInfo[];
}

function FileTree({ nodes, depth = 0 }: { nodes: FileNode[]; depth?: number }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggle = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div>
      {nodes.map((node) => (
        <div key={node.path}>
          <div
            className={`flex items-center gap-2 py-1 px-2 hover:bg-gray-800 rounded cursor-pointer text-sm font-mono`}
            style={{ paddingLeft: `${depth * 16 + 8}px` }}
            onClick={() => node.type === "directory" && toggle(node.path)}
          >
            {node.type === "directory" ? (
              <span className="text-gray-500 w-4 text-center">
                {expanded.has(node.path) ? "v" : ">"}
              </span>
            ) : (
              <span className="text-gray-600 w-4 text-center">-</span>
            )}
            <span
              className={
                node.type === "directory"
                  ? "text-blue-400 font-semibold"
                  : "text-gray-300"
              }
            >
              {node.name}
            </span>
            {node.functions && node.functions.length > 0 && (
              <span className="text-gray-600 text-xs ml-auto">
                {node.functions.length} fn
              </span>
            )}
          </div>

          {node.type === "directory" &&
            expanded.has(node.path) &&
            node.children && (
              <FileTree nodes={node.children} depth={depth + 1} />
            )}

          {node.type === "file" &&
            node.functions &&
            node.functions.map((fn) => (
              <div
                key={`${node.path}:${fn.name}`}
                className="flex items-center gap-2 py-0.5 px-2 text-sm font-mono"
                style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}
              >
                <span className="text-purple-400">def</span>
                <span className="text-yellow-300">{fn.name}</span>
                <span className="text-gray-500">
                  ({fn.args.join(", ")})
                </span>
                <span className="text-gray-700 text-xs ml-auto">
                  L{fn.line}
                </span>
              </div>
            ))}
        </div>
      ))}
    </div>
  );
}

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tree, setTree] = useState<FileNode[] | null>(null);
  const [repoName, setRepoName] = useState<string | null>(null);

  const handleLoad = async () => {
    if (!repoUrl.trim()) return;
    setLoading(true);
    setError(null);
    setTree(null);

    try {
      const res = await fetch(`${BACKEND_URL}/api/repo/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setTree(data.tree);
      setRepoName(data.repo_name);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto py-12 px-4">
      <h1 className="text-3xl font-bold mb-2">Formal Verification Pipeline</h1>
      <p className="text-gray-400 mb-8">
        Enter a git repository to analyze its functions.
      </p>

      <div className="flex gap-3 mb-6">
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLoad()}
          placeholder="Git repository path or URL..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm font-mono text-gray-100 placeholder:text-gray-600 focus:outline-none focus:border-blue-500"
          data-testid="repo-input"
        />
        <button
          onClick={handleLoad}
          disabled={loading || !repoUrl.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
          data-testid="load-button"
        >
          {loading ? "Loading..." : "Load Repository"}
        </button>
      </div>

      {error && (
        <div
          className="bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 text-red-400 text-sm mb-6"
          data-testid="error-message"
        >
          {error}
        </div>
      )}

      {tree && (
        <div
          className="bg-gray-900 border border-gray-800 rounded-lg p-4"
          data-testid="file-tree"
        >
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-800">
            <span className="text-green-400 font-semibold">{repoName}</span>
            <span className="text-gray-600 text-sm">
              — {countFunctions(tree)} functions found
            </span>
          </div>
          <FileTree nodes={tree} />
        </div>
      )}
    </main>
  );
}

function countFunctions(nodes: FileNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.functions) count += node.functions.length;
    if (node.children) count += countFunctions(node.children);
  }
  return count;
}
