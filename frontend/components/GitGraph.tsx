interface GitOp {
  operation: string;
  branch_name: string | null;
  commit_sha: string | null;
  commit_message: string | null;
  function_id: string | null;
}

const LANE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"];
const ROW_H = 26;
const LANE_W = 18;
const LEFT_PAD = 10;

export function GitGraph({ operations }: { operations: GitOp[] }) {
  // Build commits list from operations (commit + merge + init)
  const commits = operations.filter(
    (op) => op.operation === "commit" || op.operation === "merge" || op.operation === "init"
  );

  // Assign lanes by branch name
  const branchLanes: Record<string, number> = { main: 0 };
  let nextLane = 1;
  for (const op of operations) {
    if (op.branch_name && !(op.branch_name in branchLanes) && op.operation === "create_branch") {
      branchLanes[op.branch_name] = nextLane++;
    }
  }

  // Build parent map from operations
  const parentMap: Map<string, string> = new Map();
  for (const op of operations) {
    if (op.commit_sha && op.operation === "commit" && op.branch_name) {
      // Find previous commit on same branch
      const prev = commits.find(
        (c) => c.branch_name === op.branch_name && c.commit_sha !== op.commit_sha &&
        commits.indexOf(c) < commits.indexOf(op)
      );
      if (prev?.commit_sha) parentMap.set(op.commit_sha, prev.commit_sha);
    }
  }

  const svgHeight = commits.length * ROW_H + 20;
  const labelX = LEFT_PAD + Math.max(nextLane, 3) * LANE_W + 10;

  return (
    <div className="overflow-auto p-2" data-testid="git-graph">
      <svg width={Math.max(600, labelX + 400)} height={svgHeight} className="text-xs">
        {/* Draw edges */}
        {commits.map((commit, i) => {
          const parentSha = parentMap.get(commit.commit_sha || "");
          if (!parentSha) return null;
          const parentIdx = commits.findIndex((c) => c.commit_sha === parentSha);
          if (parentIdx < 0) return null;
          const lane = branchLanes[commit.branch_name || "main"] || 0;
          const parentLane = branchLanes[commits[parentIdx]?.branch_name || "main"] || 0;
          return (
            <line
              key={`edge-${i}`}
              x1={LEFT_PAD + lane * LANE_W}
              y1={i * ROW_H + 12}
              x2={LEFT_PAD + parentLane * LANE_W}
              y2={parentIdx * ROW_H + 12}
              stroke={LANE_COLORS[lane % LANE_COLORS.length]}
              strokeWidth={1.5}
              opacity={0.4}
            />
          );
        })}

        {/* Draw nodes */}
        {commits.map((commit, i) => {
          const lane = branchLanes[commit.branch_name || "main"] || 0;
          const cx = LEFT_PAD + lane * LANE_W;
          const cy = i * ROW_H + 12;
          const color = LANE_COLORS[lane % LANE_COLORS.length];
          const isMerge = commit.operation === "merge";
          return (
            <g key={`node-${i}`}>
              <circle cx={cx} cy={cy} r={isMerge ? 5 : 3.5} fill={color} />
              <text x={labelX} y={cy + 4} fill="#9ca3af" fontSize="11" fontFamily="monospace">
                <tspan fill="#6b7280">{(commit.commit_sha || "").slice(0, 7)}</tspan>
                {" "}{commit.commit_message || commit.operation}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
