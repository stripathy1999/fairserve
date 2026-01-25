import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const r = await fetch(
    `${config.zone2Base}/exports/policy-package${qs ? `?${qs}` : ""}`
  );
  const data = await r.text();
  return new NextResponse(data, {
    headers: r.headers,
    status: r.status,
  });
}
