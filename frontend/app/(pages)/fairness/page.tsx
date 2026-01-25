"use client";

import { useEffect, useMemo, useState } from "react";

type FairnessRow = {
  neighborhood?: string;
  service_type?: string;
  p50_hr?: number;
  p90_hr?: number;
  ratio_p90?: number;
  rank?: number;
  worst_k_flag?: boolean;
};

type SortState = {
  key: keyof FairnessRow;
  direction: "asc" | "desc";
};

const columns: Array<{ key: keyof FairnessRow; label: string }> = [
  { key: "neighborhood", label: "Neighborhood" },
  { key: "service_type", label: "Service" },
  { key: "p50_hr", label: "p50 (hrs)" },
  { key: "p90_hr", label: "p90 (hrs)" },
  { key: "ratio_p90", label: "Ratio p90" },
  { key: "rank", label: "Rank" },
  { key: "worst_k_flag", label: "Worst K" },
];

export default function FairnessPage() {
  const [rows, setRows] = useState<FairnessRow[]>([]);
  const [sort, setSort] = useState<SortState>({ key: "ratio_p90", direction: "desc" });

  useEffect(() => {
    fetch("/api/zone2/fairness_metrics", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => setRows(data.metrics || []))
      .catch(() => setRows([]));
  }, []);

  const sortedRows = useMemo(() => {
    const sorted = [...rows];
    sorted.sort((a, b) => {
      const aVal = a[sort.key];
      const bVal = b[sort.key];
      if (aVal === undefined || aVal === null) return 1;
      if (bVal === undefined || bVal === null) return -1;
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sort.direction === "asc" ? aVal - bVal : bVal - aVal;
      }
      return sort.direction === "asc"
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
    return sorted;
  }, [rows, sort]);

  const topWorst = useMemo(() => {
    return [...rows]
      .sort((a, b) => (b.ratio_p90 ?? 0) - (a.ratio_p90 ?? 0))
      .slice(0, 5);
  }, [rows]);

  const toggleSort = (key: keyof FairnessRow) => {
    setSort((prev) => {
      if (prev.key === key) {
        return { key, direction: prev.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "desc" };
    });
  };

  return (
    <main className="p-8 space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Fairness Metrics</h1>
          <p className="text-sm text-zinc-500">
            Sorted by {sort.key} ({sort.direction})
          </p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Top 5 worst</p>
          <div className="mt-2 space-y-1">
            {topWorst.map((row) => (
              <div key={`${row.neighborhood}-${row.service_type}`} className="flex gap-2">
                <span className="font-medium text-zinc-900">{row.neighborhood}</span>
                <span className="text-zinc-500">
                  {(row.ratio_p90 ?? 0).toFixed(2)}×
                </span>
              </div>
            ))}
            {topWorst.length === 0 ? (
              <span className="text-zinc-400">No data</span>
            ) : null}
          </div>
        </div>
      </header>

      <div className="overflow-auto rounded-lg border border-zinc-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-zinc-100 text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-2 cursor-pointer"
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row, idx) => (
              <tr
                key={`${row.neighborhood}-${idx}`}
                className={`border-t border-zinc-200 ${
                  row.worst_k_flag ? "bg-rose-50" : ""
                }`}
              >
                <td className="px-4 py-2 text-zinc-700">{row.neighborhood}</td>
                <td className="px-4 py-2 text-zinc-700">{row.service_type}</td>
                <td className="px-4 py-2 text-zinc-700">
                  {(row.p50_hr ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2 text-zinc-700">
                  {(row.p90_hr ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2 text-zinc-700">
                  {(row.ratio_p90 ?? 0).toFixed(2)}
                </td>
                <td className="px-4 py-2 text-zinc-700">{row.rank ?? "-"}</td>
                <td className="px-4 py-2">
                  {row.worst_k_flag ? (
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700">
                      Worst K
                    </span>
                  ) : (
                    <span className="text-zinc-400">—</span>
                  )}
                </td>
              </tr>
            ))}
            {sortedRows.length === 0 ? (
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
    </main>
  );
}
