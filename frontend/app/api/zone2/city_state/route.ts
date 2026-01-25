import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET() {
  const r = await fetch(`${config.zone2Base}/city_state`, {
    cache: "no-store",
  });
  const data = await r.json();
  return NextResponse.json(data);
}
