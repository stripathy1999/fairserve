import { NextResponse } from "next/server";
import { getRedTeamReport } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function POST(req: Request) {
  // Later: call Nemotron red team with city_state + scenario + verifier
  const url = new URL(req.url);
  const body = (await req.json().catch(() => ({}))) as { service_type?: string };
  const service = (body.service_type ||
    url.searchParams.get("service_type") ||
    "encampment") as ServiceType;
  const data = await getRedTeamReport(service);
  return NextResponse.json(data);
}
