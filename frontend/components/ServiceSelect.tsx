"use client";

type ServiceSelectProps = {
  services: string[];
  value: string;
  onChange: (value: string) => void;
};

export function ServiceSelect({ services, value, onChange }: ServiceSelectProps) {
  return (
    <label className="flex flex-col gap-1 text-sm text-zinc-600">
      Service
      <select
        className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {services.map((service) => (
          <option key={service} value={service}>
            {service}
          </option>
        ))}
      </select>
    </label>
  );
}
