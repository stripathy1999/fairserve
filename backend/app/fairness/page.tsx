"use client";

import { useEffect, useMemo, useState } from "react";
import ServiceTypeSelect from "../components/ServiceTypeSelect";
import type { FairnessMetrics } from "@/lib/types";

export default function FairnessPage() {
  const [data, setData] = useState<FairnessMetrics | null>(null);
  const [serviceType, setServiceType] = useState("encampment");
  const [serviceOptions, setServiceOptions] = useState([
    { value: "encampment", label: "Encampment" },
  ]);

  useEffect(() => {
    let isActive = true;
    const load = async () => {
      const res = await fetch(`/api/metrics?service_type=${encodeURIComponent(serviceType)}`);
      const payload = (await res.json()) as FairnessMetrics;
      if (isActive) {
        setData(payload);
      }
    };
    load();
    return () => {
      isActive = false;
    };
  }, [serviceType]);

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

  const rows = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.rows.filter((row) => row.service_type === serviceType);
  }, [data, serviceType]);

  return (
    <main style={{ padding: 24 }}>
      <h1>Fairness Leaderboard</h1>

      <div style={{ marginTop: 12 }}>
        <ServiceTypeSelect
          options={serviceOptions}
          value={serviceType}
          onChange={setServiceType}
        />
      </div>

      <section style={{ marginTop: 20 }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #222" }}>
                <th style={{ padding: "8px 6px" }}>Neighborhood</th>
                <th style={{ padding: "8px 6px" }}>N</th>
                <th style={{ padding: "8px 6px" }}>p50 (hr)</th>
                <th style={{ padding: "8px 6px" }}>p90 (hr)</th>
                <th style={{ padding: "8px 6px" }}>p90 ratio</th>
                <th style={{ padding: "8px 6px" }}>Unfair z</th>
                <th style={{ padding: "8px 6px" }}>Open backlog</th>
                <th style={{ padding: "8px 6px" }}>Aging 14d</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td style={{ padding: "12px 6px", opacity: 0.7 }} colSpan={8}>
                    No metrics loaded yet.
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={`${row.neighborhood}-${row.service_type}`} style={{ borderBottom: "1px solid #1b1b1b" }}>
                    <td style={{ padding: "8px 6px" }}>{row.neighborhood}</td>
                    <td style={{ padding: "8px 6px" }}>{row.N.toLocaleString()}</td>
                    <td style={{ padding: "8px 6px" }}>{row.p50_hr.toFixed(1)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.p90_hr.toFixed(1)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.ratio_p90.toFixed(2)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.unfair_z.toFixed(2)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.open_backlog.toLocaleString()}</td>
                    <td style={{ padding: "8px 6px" }}>{row.aging_tail_14d.toFixed(2)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
