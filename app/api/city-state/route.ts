import { NextResponse } from "next/server";
import { getCityState } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const service = (url.searchParams.get("service_type") || "encampment") as ServiceType;
  const data = await getCityState(service);
  return NextResponse.json(data);
}
