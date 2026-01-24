import type { ChangeEvent } from "react";

export type ServiceOption = {
  value: string;
  label: string;
};

type ServiceTypeSelectProps = {
  label?: string;
  options: ServiceOption[];
  value: string;
  onChange: (next: string) => void;
};

export default function ServiceTypeSelect({
  label = "Service Type",
  options,
  value,
  onChange,
}: ServiceTypeSelectProps) {
  const seen = new Set<string>();
  const uniqueOptions = options.filter((option) => {
    if (seen.has(option.value)) {
      return false;
    }
    seen.add(option.value);
    return true;
  });

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onChange(event.target.value);
  };

  return (
    <label style={{ display: "flex", gap: 12, alignItems: "center" }}>
      <span style={{ fontSize: 12, opacity: 0.7 }}>{label}</span>
      <select
        value={value}
        onChange={handleChange}
        style={{
          background: "#111",
          color: "#f6f6f6",
          border: "1px solid #2a2a2a",
          borderRadius: 8,
          padding: "6px 10px",
        }}
      >
        {uniqueOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
