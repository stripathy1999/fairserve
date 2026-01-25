import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function POST(req: Request) {
  const body = await req.json();
  const r = await fetch(`${config.zone2Base}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  return NextResponse.json(data, { status: r.status });
}
