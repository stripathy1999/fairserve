import { NextResponse } from "next/server";
import { getIntakeSummary } from "@/lib/data";

export async function GET() {
  const data = await getIntakeSummary();
  return NextResponse.json(data);
}
