import { NextResponse } from "next/server";
import { getFinalMemo } from "@/lib/data";
import type { ServiceType } from "@/lib/types";

export async function POST(req: Request) {
  // Later: call Nemotron arbiter and return memo
  const url = new URL(req.url);
  const body = (await req.json().catch(() => ({}))) as { service_type?: string };
  const service = (body.service_type ||
    url.searchParams.get("service_type") ||
    "encampment") as ServiceType;
  const memo = await getFinalMemo(service);
  return NextResponse.json({ memo });
}
