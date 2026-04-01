"use client";

import { useState } from "react";
import { FileTree, FileNode } from "@/components/FileTree";
import { CodeViewer } from "@/components/CodeViewer";
import { StatusTable, FunctionStatus } from "@/components/StatusTable";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function flattenFunctions(nodes: FileNode[]): FunctionStatus[] {
  const result: FunctionStatus[] = [];
  for (const node of nodes) {
    if (node.functions) {
      for (const fn of node.functions) {
        result.push({
          name: fn.name,
          file: fn.file,
          line: fn.line,
          status: "pending",
          l1: "pending",
          l2: "pending",
          l3: "pending",
          action: "pending",
        });
      }
    }
    if (node.children) {
      result.push(...flattenFunctions(node.children));
    }
  }
  return result;
}

function countFunctions(nodes: FileNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.functions) count += node.functions.length;
    if (node.children) count += countFunctions(node.children);
  }
  return count;
}

// ============================================================
// Repo Input View
// ============================================================

function RepoInput({
  onLoaded,
}: {
  onLoaded: (tree: FileNode[], repoName: string) => void;
}) {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoad = async () => {
    if (!repoUrl.trim()) return;
    setLoading(true);
    setError(null);
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
      onLoaded(data.tree, data.repo_name);
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
    </main>
  );
}

// ============================================================
// Pipeline View
// ============================================================

function PipelineView({
  tree,
  repoName,
}: {
  tree: FileNode[];
  repoName: string;
}) {
  const [selected, setSelected] = useState("");
  const [selectedFile, setSelectedFile] = useState("");
  const [codeTab, setCodeTab] = useState<"source" | "tests">("source");
  const [bottomTab, setBottomTab] = useState<"status" | "agents">("status");
  const [sourceCode, setSourceCode] = useState("");
  const [functions] = useState<FunctionStatus[]>(() => flattenFunctions(tree));

  const handleSelectFunction = async (name: string, file: string) => {
    setSelected(name);
    setSelectedFile(file);
    setCodeTab("source");
    try {
      const res = await fetch(
        `${BACKEND_URL}/api/repo/file/${encodeURIComponent(file)}`
      );
      if (res.ok) {
        const data = await res.json();
        setSourceCode(data.content);
      }
    } catch {
      setSourceCode("// Failed to load file");
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-bold">FV Pipeline</h1>
          <span className="text-xs text-gray-500">{repoName}</span>
          <span className="text-xs text-green-400">
            {countFunctions(tree)} functions
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500" data-testid="budget-display">
            Budget: $0.00 / $2.00
          </span>
          <button
            className="bg-green-600 hover:bg-green-500 text-white px-3 py-1 rounded text-xs font-medium"
            data-testid="generate-button"
          >
            Generate Specs
          </button>
        </div>
      </div>

      {/* Top half: file tree + code */}
      <div className="h-1/2 flex overflow-hidden">
        <div
          className="w-56 border-r border-gray-800 overflow-y-auto bg-gray-900/50 py-2"
          data-testid="file-tree"
        >
          <FileTree
            nodes={tree}
            selected={selected}
            onSelect={handleSelectFunction}
          />
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex border-b border-gray-800 bg-gray-900/30">
            {(["source", "tests"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setCodeTab(tab)}
                className={`px-4 py-1.5 text-xs font-medium capitalize border-b-2 transition-colors ${
                  codeTab === tab
                    ? "border-blue-500 text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-300"
                }`}
                data-testid={`tab-${tab}`}
              >
                {tab}
              </button>
            ))}
            {selected && (
              <div className="ml-auto px-3 py-1.5 text-xs text-gray-600 font-mono">
                {selected} — {selectedFile}
              </div>
            )}
          </div>

          <div
            className="flex-1 overflow-auto bg-gray-950"
            data-testid="code-panel"
          >
            {sourceCode && codeTab === "source" ? (
              <CodeViewer code={sourceCode} />
            ) : codeTab === "tests" ? (
              <div className="p-4 text-gray-500 text-sm">
                No tests generated yet. Click &quot;Generate Specs&quot; to
                start the pipeline.
              </div>
            ) : (
              <div className="p-4 text-gray-500 text-sm">
                Select a function from the file tree to view its source code.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom half: status / agents */}
      <div className="h-1/2 border-t border-gray-800 flex flex-col">
        <div className="flex border-b border-gray-800 bg-gray-900/30">
          {(["status", "agents"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setBottomTab(tab)}
              className={`px-4 py-1.5 text-xs font-medium capitalize border-b-2 transition-colors ${
                bottomTab === tab
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
              data-testid={`bottom-tab-${tab}`}
            >
              {tab === "status" ? "Status" : "Agents & Git"}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-auto">
          {bottomTab === "status" && (
            <StatusTable
              functions={functions}
              selected={selected}
              onSelect={(name) => {
                const fn = functions.find((f) => f.name === name);
                if (fn) handleSelectFunction(name, fn.file);
              }}
            />
          )}
          {bottomTab === "agents" && (
            <div className="p-4 text-gray-500 text-sm">
              Agent activity will appear here after running the pipeline.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Main
// ============================================================

export default function Home() {
  const [loaded, setLoaded] = useState(false);
  const [tree, setTree] = useState<FileNode[]>([]);
  const [repoName, setRepoName] = useState("");

  if (loaded) {
    return <PipelineView tree={tree} repoName={repoName} />;
  }

  return (
    <RepoInput
      onLoaded={(t, name) => {
        setTree(t);
        setRepoName(name);
        setLoaded(true);
      }}
    />
  );
}
