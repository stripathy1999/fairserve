type KpiCardProps = {
  label: string;
  value: string | number;
  helper?: string;
};

export function KpiCard({ label, value, helper }: KpiCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-zinc-900">{value}</p>
      {helper ? <p className="mt-1 text-sm text-zinc-500">{helper}</p> : null}
    </div>
  );
}
