import { NextResponse } from "next/server";
import { getPolicies } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function POST(req: Request) {
  // Later: call Nemotron proposer with city_state
  const url = new URL(req.url);
  const body = (await req.json().catch(() => ({}))) as { service_type?: string };
  const service = (body.service_type ||
    url.searchParams.get("service_type") ||
    "encampment") as ServiceType;
  const data = await getPolicies(service);
  return NextResponse.json(data);
}
