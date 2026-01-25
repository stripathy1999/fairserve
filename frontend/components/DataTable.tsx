type Column = {
  key: string;
  label: string;
};

type DataTableProps = {
  columns: Column[];
  rows: Array<Record<string, any>>;
};

export function DataTable({ columns, rows }: DataTableProps) {
  return (
    <div className="overflow-auto rounded-lg border border-zinc-200 bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-zinc-100 text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={idx} className="border-t border-zinc-200">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-2 text-zinc-700">
                  {String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td
                className="px-4 py-6 text-center text-sm text-zinc-500"
                colSpan={columns.length}
              >
                No data available.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
