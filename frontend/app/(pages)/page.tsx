"use client";

import { useEffect, useMemo, useState } from "react";
import { zone2 } from "@/lib/store/zone2";
import { ServiceSelect } from "@/components/ServiceSelect";

export default function HomePage() {
  const [services, setServices] = useState<string[]>([]);
  const [service, setService] = useState("");

  useEffect(() => {
    zone2.fairnessMetrics().then((data) => {
      const list = Array.from(
        new Set((data.metrics || []).map((row: any) => row.service_type))
      ).filter(Boolean);
      setServices(list);
      setService(list[0] || "");
    });
  }, []);

  const serviceParam = useMemo(
    () => (service ? `?service=${encodeURIComponent(service)}` : ""),
    [service]
  );

  return (
    <div className="space-y-10">
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <p className="text-xs uppercase tracking-widest text-emerald-600">
          FairServe Operations Console
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-zinc-900">
          City services, fairness, and policy decisions—one view.
        </h2>
        <p className="mt-3 text-sm text-zinc-600">
          Monitor live incidents, identify equity gaps, simulate policy levers, and track the
          agentic workflow from proposal to memo.
        </p>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4">
        {services.length > 0 ? (
          <ServiceSelect
            services={services}
            value={service}
            onChange={setService}
          />
        ) : (
          <p className="text-sm text-zinc-500">Loading services...</p>
        )}
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-4 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/intake${serviceParam}`}
        >
          Go to Intake →
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-4 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/fairness${serviceParam}`}
        >
          Go to Fairness →
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-4 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/policy${serviceParam}`}
        >
          Go to Policy Lab →
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-4 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/review${serviceParam}`}
        >
          Go to Review →
        </a>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          {
            title: "Intake Firewall",
            desc: "Live 311 feed with dedup, repair, and redaction checks.",
            href: `/intake${serviceParam}`,
          },
          {
            title: "Fairness Leaderboard",
            desc: "Rank neighborhoods by p90 response time and equity gaps.",
            href: `/fairness${serviceParam}`,
          },
          {
            title: "Policy Lab",
            desc: "Tune capacity + efficiency levers and verify constraints.",
            href: `/policy${serviceParam}`,
          },
          {
            title: "Executive Review",
            desc: "PASS/FAIL, constraint reasons, red-team risks, memo output.",
            href: `/review${serviceParam}`,
          },
          {
            title: "Agent Ops Room",
            desc: "Watch Nemotron agents debate and decide in real time.",
            href: `/agents${serviceParam}`,
          },
        ].map((item) => (
          <a
            key={item.title}
            href={item.href}
            className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm hover:border-zinc-300"
          >
            <h3 className="text-sm font-semibold text-zinc-900">{item.title}</h3>
            <p className="mt-2 text-xs text-zinc-500">{item.desc}</p>
          </a>
        ))}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4 text-sm text-zinc-600">
        <div className="text-xs font-semibold uppercase text-zinc-400">What you can do</div>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          <div>✔️ Monitor live incidents and investigate details quickly.</div>
          <div>✔️ Compare neighborhood fairness and identify worst‑k areas.</div>
          <div>✔️ Simulate policy levers and see constraints immediately.</div>
          <div>✔️ Track the agentic workflow and export final memos.</div>
        </div>
      </section>
    </div>
  );
}
