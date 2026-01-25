import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const r = await fetch(`${config.zone1Base}/live${qs ? `?${qs}` : ""}`, {
    cache: "no-store",
  });
  const data = await r.json();
  return NextResponse.json(data);
}
