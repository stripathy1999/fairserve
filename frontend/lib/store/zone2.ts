import { http } from "@/lib/http";

export const zone2 = {
  fairnessMetrics: (service?: string) =>
    http<any>(
      `/api/zone2/fairness_metrics${service ? `?service=${encodeURIComponent(service)}` : ""}`
    ),
  cityState: (service?: string) =>
    http<any>(
      `/api/zone2/city_state${service ? `?service=${encodeURIComponent(service)}` : ""}`
    ),
  simulate: (payload: any) =>
    http<any>("/api/zone2/simulate", { method: "POST", body: JSON.stringify(payload) }),
  verify: (payload: any) =>
    http<any>("/api/zone2/verify", { method: "POST", body: JSON.stringify(payload) }),
  refresh: () => http<any>("/api/zone2/refresh", { method: "POST" }),
  propose: (payload: any) =>
    http<any>("/api/agents/propose", { method: "POST", body: JSON.stringify(payload) }),
  evidence: (service?: string) =>
    http<any>(`/api/agents/evidence${service ? `?service=${encodeURIComponent(service)}` : ""}`),
  redteam: (payload: any) =>
    http<any>("/api/agents/redteam", { method: "POST", body: JSON.stringify(payload) }),
  memo: (payload: any) =>
    http<any>("/api/agents/memo", { method: "POST", body: JSON.stringify(payload) }),
  exportPackage: (service: string, policyId: string) =>
    `/api/zone2/export/policy-package?service=${encodeURIComponent(
      service
    )}&policy_id=${encodeURIComponent(policyId)}`,
  exportMemo: (service: string, policyId: string) =>
    `/api/zone2/export/memo?service=${encodeURIComponent(
      service
    )}&policy_id=${encodeURIComponent(policyId)}`,
};
