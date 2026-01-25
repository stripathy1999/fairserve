import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const service = searchParams.get("service");
  const r = await fetch(
    `${config.zone2Base}/agents/evidence${service ? `?service=${encodeURIComponent(service)}` : ""}`
  );
  const data = await r.json();
  return NextResponse.json(data);
}
