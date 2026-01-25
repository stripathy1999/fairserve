"use client";

import { useMemo, useState } from "react";
import { DataTable } from "@/components/DataTable";
import { KpiCard } from "@/components/KpiCard";
import { PassFailBadge } from "@/components/PassFailBadge";

type SimulateRequest = {
  policy_id: string;
  parameters: {
    capacity_shift_pct: number;
    efficiency_bonus_pct: number;
    max_reassignments: number;
  };
};

export default function PolicyPage() {
  const [cap, setCap] = useState(0.15);
  const [eff, setEff] = useState(0.04);
  const [reassign, setReassign] = useState(1);
  const [sim, setSim] = useState<any>(null);
  const [ver, setVer] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const percent = (value: number) => `${Math.round(value * 100)}%`;

  async function run() {
    setLoading(true);
    setSim(null);
    setVer(null);
    const req: SimulateRequest = {
      policy_id: `P_${Date.now()}`,
      parameters: {
        capacity_shift_pct: cap,
        efficiency_bonus_pct: eff,
        max_reassignments: reassign,
      },
    };

    const simRes = await fetch("/api/zone2/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    const simJson = await simRes.json();
    setSim(simJson);

    const verRes = await fetch("/api/zone2/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ policy_result: simJson }),
    });
    const verJson = await verRes.json();
    setVer(verJson);
    setLoading(false);
  }

  const violations = useMemo(() => ver?.violations || [], [ver]);
  const violationRows = useMemo(
    () =>
      violations.map((v: any) => ({
        constraint: v.constraint,
        neighborhood: v.neighborhood,
        observed: v.observed,
        allowed: v.allowed,
      })),
    [violations]
  );

  const neighborhoodRows = useMemo(() => {
    if (!sim?.neighborhood_effects) return [];
    return Object.entries(sim.neighborhood_effects).map(([name, metrics]: any) => ({
      neighborhood: name,
      delta_p90: percent(Number(metrics.delta_p90 ?? 0)),
      delta_backlog_pct: percent(Number(metrics.delta_backlog_pct ?? 0)),
    }));
  }, [sim]);

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Policy Lab — Simulate + Verify</h1>
      <p className="text-sm text-zinc-500">
        Adjust capacity shift and efficiency bonus to simulate policy impacts. We translate
        decimals into percentages so it is easy to read.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <label className="p-4 rounded-xl border">
          <div className="font-medium">Capacity shift</div>
          <div className="text-xs text-gray-500">0% → 30%</div>
          <input
            type="range"
            min={0}
            max={0.3}
            step={0.01}
            value={cap}
            onChange={(e) => setCap(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-sm">{percent(cap)}</div>
        </label>

        <label className="p-4 rounded-xl border">
          <div className="font-medium">Efficiency bonus</div>
          <div className="text-xs text-gray-500">0% → 20%</div>
          <input
            type="range"
            min={0}
            max={0.2}
            step={0.01}
            value={eff}
            onChange={(e) => setEff(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-sm">{percent(eff)}</div>
        </label>

        <label className="p-4 rounded-xl border">
          <div className="font-medium">Max reassignments</div>
          <div className="text-xs text-gray-500">0 → 3</div>
          <input
            type="number"
            min={0}
            max={3}
            value={reassign}
            onChange={(e) => setReassign(Number(e.target.value))}
            className="w-full border rounded-lg p-2 mt-2"
            suppressHydrationWarning
          />
        </label>
      </div>

      <button
        onClick={run}
        className="px-4 py-2 rounded-xl bg-black text-white"
        suppressHydrationWarning
        disabled={loading}
      >
        {loading ? "Running..." : "Run Simulation → Verify Constitution"}
      </button>

      {sim ? (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold">Simulation Result</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <KpiCard
              label="Equity improvement"
              value={percent(sim.equity_improvement ?? 0)}
              helper="Higher is better"
            />
            <KpiCard
              label="Citywide Δ p90"
              value={percent(sim.citywide_delta_p90 ?? 0)}
              helper="Lower is better"
            />
            <KpiCard label="Neighborhoods" value={neighborhoodRows.length} />
          </div>
          <DataTable
            columns={[
              { key: "neighborhood", label: "Neighborhood" },
              { key: "delta_p90", label: "Δ p90" },
              { key: "delta_backlog_pct", label: "Δ backlog" },
            ]}
            rows={neighborhoodRows}
          />
        </section>
      ) : null}

      {ver ? (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">Verdict</h2>
            <PassFailBadge pass={Boolean(ver.pass)} />
          </div>
          <DataTable
            columns={[
              { key: "constraint", label: "Constraint" },
              { key: "neighborhood", label: "Neighborhood" },
              { key: "observed", label: "Observed" },
              { key: "allowed", label: "Allowed" },
            ]}
            rows={violationRows}
          />
        </section>
      ) : null}
    </main>
  );
}
