export type ServiceType =
  | "encampment"
  | "cleaning_trash"
  | "graffiti"
  | string;

export type IntakeSummary = {
  lastSyncAt: string;
  windowDays: number;
  totals: {
    rawTickets: number;
    canonicalIncidents: number;
    duplicatesRemovedPct: number;
    mislabelsCorrectedCount: number;
    redactionsCount: number;
    neighborhoodUnknownPct: number;
  };
  byService: Array<{
    service_type: ServiceType;
    raw: number;
    canonical: number;
    dup_pct: number;
    mislabel_fixed: number;
  }>;
  examples: Array<{
    service_request_id: string;
    before_category: string;
    after_service_type: ServiceType;
    before_text: string;
    after_redacted_text: string;
  }>;
};

export type FairnessRow = {
  service_type: ServiceType;
  neighborhood: string;
  N: number;
  p50_hr: number;
  p90_hr: number;
  ratio_p90: number;
  unfair_z: number;
  open_backlog: number;
  aging_tail_14d: number;
};

export type FairnessMetrics = {
  generatedAt: string;
  windowDays: number;
  service_types: ServiceType[];
  city_baselines: Record<string, { p50_hr: number; p90_hr: number }>;
  rows: FairnessRow[];
};

export type Policy = {
  policy_id: string;
  knobs: {
    capacity_shift_pct: number;
    priority_weighting: "worst_only" | "backlog_pressure" | "hybrid";
    efficiency_bonus_pct: number;
  };
  rationale?: string[];
};

export type PoliciesResponse = {
  service_type: ServiceType;
  policies: Policy[];
};

export type ScenarioResult = {
  policy_id: string;
  citywide_p90_delta_pct: number;
  backlog_delta_pct: number;
  p90_delta_by_neighborhood_pct: Record<string, number>;
  equity_gain_score: number;
};

export type ScenarioResults = {
  service_type: ServiceType;
  results: ScenarioResult[];
};

export type VerifierVerdict = {
  policy_id: string;
  pass: boolean;
  reasons: string[];
  constraint_values: {
    worst_k_improve_pct: number;
    max_harm_pct: number;
    backlog_change_pct: number;
  };
};

export type VerifierOutputs = {
  service_type: ServiceType;
  verdicts: VerifierVerdict[];
};

export type CityState = {
  service_type: ServiceType;
  generatedAt: string;
  city_baseline: { p50_hr: number; p90_hr: number };
  worst_neighborhoods: string[];
  neighborhoods: Array<Record<string, any>>;
  constitution: {
    worst_k: number;
    min_improve_worst_pct: number;
    max_harm_any_pct: number;
    max_backlog_increase_pct: number;
    citywide_p90_nonworsen: boolean;
  };
  available_knobs: Record<string, any>;
};

export type RedTeamReport = {
  service_type: ServiceType;
  policy_id: string;
  risks: Array<{ type: string; severity: "low" | "medium" | "high"; detail: string }>;
  mitigations: string[];
};
