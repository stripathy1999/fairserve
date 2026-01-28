import { NextResponse } from "next/server";
import { config } from "@/lib/config";

export async function GET(req: Request) {
  try {
    // 1. Fetch the full City State from Zone 2
    const r = await fetch(`${config.zone2Base}/city_state`);

    if (!r.ok) {
      return new NextResponse(`Failed to fetch city state: ${r.status}`, { status: r.status });
    }

    const cityState = await r.json();

    // 2. Extract Memo
    // Based on workflow.py: state["memo"] = { "raw_text": ..., "parsed_json": ... }
    const memoParams = cityState?.memo;

    if (!memoParams) {
      return new NextResponse("No memo found in current City State. Run simulation first.", { status: 404 });
    }

    // 3. Construct Export Content
    const memoText = memoParams.raw_text || JSON.stringify(memoParams, null, 2);

    // 4. Return as downloadable file
    return new NextResponse(memoText, {
      headers: {
        "Content-Type": "text/markdown",
        "Content-Disposition": 'attachment; filename="fairserve_memo.md"'
      },
      status: 200,
    });

  } catch (e: any) {
    return new NextResponse(`Export failed: ${e.message}`, { status: 500 });
  }
}
