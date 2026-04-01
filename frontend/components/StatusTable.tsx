import { ActionBadge, LayerBadge, StatusBadge } from "./StatusBadge";

export interface FunctionStatus {
  name: string;
  file: string;
  line: number;
  status: string;
  l1: string;
  l2: string;
  l3: string;
  action: string;
}

export function StatusTable({
  functions,
  selected,
  onSelect,
}: {
  functions: FunctionStatus[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  return (
    <table className="w-full text-sm" data-testid="status-table">
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
            className={`border-b border-gray-900 cursor-pointer hover:bg-gray-800/50 ${
              selected === fn.name ? "bg-gray-800/80" : ""
            }`}
            data-testid={`status-row-${fn.name}`}
          >
            <td className="py-1.5 px-3 font-mono text-yellow-300 text-xs">
              {fn.name}
            </td>
            <td className="py-1.5 px-2 text-gray-600 text-xs truncate max-w-32">
              {fn.file.split("/").pop()}
            </td>
            <td className="py-1.5 px-1 text-center">
              <LayerBadge status={fn.l1} />
            </td>
            <td className="py-1.5 px-1 text-center">
              <LayerBadge status={fn.l2} />
            </td>
            <td className="py-1.5 px-1 text-center">
              <LayerBadge status={fn.l3} />
            </td>
            <td className="py-1.5 px-2 text-center">
              <StatusBadge status={fn.status} />
            </td>
            <td className="py-1.5 px-3 text-right">
              <ActionBadge action={fn.action} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
