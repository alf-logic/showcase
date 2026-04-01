export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-gray-800 text-gray-400 border-gray-700",
    processing: "bg-blue-900/50 text-blue-400 border-blue-700",
    covered: "bg-green-900/50 text-green-400 border-green-700",
    bug_suspect: "bg-yellow-900/50 text-yellow-400 border-yellow-700",
    needs_refactor: "bg-blue-900/50 text-blue-400 border-blue-700",
    test_failed: "bg-red-900/50 text-red-400 border-red-700",
  };
  const labels: Record<string, string> = {
    pending: "--", covered: "covered ✓", bug_suspect: "bug ⚠",
    needs_refactor: "refactor", test_failed: "failed ✗", processing: "...",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs border ${styles[status] || styles.pending}`}>
      {labels[status] || status}
    </span>
  );
}

export function LayerBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    done: "text-green-400", failed: "text-red-400", rejected: "text-orange-400",
    skipped: "text-gray-600", pending: "text-gray-600", processing: "text-blue-400 animate-pulse",
  };
  const labels: Record<string, string> = {
    done: "✓", failed: "✗", rejected: "✗", skipped: "--", pending: "--", processing: "⟳",
  };
  return <span className={`text-sm font-mono ${styles[status] || "text-gray-600"}`}>{labels[status] || "--"}</span>;
}

export function ActionBadge({ action }: { action: string }) {
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
