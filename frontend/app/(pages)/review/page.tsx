"use client";

import { useEffect, useRef, useState } from "react";
import { zone2 } from "@/lib/store/zone2";
import { ServiceSelect } from "@/components/ServiceSelect";
import { DataTable } from "@/components/DataTable";
import { MemoViewer } from "@/components/MemoViewer";
import { PassFailBadge } from "@/components/PassFailBadge";
import { KpiCard } from "@/components/KpiCard";

export default function ReviewPage() {
  const [services, setServices] = useState<string[]>([]);
  const [service, setService] = useState("");
  const [policies, setPolicies] = useState<any[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [results, setResults] = useState<any[]>([]);
  const [verdicts, setVerdicts] = useState<any[]>([]);
  const [cityState, setCityState] = useState<any | null>(null);
  const [evidenceCards, setEvidenceCards] = useState<any[]>([]);
  const [redteam, setRedteam] = useState<any | null>(null);
  const [memo, setMemo] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPolicies, setLoadingPolicies] = useState(false);
  const [loadingEvidence, setLoadingEvidence] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [freshnessMinutes, setFreshnessMinutes] = useState<number | null>(null);
  const [nemotronOk, setNemotronOk] = useState<boolean | null>(null);
  const autoRunRef = useRef(false);

  const percent = (value: number) => `${Math.round(value * 100)}%`;
  const policyParameters = (policy: any) => ({
    capacity_shift_pct: percent(policy?.parameters?.capacity_shift_pct ?? 0),
    efficiency_bonus_pct: percent(policy?.parameters?.efficiency_bonus_pct ?? 0),
    max_reassignments: policy?.parameters?.max_reassignments ?? 0,
  });

  const constraintExplain: Record<string, string> = {
    min_worst_k_improvement:
      "Worst-off neighborhoods must improve by the minimum equity threshold.",
    max_neighborhood_harm: "No neighborhood can worsen beyond the harm threshold.",
    max_backlog_growth: "Backlog growth must stay under the allowed cap.",
    citywide_p90_must_not_worsen: "Citywide p90 must not increase.",
  };

  useEffect(() => {
    const loadBadges = async () => {
      try {
        const live = await fetch("/api/zone1/live?limit=1", { cache: "no-store" }).then((r) =>
          r.json()
        );
        const latest = live?.data?.[0]?.opened_at;
        if (latest) {
          const diff = (Date.now() - new Date(latest).getTime()) / 60000;
          setFreshnessMinutes(Number.isFinite(diff) ? Math.max(0, Math.round(diff)) : null);
        } else {
          setFreshnessMinutes(null);
        }
      } catch {
        setFreshnessMinutes(null);
      }

      try {
        const health = await fetch("/api/agents/health", { cache: "no-store" }).then((r) =>
          r.json()
        );
        setNemotronOk(Boolean(health.ok));
      } catch {
        setNemotronOk(false);
      }
    };
    loadBadges();
  }, []);

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

  const loadPolicies = async (targetService: string) => {
    if (!targetService) return;
    setLoadingPolicies(true);
    setLoadingEvidence(true);
    setError(null);
    setResults([]);
    setVerdicts([]);
    setRedteam(null);
    setMemo(null);
    try {
      const cityState = await zone2.cityState(targetService);
      setCityState(cityState);
      const [response, evidence] = await Promise.all([
        zone2.propose({ city_state: cityState }),
        zone2.evidence(targetService),
      ]);
      const parsed = response?.parsed_json || [];
      setPolicies(parsed);
      setSelectedPolicyId(parsed[0]?.policy_id || "");
      setEvidenceCards(evidence?.retrieved_cards || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate policies.");
      setPolicies([]);
      setSelectedPolicyId("");
      setCityState(null);
      setEvidenceCards([]);
    } finally {
      setLoadingPolicies(false);
      setLoadingEvidence(false);
    }
  };

  useEffect(() => {
    if (service) {
      loadPolicies(service);
    }
  }, [service]);

  useEffect(() => {
    autoRunRef.current = false;
  }, [service]);

  const runSimVerify = async (policyList: any[] = policies) => {
    if (!service || policyList.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const simResults = [];
      const verifierResults = [];

      for (const policy of policyList) {
        const sim = await zone2.simulate(policy);
        simResults.push(sim);
        const verdict = await zone2.verify({ policy_result: sim });
        verifierResults.push(verdict);
      }

      setResults(simResults);
      setVerdicts(verifierResults);
      if (!selectedPolicyId && simResults.length > 0) {
        setSelectedPolicyId(simResults[0].policy_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (policies.length > 0 && !autoRunRef.current) {
      autoRunRef.current = true;
      runSimVerify(policies);
    }
  }, [policies]);

  const normalizeAgentResponse = (response: any) => {
    if (response && typeof response === "object" && "parsed_json" in response) {
      return {
        parsed_json: response.parsed_json,
        raw_text: response.raw_text ?? null,
        validation_status: response.validation_status ?? null,
      };
    }
    return {
      parsed_json: response,
      raw_text: null,
      validation_status: "valid",
    };
  };

  const runRedTeam = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        service,
        city_state: cityState,
        retrieved_cards: evidenceCards,
        policies,
        scenario_results: results,
        verifier_outputs: verdicts,
      };
      const response = await zone2.redteam(payload);
      setRedteam(normalizeAgentResponse(response));
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
        city_state: cityState,
        retrieved_cards: evidenceCards,
        policies,
        scenario_results: results,
        verifier_outputs: verdicts,
      };
      const response = await zone2.memo(payload);
      setMemo(normalizeAgentResponse(response));
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
          Policies are generated, simulated, verified against the constitution, then reviewed by
          red team and turned into an exec memo.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border border-zinc-200 bg-white px-3 py-1">
            Live feed{" "}
            {freshnessMinutes === null ? "unknown" : `${freshnessMinutes} min ago`}
          </span>
          <span
            className={`rounded-full px-3 py-1 ${
              nemotronOk ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
            }`}
          >
            Nemotron {nemotronOk ? "reachable ✅" : "unreachable ❌"}
          </span>
        </div>
      </div>

      <section className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
        <div className="text-xs font-semibold uppercase text-zinc-400">How to read this</div>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>Pick a service to generate candidate policies.</li>
          <li>We simulate each policy and check constitutional constraints.</li>
          <li>Use the KPIs and violations to see why a policy passes or fails.</li>
          <li>Red team and memo summarize risks and recommendations.</li>
        </ol>
      </section>

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
            disabled={loading || loadingPolicies || policies.length === 0}
        >
            {loading ? "Running..." : "Run sim + verify"}
        </button>
          <button
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700"
            onClick={() => loadPolicies(service)}
            disabled={loadingPolicies || !service}
          >
            {loadingPolicies ? "Generating..." : "Refresh policies"}
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

      {verdicts.length > 0 && verdicts.every((v: any) => !v.pass) ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          All candidate policies failed at least one constitutional constraint. Use the Policy Lab
          to adjust parameters or review the violations below to see which constraint is the
          bottleneck.
        </div>
      ) : null}

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Policy candidates</h3>
        <p className="mt-1 text-xs text-zinc-500">
          Capacity shift moves resources from best‑off to worst‑off areas. Efficiency bonus
          represents system‑wide gains. Reassignments cap prevents aging loops.
        </p>
        <div className="mt-3">
          <DataTable
            columns={[
              { key: "policy_id", label: "Policy" },
              { key: "capacity_shift_pct", label: "Capacity shift" },
              { key: "efficiency_bonus_pct", label: "Efficiency bonus" },
              { key: "max_reassignments", label: "Reassign cap" },
              { key: "status", label: "Status" },
            ]}
            rows={policies.map((policy) => {
              const verdict = verdicts.find((v: any) => v.policy_id === policy.policy_id);
              const params = policyParameters(policy);
              return {
                policy_id: policy.policy_id,
                capacity_shift_pct: params.capacity_shift_pct,
                efficiency_bonus_pct: params.efficiency_bonus_pct,
                max_reassignments: params.max_reassignments,
                status: verdict ? (verdict.pass ? "PASS" : "FAIL") : "Pending",
              };
            })}
          />
        </div>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">RAG evidence cards</h3>
            <p className="text-xs text-zinc-500">
              The retriever highlights evidence + playbook patterns used by the agents.
            </p>
          </div>
          {loadingEvidence ? (
            <span className="text-xs text-zinc-400">Loading evidence…</span>
          ) : null}
        </div>
        {evidenceCards.length === 0 ? (
          <p className="mt-3 text-sm text-zinc-500">No evidence cards retrieved yet.</p>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {evidenceCards.map((card) => (
              <div key={card.id} className="rounded-md border border-zinc-200 p-3">
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span className="font-semibold text-zinc-700">{card.id}</span>
                  <span>{card.type || "evidence"}</span>
                </div>
                <p className="mt-2 text-xs text-zinc-500">Why: {card.why_retrieved}</p>
                <p className="mt-1 text-xs text-zinc-400">
                  Similarity score: {Number(card.score ?? 0).toFixed(2)}
                </p>
                <details className="mt-2 text-xs text-zinc-500">
                  <summary className="cursor-pointer">Snippet</summary>
                  <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-600">
                    {card.snippet}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}
      </section>

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
                ? verdict.violations
                    .map(
                      (v: any) =>
                        `${constraintExplain[v.constraint] || v.constraint} (${v.neighborhood})`
                    )
                    .join(", ")
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
              {verdict.violations?.length ? (
                <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-zinc-600">
                  {verdict.violations.map((violation: any, idx: number) => (
                    <li key={`${verdict.policy_id}-violation-${idx}`}>
                      <span className="font-semibold">{violation.constraint}</span> ·{" "}
                      {constraintExplain[violation.constraint] || "Constraint violated."} (
                      {violation.neighborhood})
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-xs text-zinc-500">No violations.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {(() => {
          const selectedSim = results.find((r) => r.policy_id === selectedPolicyId);
          const selectedVerdict = verdicts.find((v) => v.policy_id === selectedPolicyId);
          const violations = selectedVerdict?.violations || [];
          return (
            <>
              <KpiCard
                label="Equity improvement"
                value={percent(selectedSim?.equity_improvement ?? 0)}
                helper="Higher is better; 0% means no change from baseline"
              />
              <KpiCard
                label="Citywide Δ p90"
                value={percent(selectedSim?.citywide_delta_p90 ?? 0)}
                helper="Lower is better; 0% means no change from baseline"
              />
              <KpiCard label="Violations" value={violations.length} />
            </>
          );
        })()}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Violations by constraint</h3>
        {(() => {
          const selectedVerdict = verdicts.find((v) => v.policy_id === selectedPolicyId);
          const violations = selectedVerdict?.violations || [];
          const grouped = violations.reduce<Record<string, string[]>>((acc, v: any) => {
            const key = v.constraint || "unknown";
            acc[key] = acc[key] || [];
            acc[key].push(v.neighborhood);
            return acc;
          }, {});
          const entries = Object.entries(grouped);
          if (entries.length === 0) {
            return <p className="mt-2 text-sm text-zinc-500">No violations.</p>;
          }
          return (
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {entries.map(([constraint, neighborhoods]) => (
                <div key={constraint} className="rounded-md border border-zinc-200 p-3">
                  <div className="text-xs uppercase text-zinc-500">{constraint}</div>
                  <div className="mt-1 text-xs text-zinc-400">
                    {constraintExplain[constraint] || "Constraint explanation unavailable."}
                  </div>
                  <div className="mt-2 text-sm text-zinc-700">
                    {neighborhoods.length} · {neighborhoods.join(", ")}
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Pareto frontier</h3>
        <p className="text-xs text-zinc-500">X: citywide Δ p90, Y: equity improvement</p>
        <div className="relative mt-4 h-56 rounded-md border border-dashed border-zinc-200 bg-zinc-50">
          {(() => {
            if (results.length === 0) {
              return (
                <p className="p-4 text-sm text-zinc-400">No simulation results yet.</p>
              );
            }
            const xs = results.map((r) => r.citywide_delta_p90 ?? 0);
            const ys = results.map((r) => r.equity_improvement ?? 0);
            const minX = Math.min(...xs, 0);
            const maxX = Math.max(...xs, 1);
            const minY = Math.min(...ys, 0);
            const maxY = Math.max(...ys, 1);
            return results.map((r) => {
              const x = r.citywide_delta_p90 ?? 0;
              const y = r.equity_improvement ?? 0;
              const left = ((x - minX) / (maxX - minX || 1)) * 100;
              const bottom = ((y - minY) / (maxY - minY || 1)) * 100;
              const isSelected = r.policy_id === selectedPolicyId;
              return (
                <button
                  key={r.policy_id}
                  className={`absolute h-3 w-3 rounded-full ${
                    isSelected ? "bg-emerald-500" : "bg-zinc-500"
                  }`}
                  style={{ left: `${left}%`, bottom: `${bottom}%` }}
                  onClick={() => setSelectedPolicyId(r.policy_id)}
                  title={r.policy_id}
                />
              );
            });
          })()}
        </div>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Constraint heatmap</h3>
        {(() => {
          const selectedVerdict = verdicts.find((v) => v.policy_id === selectedPolicyId);
          const selectedSim = results.find((r) => r.policy_id === selectedPolicyId);
          const violations = selectedVerdict?.violations || [];
          const constraints = [
            "min_worst_k_improvement",
            "max_neighborhood_harm",
            "max_backlog_growth",
            "citywide_p90_must_not_worsen",
          ];
          const neighborhoods = selectedSim
            ? Object.keys(selectedSim.neighborhood_effects || {})
            : [];
          if (constraints.length === 0 || neighborhoods.length === 0) {
            return <p className="mt-2 text-sm text-zinc-500">No heatmap data.</p>;
          }
          return (
            <div className="mt-3 overflow-auto">
              <table className="min-w-full text-left text-xs">
                <thead>
                  <tr>
                    <th className="px-2 py-1 text-zinc-400">Neighborhood</th>
                    {constraints.map((constraint) => (
                      <th key={constraint} className="px-2 py-1 text-zinc-400">
                        {constraint}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {neighborhoods.map((n) => (
                    <tr key={n} className="border-t border-zinc-200">
                      <td className="px-2 py-1 text-zinc-600">{n}</td>
                      {constraints.map((c) => {
                        const hit = violations.some(
                          (v: any) => v.constraint === c && v.neighborhood === n
                        );
                        return (
                          <td key={`${n}-${c}`} className="px-2 py-1">
                            <span
                              className={`inline-block h-3 w-3 rounded ${
                                hit ? "bg-rose-400" : "bg-emerald-300"
                              }`}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-zinc-900">Neighborhood deltas</h3>
        {(() => {
          const selectedSim = results.find((r) => r.policy_id === selectedPolicyId);
          const effects = selectedSim?.neighborhood_effects || {};
          const rows = Object.entries(effects).map(([name, metrics]: any) => ({
            neighborhood: name,
            delta_p90: percent(Number(metrics.delta_p90 ?? 0)),
            delta_backlog_pct: percent(Number(metrics.delta_backlog_pct ?? 0)),
          }));
          if (rows.length === 0) {
            return <p className="mt-2 text-sm text-zinc-500">No deltas available.</p>;
          }
          return (
            <DataTable
              columns={[
                { key: "neighborhood", label: "Neighborhood" },
                { key: "delta_p90", label: "Δ p90" },
                { key: "delta_backlog_pct", label: "Δ backlog" },
              ]}
              rows={rows}
            />
          );
        })()}
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
        {redteam ? (
          <MemoViewer
            title="Red Team"
            parsed={redteam.parsed_json}
            rawText={redteam.raw_text}
            validationStatus={redteam.validation_status}
          />
        ) : null}
        {memo ? (
          <MemoViewer
            title="Memo"
            parsed={memo.parsed_json}
            rawText={memo.raw_text}
            validationStatus={memo.validation_status}
          />
        ) : null}
      </section>
    </div>
  );
}
