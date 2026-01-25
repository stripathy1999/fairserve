"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ServiceSelect } from "@/components/ServiceSelect";
import { zone2 } from "@/lib/store/zone2";

type AgentMessage = {
  agent: string;
  content: string;
  turn: number;
  payload?: any;
};

const agentColors: Record<string, string> = {
  Proposer: "border-cyan-500/40 bg-cyan-500/10 text-cyan-100",
  "Constitution Checker": "border-amber-500/40 bg-amber-500/10 text-amber-100",
  "Red Team": "border-rose-500/40 bg-rose-500/10 text-rose-100",
  System: "border-zinc-500/40 bg-zinc-500/10 text-zinc-100",
};

const agentBadges: Record<string, string> = {
  Proposer: "P",
  "Constitution Checker": "C",
  "Red Team": "R",
  System: "S",
};

export default function AgentsPage() {
  const [services, setServices] = useState<string[]>([]);
  const [service, setService] = useState("");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [status, setStatus] = useState("Idle");
  const [finalPayload, setFinalPayload] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [freshnessMinutes, setFreshnessMinutes] = useState<number | null>(null);
  const [nemotronOk, setNemotronOk] = useState<boolean | null>(null);
  const streamRef = useRef<EventSource | null>(null);

  useEffect(() => {
    zone2.fairnessMetrics().then((data) => {
      const list = Array.from(
        new Set((data.metrics || []).map((row: any) => row.service_type))
      ).filter(Boolean);
      setServices(list);
      setService(list[0] || "");
    });
  }, []);

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

  const startStream = () => {
    if (!service) return;
    setMessages([]);
    setFinalPayload(null);
    setErrorMessage(null);
    setStatus("Streaming");

    const qs = `?service=${encodeURIComponent(service)}`;
    const es = new EventSource(`/api/agents/stream${qs}`);
    streamRef.current = es;

    es.addEventListener("message", (evt) => {
      const data = JSON.parse(evt.data) as AgentMessage;
      setMessages((prev) => [...prev, data]);
    });
    es.addEventListener("done", (evt) => {
      setFinalPayload(JSON.parse(evt.data));
      setStatus("Complete");
      es.close();
    });
    es.addEventListener("error", (evt) => {
      if ("data" in evt && typeof evt.data === "string" && evt.data) {
        try {
          const payload = JSON.parse(evt.data);
          setErrorMessage(payload.message || "Agent stream error.");
        } catch {
          setErrorMessage("Agent stream error.");
        }
      } else {
        setErrorMessage("Agent stream disconnected.");
      }
      setStatus("Error");
      es.close();
    });
  };

  const stopStream = () => {
    streamRef.current?.close();
    setStatus("Stopped");
  };

  const summary = useMemo(() => {
    if (!finalPayload) return null;
    return {
      policies: finalPayload.policies?.length || 0,
      chosen: finalPayload.chosen_policy?.policy_id || "None",
    };
  }, [finalPayload]);

  const summarizeMessage = (msg: AgentMessage) => {
    if (msg.payload?.policies) {
      return `Proposed ${msg.payload.policies.length} policy candidates.`;
    }
    if (msg.payload?.verifier_outputs) {
      const pass = msg.payload.verifier_outputs.filter((v: any) => v.pass).length;
      const fail = msg.payload.verifier_outputs.length - pass;
      return `Constitution check complete: ${pass} pass, ${fail} fail.`;
    }
    if (msg.payload?.redteam) {
      const risks = msg.payload.redteam?.risks?.length ?? 0;
      return `Red team flagged ${risks} risks and provided mitigations.`;
    }
    if (msg.payload?.city_state) {
      const neighborhoods = msg.payload.city_state?.neighborhoods?.length ?? 0;
      return `Loaded city state with ${neighborhoods} neighborhoods.`;
    }
    if (msg.content) {
      return msg.content.split("\n").filter(Boolean).slice(0, 3).join(" ");
    }
    return "Message received.";
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="space-y-6 p-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-zinc-500">
              Nemotron Agent Ops Room
            </p>
            <h2 className="text-2xl font-semibold text-white">
              Multi-agent debate and decision stream
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <ServiceSelect
              services={services}
              value={service}
              onChange={setService}
            />
            <button
              className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-zinc-900"
              onClick={startStream}
            >
              Start workflow
            </button>
            <button
              className="rounded-md border border-zinc-700 px-4 py-2 text-sm"
              onClick={stopStream}
            >
              Stop
            </button>
          </div>
        </header>

        <section className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4 text-sm text-zinc-300">
          Status: <span className="text-emerald-400">{status}</span>
          {summary ? (
            <span className="ml-4 text-zinc-400">
              Policies: {summary.policies} · Chosen: {summary.chosen}
            </span>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-zinc-700 px-3 py-1">
              Live feed{" "}
              {freshnessMinutes === null ? "unknown" : `${freshnessMinutes} min ago`}
            </span>
            <span
              className={`rounded-full px-3 py-1 ${
                nemotronOk ? "bg-emerald-500/20 text-emerald-200" : "bg-rose-500/20 text-rose-200"
              }`}
            >
              Nemotron {nemotronOk ? "reachable ✅" : "unreachable ❌"}
            </span>
          </div>
        </section>
        {errorMessage ? (
          <section className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
            {errorMessage}
          </section>
        ) : null}

        <section className="grid gap-4">
          {messages.map((msg, idx) => (
            <div key={`${msg.agent}-${idx}`} className="flex gap-3">
              <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-full bg-zinc-800 text-xs font-semibold text-zinc-200">
                {agentBadges[msg.agent] || "A"}
              </div>
              <div
                className={`flex-1 rounded-lg border p-4 text-sm ${
                  agentColors[msg.agent] || "border-zinc-700 bg-zinc-900/50 text-zinc-100"
                }`}
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-wide text-zinc-400">
                  <span>{msg.agent}</span>
                  <span>Turn {msg.turn}</span>
                </div>
                <p className="mt-2 text-sm text-zinc-100">{summarizeMessage(msg)}</p>
                <details className="mt-3 text-xs text-zinc-300">
                  <summary className="cursor-pointer">View raw</summary>
                  <pre className="mt-2 whitespace-pre-wrap">{msg.content}</pre>
                </details>
                {msg.payload ? (
                  <details className="mt-3 text-xs text-zinc-300">
                    <summary className="cursor-pointer">Structured payload</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-100">
                      {JSON.stringify(msg.payload, null, 2)}
                    </pre>
                  </details>
                ) : null}
              </div>
            </div>
          ))}
        </section>

        {finalPayload ? (
          <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
            <h3 className="text-sm font-semibold text-white">
              Final workflow payload
            </h3>
            <div className="mt-3 text-sm text-zinc-200">
              Selected policy:{" "}
              <span className="font-semibold">
                {finalPayload.chosen_policy?.policy_id || "None"}
              </span>
            </div>
            <details className="mt-3 text-xs text-zinc-300">
              <summary className="cursor-pointer">View payload JSON</summary>
              <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-100">
                {JSON.stringify(finalPayload, null, 2)}
              </pre>
            </details>
          </section>
        ) : null}

        {finalPayload ? (
          <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
            <h3 className="text-sm font-semibold text-white">Replayable Agent Trace</h3>
            <div className="mt-4 grid gap-3">
              {[
                {
                  label: "Proposer",
                  evidence: finalPayload.city_state,
                  output: finalPayload.policies,
                },
                {
                  label: "Simulator",
                  evidence: finalPayload.policies,
                  output: finalPayload.scenario_results,
                },
                {
                  label: "Verifier",
                  evidence: finalPayload.scenario_results,
                  output: finalPayload.verifier_outputs,
                },
                {
                  label: "Red Team",
                  evidence: finalPayload.verifier_outputs,
                  output: finalPayload.redteam,
                },
                {
                  label: "Memo",
                  evidence: finalPayload.redteam,
                  output: finalPayload.memo,
                },
              ].map((step) => (
                <div key={step.label} className="rounded-lg border border-zinc-700 p-3">
                  <div className="flex items-center justify-between text-xs uppercase text-zinc-400">
                    <span>{step.label}</span>
                    <span className="text-emerald-300">JSON validated ✅</span>
                  </div>
                  <p className="mt-2 text-xs text-zinc-300">
                    {step.label === "Proposer"
                      ? `${step.output?.length || 0} policies`
                      : step.label === "Simulator"
                        ? `${step.output?.length || 0} simulations`
                        : step.label === "Verifier"
                          ? `${step.output?.length || 0} verdicts`
                          : step.label === "Red Team"
                            ? `${step.output?.risks?.length ?? 0} risks`
                            : step.label === "Memo"
                              ? `${step.output?.summary?.length ?? 0} summary bullets`
                              : "Details available"}
                  </p>
                  <details className="mt-2 text-xs text-zinc-300">
                    <summary className="cursor-pointer">Evidence used</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-100">
                      {JSON.stringify(step.evidence, null, 2)}
                    </pre>
                  </details>
                  <details className="mt-2 text-xs text-zinc-300">
                    <summary className="cursor-pointer">Output</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-100">
                      {JSON.stringify(step.output, null, 2)}
                    </pre>
                  </details>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
