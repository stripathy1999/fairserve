"use client";

import { useState } from "react";

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

  async function run() {
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
  }

  return (
    <main className="p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Policy Lab — Simulate + Verify</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <label className="p-4 rounded-xl border">
          <div className="font-medium">Capacity shift</div>
          <div className="text-xs text-gray-500">0.00 → 0.30</div>
          <input
            type="range"
            min={0}
            max={0.3}
            step={0.01}
            value={cap}
            onChange={(e) => setCap(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-sm">{cap.toFixed(2)}</div>
        </label>

        <label className="p-4 rounded-xl border">
          <div className="font-medium">Efficiency bonus</div>
          <div className="text-xs text-gray-500">0.00 → 0.20</div>
          <input
            type="range"
            min={0}
            max={0.2}
            step={0.01}
            value={eff}
            onChange={(e) => setEff(Number(e.target.value))}
            className="w-full"
          />
          <div className="text-sm">{eff.toFixed(2)}</div>
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
          />
        </label>
      </div>

      <button onClick={run} className="px-4 py-2 rounded-xl bg-black text-white">
        Run Simulation → Verify Constitution
      </button>

      {sim && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Simulation Result</h2>
          <pre className="bg-black text-green-200 p-4 rounded-xl overflow-auto text-xs">
            {JSON.stringify(sim, null, 2)}
          </pre>
        </section>
      )}

      {ver && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">
            Verdict: {ver.pass ? "✅ PASS" : "❌ FAIL"}
          </h2>
          <pre className="bg-black text-green-200 p-4 rounded-xl overflow-auto text-xs">
            {JSON.stringify(ver, null, 2)}
          </pre>
        </section>
      )}
    </main>
  );
}
