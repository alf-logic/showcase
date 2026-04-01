"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileTree, FileNode } from "@/components/FileTree";
import { CodeViewer } from "@/components/CodeViewer";
import { StatusTable, FunctionStatus } from "@/components/StatusTable";
import { AgentPanel } from "@/components/AgentPanel";
import { GitGraph } from "@/components/GitGraph";

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

function statusToAction(status: string): string {
  switch (status) {
    case "covered": return "merged";
    case "bug_suspect": return "fix_pr";
    case "needs_refactor": return "issue";
    case "test_failed": return "retry";
    default: return "pending";
  }
}

function layerStatus(fnStatus: string, layer: "l1" | "l2" | "l3"): string {
  const statusOrder = ["pending", "l1_in_progress", "l1_done", "l2_in_progress", "l2_done", "l2_rejected", "l3_in_progress", "l3_done", "l3_failed", "covered", "bug_suspect", "needs_refactor", "test_failed"];
  const idx = statusOrder.indexOf(fnStatus);
  if (layer === "l1") {
    if (idx >= 2) return "done";
    if (idx === 1) return "processing";
    return "pending";
  }
  if (layer === "l2") {
    if (fnStatus === "needs_refactor" || fnStatus === "l2_rejected") return "rejected";
    if (idx >= 4) return "done";
    if (idx === 3) return "processing";
    if (idx >= 2) return "pending";
    return "pending";
  }
  if (layer === "l3") {
    if (fnStatus === "needs_refactor" || fnStatus === "l2_rejected") return "skipped";
    if (fnStatus === "covered") return "done";
    if (fnStatus === "bug_suspect" || fnStatus === "test_failed" || fnStatus === "l3_failed") return "failed";
    if (idx >= 6 && idx <= 7) return "processing";
    if (idx >= 4) return "pending";
    return "pending";
  }
  return "pending";
}

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
  const [functions, setFunctions] = useState<FunctionStatus[]>(() => flattenFunctions(tree));
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineComplete, setPipelineComplete] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [budget, setBudget] = useState({ used: 0, limit: 2.0 });
  const [conversations, setConversations] = useState<Record<string, any[]>>({});
  const [gitOps, setGitOps] = useState<any[]>([]);
  const [agentFn, setAgentFn] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);

  // Fetch debug data when pipeline completes
  useEffect(() => {
    if (!pipelineComplete || !runId) return;
    (async () => {
      try {
        const [convRes, gitRes] = await Promise.all([
          fetch(`${BACKEND_URL}/api/debug/conversations/${runId}`),
          fetch(`${BACKEND_URL}/api/debug/git-graph/${runId}`),
        ]);
        if (convRes.ok) {
          const data = await convRes.json();
          setConversations(data.conversations);
          const names = Object.keys(data.conversations);
          if (names.length > 0 && !agentFn) setAgentFn(names[0]);
        }
        if (gitRes.ok) {
          const data = await gitRes.json();
          setGitOps(data.operations);
        }
      } catch (err) {
        console.error("Failed to fetch debug data:", err);
      }
    })();
  }, [pipelineComplete, runId]);

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

  const updateFunctionStatus = useCallback((name: string, updates: Partial<FunctionStatus>) => {
    setFunctions((prev) =>
      prev.map((fn) => (fn.name === name ? { ...fn, ...updates } : fn))
    );
  }, []);

  const handleGenerate = async () => {
    setPipelineRunning(true);
    setPipelineComplete(false);

    // Set all to pending with running action
    setFunctions((prev) => prev.map((fn) => ({ ...fn, action: "running" })));

    try {
      const res = await fetch(`${BACKEND_URL}/api/pipeline/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ budget_limit: 2.0 }),
      });
      const data = await res.json();
      const newRunId: string = data.run_id;
      setRunId(newRunId);

      // Connect SSE
      const es = new EventSource(`${BACKEND_URL}/api/pipeline/stream/${newRunId}`);
      eventSourceRef.current = es;

      es.addEventListener("function_start", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        updateFunctionStatus(d.name, { status: "l1_in_progress", l1: "processing", action: "running" });
      });

      es.addEventListener("layer_start", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        updateFunctionStatus(d.name, {
          status: `${d.layer}_in_progress`,
          [d.layer]: "processing",
        } as Partial<FunctionStatus>);
      });

      es.addEventListener("layer_complete", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        updateFunctionStatus(d.name, {
          [d.layer]: "done",
        } as Partial<FunctionStatus>);
      });

      es.addEventListener("function_status", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        const status: string = d.status;
        updateFunctionStatus(d.name, {
          status,
          l1: layerStatus(status, "l1"),
          l2: layerStatus(status, "l2"),
          l3: layerStatus(status, "l3"),
          action: statusToAction(status),
        });
      });

      es.addEventListener("budget_update", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        setBudget({ used: d.used, limit: d.limit });
      });

      es.addEventListener("pipeline_complete", () => {
        setPipelineRunning(false);
        setPipelineComplete(true);
      });

      es.addEventListener("done", () => {
        es.close();
        eventSourceRef.current = null;
        setPipelineRunning(false);
        setPipelineComplete(true);
      });

      es.addEventListener("pipeline_error", (e: MessageEvent) => {
        const d = JSON.parse(e.data);
        console.error("Pipeline error:", d.error);
        es.close();
        setPipelineRunning(false);
      });

    } catch (err) {
      console.error("Failed to start pipeline:", err);
      setPipelineRunning(false);
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
          {pipelineRunning && (
            <span className="text-xs text-blue-400 animate-pulse" data-testid="pipeline-running">
              Pipeline running...
            </span>
          )}
          {pipelineComplete && (
            <span className="text-xs text-green-400" data-testid="pipeline-complete">
              Pipeline complete
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500" data-testid="budget-display">
            Budget: ${budget.used.toFixed(4)} / ${budget.limit.toFixed(2)}
          </span>
          <button
            onClick={handleGenerate}
            disabled={pipelineRunning}
            className={`px-3 py-1 rounded text-xs font-medium ${
              pipelineRunning
                ? "bg-gray-700 text-gray-400 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-500 text-white"
            }`}
            data-testid="generate-button"
          >
            {pipelineRunning ? "Running..." : "Generate Specs"}
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
            Object.keys(conversations).length > 0 ? (
              <div className="flex h-full">
                <div className="flex-1 border-r border-gray-800 overflow-auto">
                  <AgentPanel
                    conversations={conversations}
                    selectedFn={agentFn}
                    onSelectFn={setAgentFn}
                    functionNames={Object.keys(conversations)}
                  />
                </div>
                <div className="w-[480px] overflow-auto">
                  <div className="text-xs text-gray-500 font-semibold px-3 py-1.5 border-b border-gray-800 uppercase tracking-wide">
                    Git Graph
                  </div>
                  <GitGraph operations={gitOps} />
                </div>
              </div>
            ) : (
              <div className="p-4 text-gray-500 text-sm">
                {pipelineComplete ? "Loading agent data..." : "Agent activity will appear here after running the pipeline."}
              </div>
            )
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
