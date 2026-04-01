export interface FunctionInfo {
  name: string;
  file: string;
  line: number;
  args: string[];
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
  functions?: FunctionInfo[];
}

export function FileTree({
  nodes,
  selected,
  onSelect,
  depth = 0,
}: {
  nodes: FileNode[];
  selected: string;
  onSelect: (name: string, file: string) => void;
  depth?: number;
}) {
  return (
    <div className="text-sm font-mono">
      {nodes.map((node) => (
        <div key={node.path}>
          {node.type === "directory" ? (
            <>
              <div
                className="text-blue-400 font-semibold px-2 py-1"
                style={{ paddingLeft: `${depth * 12 + 8}px` }}
              >
                {node.name}/
              </div>
              {node.children?.map((child) =>
                child.type === "file" ? (
                  <div key={child.path}>
                    <div
                      className="text-gray-400 py-0.5 text-xs"
                      style={{ paddingLeft: `${(depth + 1) * 12 + 8}px` }}
                    >
                      {child.name}
                    </div>
                    {child.functions?.map((fn) => (
                      <div
                        key={fn.name}
                        onClick={() => onSelect(fn.name, child.path)}
                        className={`flex items-center gap-2 py-0.5 cursor-pointer hover:bg-gray-800 rounded ${
                          selected === fn.name
                            ? "bg-gray-800 text-white"
                            : "text-gray-300"
                        }`}
                        style={{ paddingLeft: `${(depth + 2) * 12 + 8}px` }}
                        data-testid={`fn-${fn.name}`}
                      >
                        <span className="text-purple-400 text-xs">def</span>
                        <span className="text-yellow-300">{fn.name}</span>
                        <span className="text-gray-700 text-xs ml-auto pr-2">
                          L{fn.line}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <FileTree
                    key={child.path}
                    nodes={[child]}
                    selected={selected}
                    onSelect={onSelect}
                    depth={depth + 1}
                  />
                )
              )}
            </>
          ) : null}
        </div>
      ))}
    </div>
  );
}
