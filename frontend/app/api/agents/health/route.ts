import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET() {
  const r = await fetch(`${config.zone2Base}/agents/health`, {
    cache: "no-store",
  });
  const text = await r.text();
  if (!r.ok) {
    return NextResponse.json({ ok: false, error: text || "Upstream error" }, { status: 200 });
  }
  try {
    return NextResponse.json(JSON.parse(text));
  } catch {
    return NextResponse.json({ ok: false, error: text || "Invalid JSON" }, { status: 200 });
  }
}
