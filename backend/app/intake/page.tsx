"use client";

import { useEffect, useMemo, useState } from "react";
import ServiceTypeSelect from "../components/ServiceTypeSelect";
import type { IntakeSummary } from "@/lib/types";

export default function IntakePage() {
  const [data, setData] = useState<IntakeSummary | null>(null);
  const [serviceType, setServiceType] = useState("encampment");
  const [serviceOptions, setServiceOptions] = useState<
    Array<{ value: string; label: string }>
  >([{ value: "encampment", label: "Encampment" }]);

  useEffect(() => {
    let isActive = true;
    const load = async () => {
      const res = await fetch(`/api/intake?service_type=${encodeURIComponent(serviceType)}`);
      const payload = (await res.json()) as IntakeSummary;
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

  const filteredServices = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.byService.filter((row) => row.service_type === serviceType);
  }, [data, serviceType]);

  const example = data?.examples[0];

  return (
    <main style={{ padding: 24 }}>
      <h1>Intake Summary</h1>

      <div style={{ marginTop: 12 }}>
        <ServiceTypeSelect
          options={serviceOptions}
          value={serviceType}
          onChange={setServiceType}
        />
      </div>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginTop: 16,
        }}
      >
        <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Raw tickets</div>
          <div style={{ fontSize: 28, fontWeight: 600 }}>
            {data ? data.totals.rawTickets.toLocaleString() : "—"}
          </div>
        </div>
        <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Canonical incidents</div>
          <div style={{ fontSize: 28, fontWeight: 600 }}>
            {data ? data.totals.canonicalIncidents.toLocaleString() : "—"}
          </div>
        </div>
        <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Duplicates removed %</div>
          <div style={{ fontSize: 28, fontWeight: 600 }}>
            {data ? `${data.totals.duplicatesRemovedPct.toFixed(1)}%` : "—"}
          </div>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2 style={{ marginBottom: 12 }}>Service Summary</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #222" }}>
                <th style={{ padding: "8px 6px" }}>Service</th>
                <th style={{ padding: "8px 6px" }}>Raw</th>
                <th style={{ padding: "8px 6px" }}>Canonical</th>
                <th style={{ padding: "8px 6px" }}>Dup %</th>
                <th style={{ padding: "8px 6px" }}>Mislabels fixed</th>
              </tr>
            </thead>
            <tbody>
              {filteredServices.length === 0 ? (
                <tr>
                  <td style={{ padding: "12px 6px", opacity: 0.7 }} colSpan={5}>
                    No services loaded yet.
                  </td>
                </tr>
              ) : (
                filteredServices.map((row) => (
                  <tr key={row.service_type} style={{ borderBottom: "1px solid #1b1b1b" }}>
                    <td style={{ padding: "8px 6px" }}>{row.service_type}</td>
                    <td style={{ padding: "8px 6px" }}>{row.raw.toLocaleString()}</td>
                    <td style={{ padding: "8px 6px" }}>{row.canonical.toLocaleString()}</td>
                    <td style={{ padding: "8px 6px" }}>{row.dup_pct.toFixed(1)}%</td>
                    <td style={{ padding: "8px 6px" }}>{row.mislabel_fixed.toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2 style={{ marginBottom: 12 }}>Example Redaction</h2>
        {example ? (
          <div style={{ background: "#141414", padding: 16, borderRadius: 12 }}>
            <div style={{ fontSize: 12, opacity: 0.7 }}>
              Service request {example.service_request_id}
            </div>
            <div style={{ marginTop: 8 }}>
              <strong>Before:</strong> {example.before_text}
            </div>
            <div style={{ marginTop: 8 }}>
              <strong>After:</strong> {example.after_redacted_text}
            </div>
            <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
              Category: {example.before_category} → {example.after_service_type}
            </div>
          </div>
        ) : (
          <div style={{ opacity: 0.7 }}>No example available.</div>
        )}
      </section>
    </main>
  );
}
