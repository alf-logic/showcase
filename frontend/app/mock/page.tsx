"use client";

import { useState } from "react";

// ============================================================
// MOCK DATA
// ============================================================

const MOCK_FUNCTIONS = [
  { name: "hash_key", file: "hashmap/hashmap.py", line: 15, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "put", file: "hashmap/hashmap.py", line: 28, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "get", file: "hashmap/hashmap.py", line: 57, status: "bug_suspect", l1: "done", l2: "done", l3: "failed", action: "fix_pr" },
  { name: "resize", file: "hashmap/hashmap.py", line: 78, status: "needs_refactor", l1: "done", l2: "rejected", l3: "skipped", action: "issue" },
  { name: "delete", file: "hashmap/hashmap.py", line: 118, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "split_file", file: "chunker/chunker.py", line: 12, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "calculate_boundaries", file: "chunker/chunker.py", line: 30, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "merge_chunks", file: "chunker/chunker.py", line: 54, status: "bug_suspect", l1: "done", l2: "done", l3: "failed", action: "fix_pr" },
  { name: "validate_checksum", file: "chunker/chunker.py", line: 75, status: "covered", l1: "done", l2: "done", l3: "done", action: "merged" },
  { name: "handle_partial_chunk", file: "chunker/chunker.py", line: 85, status: "test_failed", l1: "done", l2: "done", l3: "failed", action: "retry" },
];

const MOCK_SOURCE = `def hash_key(key: str, capacity: int) -> int:
    """Compute a deterministic hash index for a string key.

    Uses FNV-1a inspired hashing: XOR each byte with a running hash
    then multiply by a prime. Returns index in [0, capacity).

    \`\`\`gherkin
    Feature: hash_key

      Rule: Determinism
        Scenario: Same input produces same output
          When hash_key is called twice with key="hello" and capacity=10
          Then both calls return the same integer

      Rule: Output range
        Scenario: Result is within bounds
          When hash_key is called with any key and capacity=100
          Then the result is >= 0 and < 100

      Rule: Distribution
        Scenario: Different keys produce different hashes
          When hash_key is called with "alice" and "bob" and capacity=1000
          Then the results are different

      Rule: Edge cases
        Scenario: Empty string is valid input
          When hash_key is called with key="" and capacity=10
          Then a valid integer in [0, 10) is returned
    \`\`\`
    """
    h: int = 0x811C9DC5
    for byte in key.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h % capacity`;

const MOCK_SPEC = `Feature: hash_key

  Rule: Determinism
    Scenario: Same input produces same output
      When hash_key is called twice with key="hello" and capacity=10
      Then both calls return the same integer

  Rule: Output range
    Scenario: Result is within bounds
      When hash_key is called with any key and capacity=100
      Then the result is >= 0 and < 100

  Rule: Distribution
    Scenario: Different keys produce different hashes
      When hash_key is called with "alice" and "bob" and capacity=1000
      Then the results are different

  Rule: Edge cases
    Scenario: Empty string is valid input
      When hash_key is called with key="" and capacity=10
      Then a valid integer in [0, 10) is returned`;

const MOCK_TESTS = `import pytest
from hashmap.hashmap import hash_key

def test_hash_key_determinism():
    # When
    result1 = hash_key("hello", 10)
    result2 = hash_key("hello", 10)
    # Then
    assert result1 == result2

def test_hash_key_range():
    # When
    result = hash_key("test", 100)
    # Then
    assert 0 <= result < 100

def test_hash_key_distribution():
    # When
    r1 = hash_key("alice", 1000)
    r2 = hash_key("bob", 1000)
    # Then
    assert r1 != r2

def test_hash_key_empty_string():
    # When
    result = hash_key("", 10)
    # Then
    assert 0 <= result < 10`;

const MOCK_TEST_OUTPUT = `===== test session starts =====
_fv_generated_test.py::test_hash_key_determinism PASSED
_fv_generated_test.py::test_hash_key_range PASSED
_fv_generated_test.py::test_hash_key_distribution PASSED
_fv_generated_test.py::test_hash_key_empty_string PASSED
===== 4 passed in 0.01s =====`;

const MOCK_GIT_COMMITS = [
  { sha: "a1b2c3", branch: "main", message: "Initial commit", parents: [], x: 0 },
  { sha: "d4e5f6", branch: "spec/hash_key", message: "L1: add spec for hash_key", parents: ["a1b2c3"], x: 1 },
  { sha: "g7h8i9", branch: "spec/hash_key", message: "L2: refined spec", parents: ["d4e5f6"], x: 2 },
  { sha: "j0k1l2", branch: "spec/hash_key", message: "L3: tests for hash_key", parents: ["g7h8i9"], x: 3 },
  { sha: "m3n4o5", branch: "main", message: "Merge spec/hash_key → main", parents: ["a1b2c3", "j0k1l2"], x: 4 },
  { sha: "p6q7r8", branch: "spec/get", message: "L1: add spec for get", parents: ["m3n4o5"], x: 5 },
  { sha: "s9t0u1", branch: "spec/get", message: "L2: refined spec", parents: ["p6q7r8"], x: 6 },
  { sha: "v2w3x4", branch: "spec/get", message: "L3: tests (bug found)", parents: ["s9t0u1"], x: 7 },
  { sha: "y5z6a7", branch: "spec/resize", message: "L1: add spec for resize", parents: ["m3n4o5"], x: 5 },
  { sha: "b8c9d0", branch: "spec/resize", message: "L2: REJECTED", parents: ["y5z6a7"], x: 6 },
];

const MOCK_AGENT_CONVERSATIONS = {
  hash_key: {
    spec_agent: [
      { role: "working", content: "Analyzing hash_key — pure FNV-1a hash function" },
      { role: "commit", sha: "d4e5f6", content: "Generated L1 spec with 4 scenarios: determinism, range, distribution, empty string" },
    ],
    reviewer: [
      { role: "review", content: "Spec is complete and accurate. Function is pure and simple." },
      { role: "accept", sha: "g7h8i9", content: "Accepted. Minor refinement: clarified edge case scenario." },
    ],
    test_agent: [
      { role: "commit", sha: "j0k1l2", content: "Generated 4 tests — all passed ✓" },
    ],
    result: "merged",
  },
  resize: {
    spec_agent: [
      { role: "working", content: "Analyzing resize — complex function with multiple responsibilities" },
      { role: "commit", sha: "y5z6a7", content: "Generated L1 spec covering rehashing, tombstone skipping, load factor validation" },
    ],
    reviewer: [
      { role: "review", content: "Function has too many mixed responsibilities: rehashing, validation, statistics, error handling" },
      { role: "reject", sha: "b8c9d0", content: "REJECTED: Needs refactoring — separate migration logic from validation" },
    ],
    test_agent: [],
    result: "not_merged",
  },
  get: {
    spec_agent: [
      { role: "working", content: "Analyzing get — linear probing lookup" },
      { role: "commit", sha: "p6q7r8", content: "Generated L1 spec for probe loop behavior" },
    ],
    reviewer: [
      { role: "review", content: "Spec covers probing behavior. Function is simple enough to test." },
      { role: "accept", sha: "s9t0u1", content: "Accepted. Highlighted probe loop boundary." },
    ],
    test_agent: [
      { role: "commit", sha: "v2w3x4", content: "Generated tests — test_probe_boundary FAILED: off-by-one in range(capacity-1)" },
    ],
    result: "bug_found",
  },
};

// ============================================================
// COMPONENTS
// ============================================================

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-gray-800 text-gray-400 border-gray-700",
    processing: "bg-blue-900/50 text-blue-400 border-blue-700",
    done: "bg-green-900/50 text-green-400 border-green-700",
    failed: "bg-red-900/50 text-red-400 border-red-700",
    rejected: "bg-orange-900/50 text-orange-400 border-orange-700",
    skipped: "bg-gray-800 text-gray-500 border-gray-700",
    covered: "bg-green-900/50 text-green-400 border-green-700",
    bug_suspect: "bg-yellow-900/50 text-yellow-400 border-yellow-700",
    needs_refactor: "bg-blue-900/50 text-blue-400 border-blue-700",
    test_failed: "bg-red-900/50 text-red-400 border-red-700",
  };
  const labels: Record<string, string> = {
    pending: "--", done: "✓", failed: "✗", rejected: "✗", skipped: "--",
    covered: "covered ✓", bug_suspect: "bug ⚠", needs_refactor: "refactor", test_failed: "failed ✗",
    processing: "...",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs border ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  );
}

function LayerBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    done: "text-green-400", failed: "text-red-400", rejected: "text-orange-400",
    skipped: "text-gray-600", pending: "text-gray-600", processing: "text-blue-400",
  };
  const labels: Record<string, string> = {
    done: "✓", failed: "✗", rejected: "✗", skipped: "--", pending: "--", processing: "⟳",
  };
  return <span className={`text-sm font-mono ${styles[status] || "text-gray-600"}`}>{labels[status] || "--"}</span>;
}

// ============================================================
// VIEW 1: Three-panel IDE layout
// ============================================================

function MockFileTree({ selected, onSelect }: { selected: string; onSelect: (name: string) => void }) {
  const dirs: Record<string, typeof MOCK_FUNCTIONS> = {};
  for (const fn of MOCK_FUNCTIONS) {
    const dir = fn.file.split("/")[0];
    if (!dirs[dir]) dirs[dir] = [];
    dirs[dir].push(fn);
  }

  return (
    <div className="text-sm font-mono">
      {Object.entries(dirs).map(([dir, fns]) => (
        <div key={dir}>
          <div className="text-blue-400 font-semibold px-2 py-1">{dir}/</div>
          <div className="text-gray-400 px-4 py-0.5 text-xs">{fns[0].file.split("/")[1]}</div>
          {fns.map((fn) => (
            <div
              key={fn.name}
              onClick={() => onSelect(fn.name)}
              className={`flex items-center gap-2 px-6 py-0.5 cursor-pointer hover:bg-gray-800 rounded ${selected === fn.name ? "bg-gray-800 text-white" : "text-gray-300"}`}
            >
              <span className="text-purple-400 text-xs">def</span>
              <span className="text-yellow-300">{fn.name}</span>
              <span className="text-gray-700 text-xs ml-auto">L{fn.line}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function MockCodeViewer({ code }: { code: string }) {
  let inGherkin = false;
  return (
    <pre className="text-sm font-mono text-gray-300 p-3 overflow-auto leading-relaxed">
      {code.split("\n").map((line, i) => {
        if (line.includes("```gherkin")) { inGherkin = true; }
        const isGherkinLine = inGherkin;
        if (line.includes("```") && inGherkin && !line.includes("gherkin")) { inGherkin = false; }

        const isKeyword = /^\s*(Feature:|Rule:|Scenario:|When |Then |And )/.test(line);
        return (
          <div key={i} className={`flex ${isGherkinLine ? "bg-emerald-950/30" : ""}`}>
            <span className="text-gray-700 w-8 text-right pr-3 select-none shrink-0">{i + 1}</span>
            <span className={isGherkinLine && isKeyword ? "text-emerald-400" : isGherkinLine ? "text-emerald-300/70" : ""}>
              {line}
            </span>
          </div>
        );
      })}
    </pre>
  );
}

function ActionBadge({ action }: { action: string }) {
  const config: Record<string, { style: string; label: string }> = {
    merged: { style: "text-green-500", label: "Merged ✓" },
    fix_pr: { style: "text-yellow-400 underline cursor-pointer hover:text-yellow-300", label: "Create Fix PR" },
    issue: { style: "text-blue-400 underline cursor-pointer hover:text-blue-300", label: "Open Issue" },
    retry: { style: "text-gray-400 underline cursor-pointer hover:text-gray-300", label: "Retry" },
    running: { style: "text-blue-400 animate-pulse", label: "Running..." },
    pending: { style: "text-gray-600", label: "--" },
  };
  const c = config[action] || config.pending;
  return <span className={`text-xs ${c.style}`}>{c.label}</span>;
}

function MockStatusTable({ functions, selected, onSelect }: { functions: typeof MOCK_FUNCTIONS; selected: string; onSelect: (name: string) => void }) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-800 text-gray-500">
          <th className="text-left py-2 px-3 font-medium w-40">Function</th>
          <th className="text-left py-2 px-2 font-medium w-32 text-xs">File</th>
          <th className="text-center py-2 px-1 font-medium w-10">L1</th>
          <th className="text-center py-2 px-1 font-medium w-10">L2</th>
          <th className="text-center py-2 px-1 font-medium w-10">L3</th>
          <th className="text-center py-2 px-2 font-medium w-24">Status</th>
          <th className="text-right py-2 px-3 font-medium">Action</th>
        </tr>
      </thead>
      <tbody>
        {functions.map((fn) => (
          <tr
            key={fn.name}
            onClick={() => onSelect(fn.name)}
            className={`border-b border-gray-900 cursor-pointer hover:bg-gray-800/50 ${selected === fn.name ? "bg-gray-800/80" : ""}`}
          >
            <td className="py-1.5 px-3 font-mono text-yellow-300 text-xs">{fn.name}</td>
            <td className="py-1.5 px-2 text-gray-600 text-xs truncate max-w-32">{fn.file.split("/")[1]}</td>
            <td className="py-1.5 px-1 text-center"><LayerBadge status={fn.l1} /></td>
            <td className="py-1.5 px-1 text-center"><LayerBadge status={fn.l2} /></td>
            <td className="py-1.5 px-1 text-center"><LayerBadge status={fn.l3} /></td>
            <td className="py-1.5 px-2 text-center"><StatusBadge status={fn.status} /></td>
            <td className="py-1.5 px-3 text-right"><ActionBadge action={fn.action} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ============================================================
// VIEW 2: Agent Panel + Git Graph
// ============================================================

function MockAgentPanel({ fnName }: { fnName: string }) {
  const conv = MOCK_AGENT_CONVERSATIONS[fnName as keyof typeof MOCK_AGENT_CONVERSATIONS];
  if (!conv) return <div className="text-gray-500 p-4 text-sm">Select a function to view agent activity</div>;

  return (
    <div className="grid grid-cols-2 gap-0 h-full">
      {/* Spec Agent */}
      <div className="border-r border-gray-800 p-3">
        <div className="text-xs text-blue-400 font-semibold mb-2 uppercase tracking-wide">Spec Agent</div>
        <div className="space-y-2">
          {conv.spec_agent.map((entry, i) => (
            <div key={i} className="text-xs">
              {entry.role === "working" && (
                <div className="text-gray-400 flex items-center gap-1.5">
                  <span className="text-blue-400">●</span> {entry.content}
                </div>
              )}
              {entry.role === "commit" && (
                <div className="bg-gray-800/50 rounded p-2 border border-gray-800">
                  <div className="text-green-400 font-mono text-xs mb-1">commit {entry.sha}</div>
                  <div className="text-gray-300">{entry.content}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Reviewer */}
      <div className="p-3">
        <div className="text-xs text-purple-400 font-semibold mb-2 uppercase tracking-wide">Reviewer</div>
        <div className="space-y-2">
          {conv.reviewer.map((entry, i) => (
            <div key={i} className="text-xs">
              {entry.role === "review" && (
                <div className="text-gray-400 flex items-center gap-1.5">
                  <span className="text-purple-400">●</span> {entry.content}
                </div>
              )}
              {entry.role === "accept" && (
                <div className="bg-green-900/20 rounded p-2 border border-green-900/50">
                  <div className="text-green-400 font-mono text-xs mb-1">✓ Accepted — commit {entry.sha}</div>
                  <div className="text-gray-300">{entry.content}</div>
                </div>
              )}
              {entry.role === "reject" && (
                <div className="bg-red-900/20 rounded p-2 border border-red-900/50">
                  <div className="text-red-400 font-mono text-xs mb-1">✗ Rejected — commit {entry.sha}</div>
                  <div className="text-gray-300">{entry.content}</div>
                </div>
              )}
            </div>
          ))}
          {conv.test_agent.length > 0 && (
            <>
              <div className="text-xs text-emerald-400 font-semibold mt-3 uppercase tracking-wide">Test Agent</div>
              {conv.test_agent.map((entry, i) => (
                <div key={i} className="text-xs">
                  <div className={`rounded p-2 border ${conv.result === "bug_found" ? "bg-yellow-900/20 border-yellow-900/50" : "bg-green-900/20 border-green-900/50"}`}>
                    <div className={`font-mono text-xs mb-1 ${conv.result === "bug_found" ? "text-yellow-400" : "text-green-400"}`}>
                      commit {entry.sha}
                    </div>
                    <div className="text-gray-300">{entry.content}</div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function MockGitGraph() {
  const LANE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"];
  const ROW_H = 28;
  const LANE_W = 20;
  const LEFT_PAD = 80;

  // Assign lanes: main=0, spec/hash_key=1, spec/get=2, spec/resize=3
  const laneMap: Record<string, number> = {
    main: 0, "spec/hash_key": 1, "spec/get": 2, "spec/resize": 3,
  };

  return (
    <div className="overflow-auto p-2">
      <svg width="600" height={MOCK_GIT_COMMITS.length * ROW_H + 20} className="text-xs">
        {/* Draw edges */}
        {MOCK_GIT_COMMITS.map((commit, i) =>
          commit.parents.map((parentSha) => {
            const parent = MOCK_GIT_COMMITS.find((c) => c.sha === parentSha);
            if (!parent) return null;
            const pi = MOCK_GIT_COMMITS.indexOf(parent);
            const x1 = LEFT_PAD + laneMap[commit.branch] * LANE_W;
            const y1 = i * ROW_H + 12;
            const x2 = LEFT_PAD + laneMap[parent.branch] * LANE_W;
            const y2 = pi * ROW_H + 12;
            return (
              <line key={`${commit.sha}-${parentSha}`} x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={LANE_COLORS[laneMap[commit.branch]] || "#666"} strokeWidth={1.5} opacity={0.5} />
            );
          })
        )}
        {/* Draw nodes */}
        {MOCK_GIT_COMMITS.map((commit, i) => {
          const lane = laneMap[commit.branch] || 0;
          const cx = LEFT_PAD + lane * LANE_W;
          const cy = i * ROW_H + 12;
          const color = LANE_COLORS[lane] || "#666";
          const isMerge = commit.parents.length > 1;
          return (
            <g key={commit.sha}>
              <circle cx={cx} cy={cy} r={isMerge ? 5 : 3.5} fill={color} />
              <text x={LEFT_PAD + 4 * LANE_W + 10} y={cy + 4} fill="#9ca3af" fontSize="11" fontFamily="monospace">
                <tspan fill="#6b7280">{commit.sha}</tspan>
                {" "}{commit.message}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ============================================================
// MAIN MOCK PAGE
// ============================================================

export default function MockPage() {
  const [selected, setSelected] = useState("hash_key");
  const [codeTab, setCodeTab] = useState<"source" | "tests">("source");
  const [bottomTab, setBottomTab] = useState<"status" | "agents">("status");
  const [agentFn, setAgentFn] = useState("hash_key");

  const codeContent: Record<string, string> = {
    source: MOCK_SOURCE,
    tests: MOCK_TESTS,
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-bold">FV Pipeline</h1>
          <span className="text-xs text-gray-500">showcase-example</span>
          <span className="text-xs text-green-400">10 functions</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">Budget: $0.009 / $2.00</span>
          <button className="bg-green-600 hover:bg-green-500 text-white px-3 py-1 rounded text-xs font-medium">
            Generate Specs
          </button>
        </div>
      </div>

      {/* Main 3-panel layout — top half */}
      <div className="h-1/2 flex overflow-hidden">
        {/* Left: File Tree */}
        <div className="w-56 border-r border-gray-800 overflow-y-auto bg-gray-900/50 py-2">
          <MockFileTree selected={selected} onSelect={(name) => { setSelected(name); setAgentFn(name); }} />
        </div>

        {/* Right: Code Viewer with Tabs */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Code tabs */}
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
              >
                {tab}
              </button>
            ))}
            <div className="ml-auto px-3 py-1.5 text-xs text-gray-600 font-mono">
              {selected} — {MOCK_FUNCTIONS.find((f) => f.name === selected)?.file}
            </div>
          </div>

          {/* Code content */}
          <div className="flex-1 overflow-auto bg-gray-950">
            <MockCodeViewer code={codeContent[codeTab]} />
            {codeTab === "tests" && (
              <div className="border-t border-gray-800 bg-gray-900/30 p-3">
                <div className="text-xs text-gray-500 mb-1 font-semibold uppercase tracking-wide">Test Output</div>
                <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap">{MOCK_TEST_OUTPUT}</pre>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Panel — 50% height */}
      <div className="h-1/2 border-t border-gray-800 flex flex-col">
        {/* Bottom panel tabs */}
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
            >
              {tab === "status" ? "Status" : "Agents & Git"}
            </button>
          ))}
        </div>

        {/* Bottom panel content */}
        <div className="flex-1 overflow-auto">
          {bottomTab === "status" && (
            <MockStatusTable functions={MOCK_FUNCTIONS} selected={selected} onSelect={(name) => { setSelected(name); setAgentFn(name); }} />
          )}
          {bottomTab === "agents" && (
            <div className="flex h-full">
              {/* Agent conversations */}
              <div className="flex-1 border-r border-gray-800 overflow-auto">
                <div className="flex border-b border-gray-800 bg-gray-900/20">
                  {["hash_key", "get", "resize"].map((fn) => (
                    <button
                      key={fn}
                      onClick={() => setAgentFn(fn)}
                      className={`px-3 py-1 text-xs ${agentFn === fn ? "text-blue-400 border-b border-blue-500" : "text-gray-500 hover:text-gray-300"}`}
                    >
                      {fn}
                    </button>
                  ))}
                </div>
                <MockAgentPanel fnName={agentFn} />
              </div>

              {/* Git graph */}
              <div className="w-[500px] overflow-auto">
                <div className="text-xs text-gray-500 font-semibold px-3 py-1.5 border-b border-gray-800 uppercase tracking-wide">Git Graph</div>
                <MockGitGraph />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
