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
    <div className="space-y-8">
      <section>
        <h2 className="text-2xl font-semibold text-zinc-900">
          FairServe Operations Console
        </h2>
        <p className="mt-2 text-sm text-zinc-600">
          Tools for city operations: intake, fairness, policy lab, review, and
          agentic workflow.
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
          className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/intake${serviceParam}`}
        >
          Go to Intake
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/fairness${serviceParam}`}
        >
          Go to Fairness
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/policy${serviceParam}`}
        >
          Go to Policy
        </a>
        <a
          className="rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm font-medium text-zinc-700 shadow-sm hover:border-zinc-300"
          href={`/review${serviceParam}`}
        >
          Go to Review
        </a>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          {
            title: "Intake Firewall",
            desc: "Live 311 feed with dedup, repair, redaction.",
            href: `/intake${serviceParam}`,
          },
          {
            title: "Fairness Leaderboard",
            desc: "Worst neighborhoods by service response time.",
            href: `/fairness${serviceParam}`,
          },
          {
            title: "Policy Lab",
            desc: "Simulate and verify candidate policies.",
            href: `/policy${serviceParam}`,
          },
          {
            title: "Executive Review",
            desc: "PASS/FAIL, red-team risks, memo output.",
            href: `/review${serviceParam}`,
          },
          {
            title: "Agent Ops Room",
            desc: "Watch Nemotron agents debate and decide.",
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
    </div>
  );
}
