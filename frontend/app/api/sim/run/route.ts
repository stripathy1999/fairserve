import { NextResponse } from "next/server";
import { getScenarioAndVerifier } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function POST(req: Request) {
  // Later: forward policies to Shivani simulator + verifier and return both
  const url = new URL(req.url);
  const body = (await req.json().catch(() => ({}))) as {
    service_type?: string;
    chaos?: boolean;
    stress?: "none" | "storm" | "staff" | "duplicate";
  };
  const service = (body.service_type ||
    url.searchParams.get("service_type") ||
    "encampment") as ServiceType;
  const chaos =
    body.chaos ?? (url.searchParams.get("chaos") || "false") === "true";
  const stress =
    body.stress ??
    (url.searchParams.get("stress") as "none" | "storm" | "staff" | "duplicate" | null) ??
    "none";
  const { scenario, verifier } = await getScenarioAndVerifier(service, { chaos, stress });
  return NextResponse.json({ scenario, verifier });
}
