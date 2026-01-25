import { config } from "@/lib/config";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const qs = url.searchParams.toString();
  const upstream = await fetch(
    `${config.zone2Base}/agents/stream${qs ? `?${qs}` : ""}`,
    {
      headers: { Accept: "text/event-stream" },
    }
  );

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
