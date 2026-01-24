"use client";

import { useEffect, useState } from "react";
import ServiceTypeSelect from "../components/ServiceTypeSelect";
import type { PoliciesResponse } from "@/lib/types";

export default function PolicyPage() {
  const [data, setData] = useState<PoliciesResponse | null>(null);
  const [serviceType, setServiceType] = useState("encampment");
  const [serviceOptions, setServiceOptions] = useState([
    { value: "encampment", label: "Encampment" },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);

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

  const handleGenerate = async () => {
    setIsLoading(true);
    const res = await fetch(
      `/api/policies/generate?service_type=${encodeURIComponent(serviceType)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service_type: serviceType }),
      }
    );
    const payload = (await res.json()) as PoliciesResponse;
    setData(payload);
    setIsLoading(false);
  };

  const handleSelectPolicy = (policyId: string) => {
    setSelectedPolicyId(policyId);
    if (typeof window !== "undefined") {
      sessionStorage.setItem("fairserve:selectedServiceType", serviceType);
      sessionStorage.setItem("fairserve:selectedPolicyId", policyId);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Policy Proposals</h1>

      <div style={{ marginTop: 12 }}>
        <ServiceTypeSelect
          options={serviceOptions}
          value={serviceType}
          onChange={(next) => {
            setServiceType(next);
            setData(null);
          }}
        />
      </div>

      <div style={{ marginTop: 12 }}>
        <button
          onClick={handleGenerate}
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
          {isLoading ? "Generating..." : "Generate policies"}
        </button>
      </div>

      <section style={{ marginTop: 20 }}>
        {data ? (
          <div style={{ display: "grid", gap: 12 }}>
            {data.policies.map((policy) => (
              <div
                key={policy.policy_id}
                style={{ background: "#141414", padding: 16, borderRadius: 12 }}
              >
                <div style={{ fontSize: 14, opacity: 0.7 }}>{policy.policy_id}</div>
                <div style={{ marginTop: 8 }}>
                  Capacity shift: {policy.knobs.capacity_shift_pct}%
                </div>
                <div>Priority: {policy.knobs.priority_weighting}</div>
                <div>Efficiency bonus: {policy.knobs.efficiency_bonus_pct}%</div>
                {policy.rationale && policy.rationale.length > 0 ? (
                  <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                    {policy.rationale.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
                <div style={{ marginTop: 12, display: "flex", gap: 12, alignItems: "center" }}>
                  <button
                    onClick={() => handleSelectPolicy(policy.policy_id)}
                    style={{
                      background: "#2d2d2d",
                      color: "#fff",
                      border: "1px solid #3b3b3b",
                      padding: "8px 12px",
                      borderRadius: 8,
                      cursor: "pointer",
                    }}
                  >
                    Select for simulation
                  </button>
                  {selectedPolicyId === policy.policy_id ? (
                    <span style={{ fontSize: 12, opacity: 0.7 }}>Selected</span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ opacity: 0.7, marginTop: 12 }}>
            Click "Generate policies" to load results.
          </div>
        )}
      </section>
    </main>
  );
}
