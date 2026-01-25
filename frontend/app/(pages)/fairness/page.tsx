export default async function FairnessPage() {
  const r = await fetch("http://localhost:3000/api/zone2/fairness_metrics", {
    cache: "no-store",
  });
  const data = await r.json();

  return (
    <main className="p-8 space-y-4">
      <h1 className="text-2xl font-semibold">Fairness Metrics</h1>
      <pre className="bg-black text-green-200 p-4 rounded-xl overflow-auto text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
    </main>
  );
}
