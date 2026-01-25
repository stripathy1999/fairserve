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

export default function AgentsPage() {
  const [services, setServices] = useState<string[]>([]);
  const [service, setService] = useState("");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [status, setStatus] = useState("Idle");
  const [finalPayload, setFinalPayload] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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
        </section>
        {errorMessage ? (
          <section className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
            {errorMessage}
          </section>
        ) : null}

        <section className="grid gap-4">
          {messages.map((msg, idx) => (
            <div
              key={`${msg.agent}-${idx}`}
              className={`rounded-lg border p-4 text-sm ${agentColors[msg.agent] || "border-zinc-700 bg-zinc-900/50 text-zinc-100"}`}
            >
              <div className="flex items-center justify-between text-xs uppercase tracking-wide text-zinc-400">
                <span>{msg.agent}</span>
                <span>Turn {msg.turn}</span>
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-sm text-zinc-100">
                {msg.content}
              </pre>
              {msg.payload ? (
                <details className="mt-3 text-xs text-zinc-300">
                  <summary className="cursor-pointer">Payload</summary>
                  <pre className="mt-2 whitespace-pre-wrap">
                    {JSON.stringify(msg.payload, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          ))}
        </section>

        {finalPayload ? (
          <section className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
            <h3 className="text-sm font-semibold text-white">
              Final workflow payload
            </h3>
            <pre className="mt-3 whitespace-pre-wrap text-xs text-zinc-100">
              {JSON.stringify(finalPayload, null, 2)}
            </pre>
          </section>
        ) : null}
      </div>
    </div>
  );
}
