"use client";

import { useEffect, useMemo, useState } from "react";
import ServiceTypeSelect from "../components/ServiceTypeSelect";
import type { RedTeamReport, ScenarioResults, VerifierOutputs } from "@/lib/types";

type SimPayload = {
  scenario: ScenarioResults;
  verifier: VerifierOutputs;
};

type StressPayload = {
  baseline: SimPayload;
  stressed: SimPayload;
  stressLabel: string;
};

type ParetoRow = {
  policyId: string;
  equityGain: number;
  backlogDelta: number;
  citywideP90: number;
  robustness: number;
};

const STRESS_OPTIONS = [
  { value: "none", label: "None (normal)" },
  { value: "storm", label: "Storm Day: demand +30%" },
  { value: "staff", label: "Staff Shortage: capacity −15%" },
  { value: "duplicate", label: "Duplicate Spam Surge: duplicates +50%" },
] as const;

export default function ReviewPage() {
  const [serviceType, setServiceType] = useState("encampment");
  const [serviceOptions, setServiceOptions] = useState([
    { value: "encampment", label: "Encampment" },
  ]);
  const [payload, setPayload] = useState<SimPayload | null>(null);
  const [stressPayload, setStressPayload] = useState<StressPayload | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [stressScenario, setStressScenario] = useState<(typeof STRESS_OPTIONS)[number]["value"]>(
    "none"
  );
  const [paretoRows, setParetoRows] = useState<ParetoRow[] | null>(null);
  const [isParetoLoading, setIsParetoLoading] = useState(false);
  const [redteam, setRedteam] = useState<RedTeamReport | null>(null);
  const [memo, setMemo] = useState<string | null>(null);
  const [isRedteamLoading, setIsRedteamLoading] = useState(false);
  const [isMemoLoading, setIsMemoLoading] = useState(false);

  useEffect(() => {
    const storedServiceType = sessionStorage.getItem("fairserve:selectedServiceType");
    if (storedServiceType) {
      setServiceType(storedServiceType);
    }
  }, []);

  useEffect(() => {
    let isActive = true;
    const loadServices = async () => {
      const res = await fetch("/api/services");
      const payload = (await res.json()) as { services: Array<{ id: string; label: string }> };
      if (isActive && payload.services.length > 0) {
        setServiceOptions(payload.services.map((svc) => ({ value: svc.id, label: svc.label })));
      }
    };
    loadServices();
    return () => {
      isActive = false;
    };
  }, []);

  const handleRun = async () => {
    setIsLoading(true);
    setPayload(null);
    setStressPayload(null);
    setParetoRows(null);

    if (stressScenario === "none") {
      const res = await fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service_type: serviceType }),
      });
      const result = (await res.json()) as SimPayload;
      setPayload(result);
      setIsLoading(false);
      return;
    }

    const [baselineRes, stressRes] = await Promise.all([
      fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service_type: serviceType }),
      }),
      fetch(
        `/api/sim/run?service_type=${encodeURIComponent(serviceType)}&stress=${stressScenario}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ service_type: serviceType, stress: stressScenario }),
        }
      ),
    ]);

    const [baseline, stressed] = (await Promise.all([
      baselineRes.json(),
      stressRes.json(),
    ])) as [SimPayload, SimPayload];

    const stressLabel =
      STRESS_OPTIONS.find((option) => option.value === stressScenario)?.label ??
      "Stress Scenario";
    setStressPayload({ baseline, stressed, stressLabel });
    setIsLoading(false);
  };

  const handleRunPareto = async () => {
    setIsParetoLoading(true);
    setParetoRows(null);
    const baseRequest = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_type: serviceType }),
    };

    const [baselineRes, stormRes, staffRes, duplicateRes] = await Promise.all([
      fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}`, baseRequest),
      fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}&stress=storm`, {
        ...baseRequest,
        body: JSON.stringify({ service_type: serviceType, stress: "storm" }),
      }),
      fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}&stress=staff`, {
        ...baseRequest,
        body: JSON.stringify({ service_type: serviceType, stress: "staff" }),
      }),
      fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}&stress=duplicate`, {
        ...baseRequest,
        body: JSON.stringify({ service_type: serviceType, stress: "duplicate" }),
      }),
    ]);

    const [baseline, storm, staff, duplicate] = (await Promise.all([
      baselineRes.json(),
      stormRes.json(),
      staffRes.json(),
      duplicateRes.json(),
    ])) as [SimPayload, SimPayload, SimPayload, SimPayload];

    const verdictMaps = [
      new Map(storm.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict.pass])),
      new Map(staff.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict.pass])),
      new Map(duplicate.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict.pass])),
    ];

    const rows: ParetoRow[] = baseline.scenario.results.map((result) => {
      const robustness = verdictMaps.reduce((count, map) => {
        return count + (map.get(result.policy_id) ? 1 : 0);
      }, 0);

      return {
        policyId: result.policy_id,
        equityGain: result.equity_gain_score,
        backlogDelta: result.backlog_delta_pct,
        citywideP90: result.citywide_p90_delta_pct,
        robustness,
      };
    });

    rows.sort((a, b) => {
      if (b.equityGain !== a.equityGain) {
        return b.equityGain - a.equityGain;
      }
      if (a.backlogDelta !== b.backlogDelta) {
        return a.backlogDelta - b.backlogDelta;
      }
      if (a.citywideP90 !== b.citywideP90) {
        return a.citywideP90 - b.citywideP90;
      }
      return b.robustness - a.robustness;
    });

    setParetoRows(rows);
    setIsParetoLoading(false);
  };

  const handleRunRedteam = async () => {
    setIsRedteamLoading(true);
    const res = await fetch(`/api/redteam?service_type=${encodeURIComponent(serviceType)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_type: serviceType }),
    });
    const report = (await res.json()) as RedTeamReport;
    setRedteam(report);
    setIsRedteamLoading(false);
  };

  const handleMemo = async () => {
    setIsMemoLoading(true);
    const res = await fetch(`/api/memo?service_type=${encodeURIComponent(serviceType)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service_type: serviceType }),
    });
    const result = (await res.json()) as { memo: string };
    setMemo(result.memo);
    setIsMemoLoading(false);
  };

  const verdictMap = useMemo(() => {
    if (payload) {
      return new Map(payload.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict]));
    }
    if (stressPayload) {
      return new Map(
        stressPayload.stressed.verifier.verdicts.map((verdict) => [
          verdict.policy_id,
          verdict,
        ])
      );
    }
    return new Map<string, VerifierOutputs["verdicts"][number]>();
  }, [payload, stressPayload]);

  const baselineVerdictMap = useMemo(() => {
    if (!stressPayload) {
      return new Map<string, VerifierOutputs["verdicts"][number]>();
    }
    return new Map(
      stressPayload.baseline.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict])
    );
  }, [stressPayload]);

  const stressedVerdictMap = useMemo(() => {
    if (!stressPayload) {
      return new Map<string, VerifierOutputs["verdicts"][number]>();
    }
    return new Map(
      stressPayload.stressed.verifier.verdicts.map((verdict) => [verdict.policy_id, verdict])
    );
  }, [stressPayload]);

  const robustWinner = useMemo(() => {
    if (!stressPayload) {
      return null;
    }
    const passed = stressPayload.stressed.verifier.verdicts.find((verdict) => verdict.pass);
    return passed?.policy_id ?? null;
  }, [stressPayload]);


  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadMemoMarkdown = async () => {
    const memoText = memo ?? (await (await fetch("/api/memo", { method: "POST" })).json()).memo;
    setMemo(memoText);
    downloadBlob(new Blob([memoText], { type: "text/markdown" }), "final_memo.md");
  };

  const handleDownloadMemoPdf = async () => {
    const memoText = memo ?? (await (await fetch("/api/memo", { method: "POST" })).json()).memo;
    setMemo(memoText);
    const win = window.open("", "_blank");
    if (!win) {
      return;
    }
    win.document.write(`<!doctype html><html><head><title>Final Memo</title></head><body style="font-family: system-ui; padding: 24px;"><pre style="white-space: pre-wrap;">${memoText}</pre></body></html>`);
    win.document.close();
    win.focus();
    win.print();
  };

  const handleDownloadPolicyPackage = async () => {
    let basePayload = payload;
    if (!basePayload) {
      const res = await fetch(`/api/sim/run?service_type=${encodeURIComponent(serviceType)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service_type: serviceType }),
      });
      basePayload = (await res.json()) as SimPayload;
      setPayload(basePayload);
    }

    const packageData = {
      service_type: serviceType,
      generatedAt: new Date().toISOString(),
      scenario: basePayload?.scenario ?? null,
      verifier: basePayload?.verifier ?? null,
      stressScenario,
      stressPayload: stressPayload ?? null,
      redteam,
      memo,
    };

    downloadBlob(
      new Blob([JSON.stringify(packageData, null, 2)], { type: "application/json" }),
      `policy_package_${serviceType}.json`
    );
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Simulation Review</h1>

      <div style={{ marginTop: 12 }}>
        <ServiceTypeSelect
          options={serviceOptions}
          value={serviceType}
          onChange={(next) => {
            setServiceType(next);
            setPayload(null);
            setRedteam(null);
            setMemo(null);
            setStressPayload(null);
            setParetoRows(null);
          }}
        />
      </div>

      <div style={{ marginTop: 12, display: "flex", gap: 16, flexWrap: "wrap" }}>
        <button
          onClick={handleRun}
          disabled={isLoading}
          style={{
            background: "#1f6feb",
            color: "#fff",
            border: "none",
            padding: "10px 14px",
            borderRadius: 10,
            cursor: "pointer",
          }}
        >
          {isLoading ? "Running..." : "Run simulation + verify"}
        </button>
        <button
          onClick={handleRunPareto}
          disabled={isParetoLoading}
          style={{
            background: "#2d2d2d",
            color: "#fff",
            border: "1px solid #3b3b3b",
            padding: "10px 14px",
            borderRadius: 10,
            cursor: "pointer",
          }}
        >
          {isParetoLoading ? "Building Pareto..." : "Compute Pareto Frontier"}
        </button>
        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ fontSize: 12, opacity: 0.7 }}>Run under stress</span>
          <select
            value={stressScenario}
            onChange={(event) => {
              setStressScenario(event.target.value as typeof stressScenario);
              setPayload(null);
              setStressPayload(null);
            }}
            style={{
              background: "#111",
              color: "#f6f6f6",
              border: "1px solid #2a2a2a",
              borderRadius: 8,
              padding: "6px 10px",
            }}
          >
            {STRESS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section style={{ marginTop: 20 }}>
        {payload || stressPayload ? (
          <div style={{ overflowX: "auto" }}>
            {stressPayload ? (
              <div style={{ marginBottom: 12, opacity: 0.8 }}>
                Stress scenario: <strong>{stressPayload.stressLabel}</strong>
                {robustWinner ? (
                  <span style={{ marginLeft: 12 }}>
                    Robust winner: <strong>{robustWinner}</strong>
                  </span>
                ) : null}
              </div>
            ) : null}
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid #222" }}>
                  <th style={{ padding: "8px 6px" }}>Policy ID</th>
                  <th style={{ padding: "8px 6px" }}>Citywide p90 delta</th>
                  <th style={{ padding: "8px 6px" }}>Backlog delta</th>
                  <th style={{ padding: "8px 6px" }}>Verdict</th>
                  {stressPayload ? (
                    <th style={{ padding: "8px 6px" }}>Flip check</th>
                  ) : null}
                  <th style={{ padding: "8px 6px" }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {(payload ?? stressPayload?.stressed)?.scenario.results.map((result) => {
                  const verdict = verdictMap.get(result.policy_id);
                  const pass = verdict?.pass ?? false;
                  const baselineVerdict = baselineVerdictMap.get(result.policy_id);
                  const stressedVerdict = stressedVerdictMap.get(result.policy_id);
                  const flipped =
                    baselineVerdict && stressedVerdict
                      ? baselineVerdict.pass && !stressedVerdict.pass
                      : false;
                  return (
                    <tr
                      key={result.policy_id}
                      style={{ borderBottom: "1px solid #1b1b1b" }}
                    >
                      <td style={{ padding: "8px 6px" }}>{result.policy_id}</td>
                      <td style={{ padding: "8px 6px" }}>
                        {result.citywide_p90_delta_pct.toFixed(1)}%
                      </td>
                      <td style={{ padding: "8px 6px" }}>
                        {result.backlog_delta_pct.toFixed(1)}%
                      </td>
                      <td style={{ padding: "8px 6px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 6,
                              padding: "4px 8px",
                              borderRadius: 999,
                              background: pass ? "#113d2a" : "#3a1a1a",
                              color: pass ? "#7ee3a1" : "#ff8f8f",
                              fontSize: 12,
                              width: "fit-content",
                            }}
                          >
                            {pass ? "✅ PASS" : "❌ FAIL"}
                          </span>
                          {!pass && verdict?.reasons?.length ? (
                            <div style={{ color: "#ff8f8f", fontSize: 12 }}>
                              {verdict.reasons[0]}
                            </div>
                          ) : null}
                        </div>
                      </td>
                      {stressPayload ? (
                        <td style={{ padding: "8px 6px" }}>
                          {flipped ? (
                            <span style={{ color: "#ff8f8f", fontSize: 12 }}>
                              ✅ PASS normally → ❌ FAIL under stress
                            </span>
                          ) : (
                            <span style={{ color: "#7ee3a1", fontSize: 12 }}>
                              Stable under stress
                            </span>
                          )}
                        </td>
                      ) : null}
                      <td style={{ padding: "8px 6px" }}>
                        <details>
                          <summary style={{ cursor: "pointer" }}>View details</summary>
                          <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
                            <div>Equity gain score: {result.equity_gain_score.toFixed(2)}</div>
                            {verdict ? (
                              <>
                                <div style={{ marginTop: 6 }}>
                                  Worst-K improve: {verdict.constraint_values.worst_k_improve_pct.toFixed(1)}%
                                </div>
                                <div>
                                  Max harm: {verdict.constraint_values.max_harm_pct.toFixed(1)}%
                                </div>
                                <div>
                                  Backlog change: {verdict.constraint_values.backlog_change_pct.toFixed(1)}%
                                </div>
                                {verdict.reasons.length > 0 ? (
                                  <ul style={{ marginTop: 6, paddingLeft: 18 }}>
                                    {verdict.reasons.map((reason) => (
                                      <li key={reason}>{reason}</li>
                                    ))}
                                  </ul>
                                ) : null}
                              </>
                            ) : (
                              <div style={{ marginTop: 6 }}>No verifier details.</div>
                            )}
                          </div>
                        </details>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ opacity: 0.7 }}>Run the simulation to see results.</div>
        )}
      </section>

      {(payload || stressPayload) && verdictMap.size > 0 ? (
        <section style={{ marginTop: 20 }}>
          <h2>Audit Trail</h2>
          <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
            {(payload ?? stressPayload?.stressed)?.scenario.results.map((result) => {
              const verdict = verdictMap.get(result.policy_id);
              if (!verdict) {
                return null;
              }

              const worstImprove = verdict.constraint_values.worst_k_improve_pct;
              const maxHarm = verdict.constraint_values.max_harm_pct;
              const backlogChange = verdict.constraint_values.backlog_change_pct;

              const passesWorst = worstImprove >= 12;
              const passesHarm = maxHarm <= 5;
              const passesBacklog = backlogChange <= 8;
              const passesCitywide = result.citywide_p90_delta_pct <= 0;

              return (
                <div
                  key={result.policy_id}
                  style={{ background: "#141414", padding: 16, borderRadius: 12 }}
                >
                  <div style={{ fontSize: 14, opacity: 0.7, marginBottom: 8 }}>
                    Policy Certificate — {result.policy_id}
                  </div>
                  <div style={{ display: "grid", gap: 6, fontSize: 13 }}>
                    <div>
                      Worst-K improvement: {worstImprove.toFixed(1)}%{" "}
                      <span style={{ color: passesWorst ? "#7ee3a1" : "#ff8f8f" }}>
                        {passesWorst ? "✅ (>=12)" : "❌ (<12)"}
                      </span>
                    </div>
                    <div>
                      Max harm: {maxHarm.toFixed(1)}%{" "}
                      <span style={{ color: passesHarm ? "#7ee3a1" : "#ff8f8f" }}>
                        {passesHarm ? "✅ (<=5)" : "❌ (>5)"}
                      </span>
                    </div>
                    <div>
                      Backlog change: {backlogChange.toFixed(1)}%{" "}
                      <span style={{ color: passesBacklog ? "#7ee3a1" : "#ff8f8f" }}>
                        {passesBacklog ? "✅ (<=8)" : "❌ (>8)"}
                      </span>
                    </div>
                    <div>
                      Citywide p90 non-worsen:{" "}
                      <span style={{ color: passesCitywide ? "#7ee3a1" : "#ff8f8f" }}>
                        {passesCitywide ? "✅" : "❌"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <section style={{ marginTop: 28 }}>
        <h2>Exportables</h2>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 12 }}>
          <button
            onClick={handleDownloadMemoMarkdown}
            style={{
              background: "#2d2d2d",
              color: "#fff",
              border: "1px solid #3b3b3b",
              padding: "10px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            Download Final Memo (Markdown)
          </button>
          <button
            onClick={handleDownloadMemoPdf}
            style={{
              background: "#2d2d2d",
              color: "#fff",
              border: "1px solid #3b3b3b",
              padding: "10px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            Download Final Memo (PDF)
          </button>
          <button
            onClick={handleDownloadPolicyPackage}
            style={{
              background: "#2d2d2d",
              color: "#fff",
              border: "1px solid #3b3b3b",
              padding: "10px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            Download Policy Package JSON
          </button>
        </div>
      </section>

      <section style={{ marginTop: 28 }}>
        <h2>Pareto Frontier</h2>
        {paretoRows ? (
          <div style={{ overflowX: "auto", marginTop: 12 }}>
            <div style={{ marginBottom: 10, opacity: 0.7 }}>
              Top 5 policies (Pareto candidates)
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid #222" }}>
                  <th style={{ padding: "8px 6px" }}>Policy ID</th>
                  <th style={{ padding: "8px 6px" }}>Equity gain</th>
                  <th style={{ padding: "8px 6px" }}>Backlog delta</th>
                  <th style={{ padding: "8px 6px" }}>Citywide p90</th>
                  <th style={{ padding: "8px 6px" }}>Robustness</th>
                </tr>
              </thead>
              <tbody>
                {paretoRows.slice(0, 5).map((row) => (
                  <tr key={row.policyId} style={{ borderBottom: "1px solid #1b1b1b" }}>
                    <td style={{ padding: "8px 6px" }}>{row.policyId}</td>
                    <td style={{ padding: "8px 6px" }}>{row.equityGain.toFixed(2)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.backlogDelta.toFixed(1)}%</td>
                    <td style={{ padding: "8px 6px" }}>{row.citywideP90.toFixed(1)}%</td>
                    <td style={{ padding: "8px 6px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "4px 8px",
                          borderRadius: 999,
                          background: row.robustness === 3 ? "#113d2a" : "#2f2a14",
                          color: row.robustness === 3 ? "#7ee3a1" : "#ffd27d",
                          fontSize: 12,
                        }}
                      >
                        {row.robustness}/3
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ opacity: 0.7, marginTop: 12 }}>
            Click "Compute Pareto Frontier" to rank policies.
          </div>
        )}
      </section>

      <section style={{ marginTop: 28 }}>
        <h2>Red Team + Final Memo</h2>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 12 }}>
          <button
            onClick={handleRunRedteam}
            disabled={isRedteamLoading}
            style={{
              background: "#2d2d2d",
              color: "#fff",
              border: "1px solid #3b3b3b",
              padding: "10px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            {isRedteamLoading ? "Running audit..." : "Run Red Team Audit"}
          </button>
          <button
            onClick={handleMemo}
            disabled={isMemoLoading}
            style={{
              background: "#2d2d2d",
              color: "#fff",
              border: "1px solid #3b3b3b",
              padding: "10px 14px",
              borderRadius: 10,
              cursor: "pointer",
            }}
          >
            {isMemoLoading ? "Generating memo..." : "Generate Final Memo"}
          </button>
        </div>

        <div style={{ display: "grid", gap: 16, marginTop: 16 }}>
          {redteam ? (
            <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
              <h3 style={{ marginTop: 0 }}>Risks</h3>
              <div style={{ display: "grid", gap: 8 }}>
                {redteam.risks.map((risk) => (
                  <div key={risk.detail} style={{ display: "flex", gap: 10 }}>
                    <span
                      style={{
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 999,
                        background:
                          risk.severity === "high"
                            ? "#3a1a1a"
                            : risk.severity === "medium"
                            ? "#2f2a14"
                            : "#1c2b1e",
                        color:
                          risk.severity === "high"
                            ? "#ff8f8f"
                            : risk.severity === "medium"
                            ? "#ffd27d"
                            : "#7ee3a1",
                        textTransform: "uppercase",
                        letterSpacing: 0.4,
                        height: "fit-content",
                      }}
                    >
                      {risk.severity}
                    </span>
                    <div>
                      <strong>{risk.type}</strong>: {risk.detail}
                    </div>
                  </div>
                ))}
              </div>

              <h3 style={{ marginTop: 16 }}>Mitigations</h3>
              <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                {redteam.mitigations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div style={{ opacity: 0.7 }}>Run the red team audit to see risks.</div>
          )}

          {memo ? (
            <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
              <h3 style={{ marginTop: 0 }}>Final Memo</h3>
              <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{memo}</div>
            </div>
          ) : (
            <div style={{ opacity: 0.7 }}>Generate the final memo to view it.</div>
          )}
        </div>
      </section>
    </main>
  );
}
