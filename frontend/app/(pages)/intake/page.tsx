"use client";

import { useEffect, useMemo, useState } from "react";

type Incident = {
  incident_id?: string;
  service_type?: string;
  neighborhood?: string;
  opened_at?: string;
  status?: string;
  is_duplicate?: boolean;
  service_type_confidence?: number;
  description_redacted?: string;
  agency?: string;
  source?: string;
  address?: string;
  priority?: string | number;
  category?: string;
  channel?: string;
  canonical_incident_id?: string;
};

export default function IntakePage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/zone1/live?limit=50&minutes_back=60", {
        cache: "no-store",
      });
      const data = await r.json();
      setIncidents(data.data || []);
      setSelected((prev) =>
        prev ? data.data.find((i: Incident) => i.incident_id === prev.incident_id) || null : null
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const rows = useMemo(
    () =>
      incidents.map((incident) => ({
        id: incident.incident_id,
        service_type: incident.service_type,
        neighborhood: incident.neighborhood,
        opened_at: incident.opened_at
          ? new Date(incident.opened_at).toLocaleString()
          : "-",
        status: incident.status,
        duplicate: incident.is_duplicate ? "Yes" : "No",
        confidence: incident.service_type_confidence
          ? `${Math.round(incident.service_type_confidence * 100)}%`
          : "-",
      })),
    [incidents]
  );

  return (
    <main className="p-8 space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">
            Intake Firewall — Live Feed
          </h1>
          <p className="text-sm text-zinc-500">
            Last 60 minutes, max 50 records. Click a row to view details.
          </p>
        </div>
        <button
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm text-zinc-700"
          onClick={fetchIncidents}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      <div className="overflow-auto rounded-lg border border-zinc-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-zinc-100 text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-4 py-2">Incident</th>
              <th className="px-4 py-2">Service</th>
              <th className="px-4 py-2">Neighborhood</th>
              <th className="px-4 py-2">Opened</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Duplicate</th>
              <th className="px-4 py-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className={`cursor-pointer border-t border-zinc-200 hover:bg-zinc-50 ${
                  selected?.incident_id === row.id ? "bg-emerald-50" : ""
                }`}
                onClick={() =>
                  setSelected(incidents.find((i) => i.incident_id === row.id) || null)
                }
              >
                <td className="px-4 py-2 text-zinc-700">{row.id}</td>
                <td className="px-4 py-2 text-zinc-700">{row.service_type}</td>
                <td className="px-4 py-2 text-zinc-700">{row.neighborhood}</td>
                <td className="px-4 py-2 text-zinc-700">{row.opened_at}</td>
                <td className="px-4 py-2 text-zinc-700">{row.status}</td>
                <td className="px-4 py-2 text-zinc-700">{row.duplicate}</td>
                <td className="px-4 py-2 text-zinc-700">{row.confidence}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-zinc-500" colSpan={7}>
                  No live incidents in the last 60 minutes.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {selected ? (
        <section className="rounded-lg border border-zinc-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-zinc-900">Incident details</h3>
          <div className="mt-3 grid gap-3 text-sm text-zinc-700 md:grid-cols-2">
            <div>
              <div className="text-xs uppercase text-zinc-400">Description</div>
              <p className="mt-1">{selected.description_redacted || "No description."}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Service</div>
              <p className="mt-1">{selected.service_type || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Agency</div>
              <p className="mt-1">{selected.agency || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Source</div>
              <p className="mt-1">{selected.source || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Neighborhood</div>
              <p className="mt-1">{selected.neighborhood || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Address</div>
              <p className="mt-1">{selected.address || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Opened at</div>
              <p className="mt-1">
                {selected.opened_at ? new Date(selected.opened_at).toLocaleString() : "-"}
              </p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Priority</div>
              <p className="mt-1">{selected.priority ?? "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Category</div>
              <p className="mt-1">{selected.category || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Channel</div>
              <p className="mt-1">{selected.channel || "-"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Duplicate</div>
              <p className="mt-1">{selected.is_duplicate ? "Yes" : "No"}</p>
            </div>
            <div>
              <div className="text-xs uppercase text-zinc-400">Confidence</div>
              <p className="mt-1">
                {selected.service_type_confidence
                  ? `${Math.round(selected.service_type_confidence * 100)}%`
                  : "-"}
              </p>
            </div>
          </div>
          <details className="mt-4 text-xs text-zinc-500">
            <summary className="cursor-pointer">All incident fields</summary>
            <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-600">
              {JSON.stringify(selected, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}
    </main>
  );
}
