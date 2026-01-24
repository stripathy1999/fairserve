import path from "path";
import { promises as fs } from "fs";
import type {
  CityState,
  FairnessMetrics,
  IntakeSummary,
  PoliciesResponse,
  RedTeamReport,
  ScenarioResults,
  ServiceType,
  VerifierOutputs,
} from "@/lib/types";

const DEMO_DIR = path.join(process.cwd(), "demo");
export const REAL_OUTPUTS_DIR = path.join(process.cwd(), "data", "processed");

const DEMO_MODE = process.env.DEMO_MODE !== "false";

async function readJson<T>(filename: string, baseDir: string): Promise<T> {
  const p = path.join(baseDir, filename);
  const raw = await fs.readFile(p, "utf-8");
  return JSON.parse(raw) as T;
}

async function readText(filename: string, baseDir: string): Promise<string> {
  const p = path.join(baseDir, filename);
  return fs.readFile(p, "utf-8");
}

function getBaseDir(): string {
  return DEMO_MODE ? DEMO_DIR : REAL_OUTPUTS_DIR;
}

export async function getIntakeSummary(): Promise<IntakeSummary> {
  return readJson<IntakeSummary>("intake_summary.json", getBaseDir());
}

export async function getFairnessMetrics(_service: ServiceType): Promise<FairnessMetrics> {
  return readJson<FairnessMetrics>("fairness_metrics.json", getBaseDir());
}

export async function getCityState(_service: ServiceType): Promise<CityState> {
  return readJson<CityState>("city_state.json", getBaseDir());
}

export async function getPolicies(_service: ServiceType): Promise<PoliciesResponse> {
  return readJson<PoliciesResponse>("policies.json", getBaseDir());
}

export async function getScenarioAndVerifier(
  _service: ServiceType,
  options?: { chaos?: boolean; stress?: "none" | "storm" | "staff" | "duplicate" }
): Promise<{ scenario: ScenarioResults; verifier: VerifierOutputs }> {
  const baseDir = getBaseDir();
  const scenario = await readJson<ScenarioResults>("scenario_results.json", baseDir);
  const verifier = await readJson<VerifierOutputs>("verifier_outputs.json", baseDir);

  if (DEMO_MODE && options?.chaos) {
    const chaosTarget = "P_PASS";
    const chaosBacklogDelta = 12.0;
    const chaosReason = "Backlog cap violated: 12.0% > 8%";

    scenario.results = scenario.results.map((result) => {
      if (result.policy_id !== chaosTarget) {
        return result;
      }
      return {
        ...result,
        backlog_delta_pct: chaosBacklogDelta,
      };
    });

    verifier.verdicts = verifier.verdicts.map((verdict) => {
      if (verdict.policy_id !== chaosTarget) {
        return verdict;
      }
      return {
        ...verdict,
        pass: false,
        reasons: [chaosReason],
        constraint_values: {
          ...verdict.constraint_values,
          backlog_change_pct: chaosBacklogDelta,
        },
      };
    });
  }

  if (DEMO_MODE && options?.stress && options.stress !== "none") {
    const stressTarget = "P_PASS";
    const stressMap = {
      storm: {
        backlogDelta: 13.2,
        reason: "Backlog cap violated: 13.2% > 8%",
      },
      staff: {
        backlogDelta: 11.5,
        reason: "Capacity shock violated backlog cap: 11.5% > 8%",
      },
      duplicate: {
        backlogDelta: 10.4,
        reason: "Duplicate surge violated backlog cap: 10.4% > 8%",
      },
    } as const;

    const stress = stressMap[options.stress];

    scenario.results = scenario.results.map((result) => {
      if (result.policy_id !== stressTarget) {
        return result;
      }
      return {
        ...result,
        backlog_delta_pct: stress.backlogDelta,
      };
    });

    verifier.verdicts = verifier.verdicts.map((verdict) => {
      if (verdict.policy_id !== stressTarget) {
        return verdict;
      }
      return {
        ...verdict,
        pass: false,
        reasons: [stress.reason],
        constraint_values: {
          ...verdict.constraint_values,
          backlog_change_pct: stress.backlogDelta,
        },
      };
    });
  }

  return { scenario, verifier };
}

export async function getRedTeamReport(_service: ServiceType): Promise<RedTeamReport> {
  return readJson<RedTeamReport>("redteam_report.json", getBaseDir());
}

export async function getFinalMemo(_service: ServiceType): Promise<string> {
  return readText("final_memo.md", getBaseDir());
}
