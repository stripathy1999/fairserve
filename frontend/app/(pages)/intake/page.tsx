export default async function IntakePage() {
  const r = await fetch(
    "http://localhost:3000/api/zone1/live?limit=50&minutes_back=60",
    { cache: "no-store" }
  );
  const data = await r.json();

  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">Intake Firewall — Live Feed</h1>
      <p className="text-sm text-gray-500">
        Showing last 60 minutes (max 50 records).
      </p>
      <pre className="bg-black text-green-200 p-4 rounded-xl overflow-auto text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
    </main>
  );
}
