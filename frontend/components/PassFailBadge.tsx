type PassFailBadgeProps = {
  pass: boolean;
};

export function PassFailBadge({ pass }: PassFailBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
        pass ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
      }`}
    >
      {pass ? "Pass" : "Fail"}
    </span>
  );
}
