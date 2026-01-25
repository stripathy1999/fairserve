"use client";

import { useEffect, useState } from "react";
import { zone2 } from "@/lib/store/zone2";
import { ServiceSelect } from "@/components/ServiceSelect";
import { DataTable } from "@/components/DataTable";
import { MemoViewer } from "@/components/MemoViewer";
import { PassFailBadge } from "@/components/PassFailBadge";

export default function ReviewPage() {
  const [services, setServices] = useState<string[]>([]);
  const [service, setService] = useState("");
  const [policies, setPolicies] = useState<any[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [results, setResults] = useState<any[]>([]);
  const [verdicts, setVerdicts] = useState<any[]>([]);
  const [redteam, setRedteam] = useState("");
  const [memo, setMemo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    zone2.fairnessMetrics().then((data) => {
      const list = Array.from(
        new Set((data.metrics || []).map((row: any) => row.service_type))
      ).filter(Boolean);
      setServices(list);
      const storedService = localStorage.getItem("selectedService");
      setService(storedService || list[0] || "");
    });
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("selectedPolicies");
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored);
      setPolicies(parsed);
      if (parsed.length > 0) {
        setSelectedPolicyId(parsed[0].policy_id);
      }
    } catch {
      setError("Unable to load stored policies.");
    }
  }, []);

  const runSimVerify = async () => {
    if (!service || policies.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const simResults = [];
      const verifierResults = [];

      for (const policy of policies) {
        const sim = await zone2.simulate(policy);
        simResults.push(sim);
        const verdict = await zone2.verify({ policy_result: sim });
        verifierResults.push(verdict);
      }

      setResults(simResults);
      setVerdicts(verifierResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const runRedTeam = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        service,
        policies,
        scenario_results: results,
        verifier_outputs: verdicts,
      };
      const response = await zone2.redteam(payload);
      setRedteam(JSON.stringify(response, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Red team failed");
    } finally {
      setLoading(false);
    }
  };

  const runMemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        service,
        policies,
        scenario_results: results,
        verifier_outputs: verdicts,
      };
      const response = await zone2.memo(payload);
      setMemo(JSON.stringify(response, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Memo failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-zinc-900">Review</h2>
        <p className="mt-2 text-sm text-zinc-600">
          Run sim + verify, then red team and memo.
        </p>
      </div>

      <section className="flex flex-wrap items-end gap-4">
        <ServiceSelect services={services} value={service} onChange={setService} />
        <label className="flex flex-col gap-1 text-sm text-zinc-600">
          Policy ID
          <select
            className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900"
            value={selectedPolicyId}
            onChange={(event) => setSelectedPolicyId(event.target.value)}
          >
            {policies.map((policy) => (
              <option key={policy.policy_id} value={policy.policy_id}>
                {policy.policy_id}
              </option>
            ))}
          </select>
        </label>
        <button
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white"
          onClick={runSimVerify}
          disabled={loading || policies.length === 0}
        >
          Run sim + verify
        </button>
        <button
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700"
          onClick={runRedTeam}
          disabled={loading || verdicts.length === 0}
        >
          Run Red Team
        </button>
        <button
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700"
          onClick={runMemo}
          disabled={loading || verdicts.length === 0}
        >
          Generate Memo
        </button>
      </section>

      {error ? (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <section>
        <h3 className="text-lg font-semibold text-zinc-900">PASS / FAIL</h3>
        <div className="mt-4">
          <DataTable
            columns={[
              { key: "policy_id", label: "Policy" },
              { key: "status", label: "Status" },
              { key: "reasons", label: "Reasons" },
            ]}
            rows={verdicts.map((verdict: any) => ({
              policy_id: verdict.policy_id,
              status: verdict.pass ? "PASS" : "FAIL",
              reasons: verdict.violations?.length
                ? verdict.violations.map((v: any) => `${v.constraint}: ${v.neighborhood}`).join(", ")
                : "No violations",
            }))}
          />
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {verdicts.map((verdict: any) => (
            <div
              key={verdict.policy_id}
              className="rounded-lg border border-zinc-200 bg-white p-4"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-zinc-900">
                  {verdict.policy_id}
                </h4>
                <PassFailBadge pass={Boolean(verdict.pass)} />
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-xs text-zinc-500">
                {JSON.stringify(verdict.violations, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-wrap gap-3">
        {selectedPolicyId ? (
          <>
            <a
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700"
              href={zone2.exportPackage(service, selectedPolicyId)}
              target="_blank"
              rel="noreferrer"
            >
              Export JSON
            </a>
            <a
              className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700"
              href={zone2.exportMemo(service, selectedPolicyId)}
              target="_blank"
              rel="noreferrer"
            >
              Export memo
            </a>
          </>
        ) : (
          <p className="text-sm text-zinc-500">Select a policy to export.</p>
        )}
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {redteam ? <MemoViewer title="Red Team" content={redteam} /> : null}
        {memo ? <MemoViewer title="Memo" content={memo} /> : null}
      </section>
    </div>
  );
}
