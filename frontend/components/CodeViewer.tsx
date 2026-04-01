export function CodeViewer({ code }: { code: string }) {
  let inGherkin = false;
  return (
    <pre className="text-sm font-mono text-gray-300 p-3 overflow-auto leading-relaxed">
      {code.split("\n").map((line, i) => {
        if (line.includes("```gherkin")) {
          inGherkin = true;
        }
        const isGherkinLine = inGherkin;
        if (line.includes("```") && inGherkin && !line.includes("gherkin")) {
          inGherkin = false;
        }

        const isKeyword =
          /^\s*(Feature:|Rule:|Scenario:|When |Then |And )/.test(line);
        return (
          <div
            key={i}
            className={`flex ${isGherkinLine ? "bg-emerald-950/30" : ""}`}
          >
            <span className="text-gray-700 w-8 text-right pr-3 select-none shrink-0">
              {i + 1}
            </span>
            <span
              className={
                isGherkinLine && isKeyword
                  ? "text-emerald-400"
                  : isGherkinLine
                    ? "text-emerald-300/70"
                    : ""
              }
            >
              {line}
            </span>
          </div>
        );
      })}
    </pre>
  );
}
