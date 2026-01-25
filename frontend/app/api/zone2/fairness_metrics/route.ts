import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET() {
  const r = await fetch(`${config.zone2Base}/fairness_metrics`, {
    cache: "no-store",
  });
  const data = await r.json();
  return NextResponse.json(data);
}
