interface LogEntry {
  layer: string;
  role: string;
  content: string;
  model: string | null;
  tokens_used: number;
  cost_usd: number;
}

export function AgentPanel({
  conversations,
  selectedFn,
  onSelectFn,
  functionNames,
}: {
  conversations: Record<string, LogEntry[]>;
  selectedFn: string;
  onSelectFn: (name: string) => void;
  functionNames: string[];
}) {
  const logs = conversations[selectedFn] || [];
  const l1Logs = logs.filter((l) => l.layer === "l1");
  const l2Logs = logs.filter((l) => l.layer === "l2");
  const l3Logs = logs.filter((l) => l.layer === "l3");

  return (
    <div className="flex flex-col h-full">
      {/* Function selector tabs */}
      <div className="flex border-b border-gray-800 bg-gray-900/20 overflow-x-auto">
        {functionNames.map((fn) => (
          <button
            key={fn}
            onClick={() => onSelectFn(fn)}
            className={`px-3 py-1 text-xs whitespace-nowrap ${
              selectedFn === fn
                ? "text-blue-400 border-b border-blue-500"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {fn}
          </button>
        ))}
      </div>

      {/* Agent columns */}
      <div className="flex-1 grid grid-cols-2 gap-0 overflow-auto">
        {/* Spec Agent (L1) */}
        <div className="border-r border-gray-800 p-3 overflow-auto">
          <div className="text-xs text-blue-400 font-semibold mb-2 uppercase tracking-wide">
            Spec Agent (L1)
          </div>
          <div className="space-y-2">
            {l1Logs.filter((l) => l.role === "assistant").map((log, i) => (
              <div key={i} className="bg-gray-800/50 rounded p-2 border border-gray-800 text-xs">
                <div className="text-green-400 font-mono mb-1">
                  {log.model} — {log.tokens_used} tokens (${log.cost_usd.toFixed(4)})
                </div>
                <div className="text-gray-300 whitespace-pre-wrap max-h-40 overflow-auto">
                  {log.content.slice(0, 500)}{log.content.length > 500 ? "..." : ""}
                </div>
              </div>
            ))}
            {l1Logs.length === 0 && (
              <div className="text-gray-600 text-xs">No L1 activity</div>
            )}
          </div>
        </div>

        {/* Reviewer (L2) + Test Agent (L3) */}
        <div className="p-3 overflow-auto">
          <div className="text-xs text-purple-400 font-semibold mb-2 uppercase tracking-wide">
            Reviewer (L2)
          </div>
          <div className="space-y-2">
            {l2Logs.filter((l) => l.role === "assistant").map((log, i) => {
              const isRejection = log.content.toUpperCase().startsWith("REJECTED");
              return (
                <div
                  key={i}
                  className={`rounded p-2 border text-xs ${
                    isRejection
                      ? "bg-red-900/20 border-red-900/50"
                      : "bg-green-900/20 border-green-900/50"
                  }`}
                >
                  <div className={`font-mono mb-1 ${isRejection ? "text-red-400" : "text-green-400"}`}>
                    {isRejection ? "✗ Rejected" : "✓ Accepted"} — {log.model}
                  </div>
                  <div className="text-gray-300 whitespace-pre-wrap max-h-40 overflow-auto">
                    {log.content.slice(0, 500)}{log.content.length > 500 ? "..." : ""}
                  </div>
                </div>
              );
            })}
            {l2Logs.length === 0 && (
              <div className="text-gray-600 text-xs">No L2 activity</div>
            )}
          </div>

          {l3Logs.length > 0 && (
            <>
              <div className="text-xs text-emerald-400 font-semibold mt-3 mb-2 uppercase tracking-wide">
                Test Agent (L3)
              </div>
              <div className="space-y-2">
                {l3Logs.filter((l) => l.role === "assistant").map((log, i) => (
                  <div key={i} className="bg-gray-800/50 rounded p-2 border border-gray-800 text-xs">
                    <div className="text-emerald-400 font-mono mb-1">
                      {log.model} — {log.tokens_used} tokens
                    </div>
                    <div className="text-gray-300 whitespace-pre-wrap max-h-40 overflow-auto">
                      {log.content.slice(0, 500)}{log.content.length > 500 ? "..." : ""}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
