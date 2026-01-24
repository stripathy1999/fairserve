import { NextResponse } from "next/server";
import { getFairnessMetrics } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function GET(req: Request) {
  // Later: use query param service_type to filter real metrics
  const url = new URL(req.url);
  const service = (url.searchParams.get("service_type") || "encampment") as ServiceType;
  const data = await getFairnessMetrics(service);
  return NextResponse.json(data);
}
