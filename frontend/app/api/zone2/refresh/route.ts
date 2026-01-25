import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function POST() {
  const r = await fetch(`${config.zone2Base}/refresh`, { method: "POST" });
  const data = await r.json();
  return NextResponse.json(data);
}
