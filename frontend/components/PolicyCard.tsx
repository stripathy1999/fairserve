import { PolicyProposal } from "@/lib/types";

type PolicyCardProps = {
  policy: PolicyProposal;
  onSelect?: () => void;
};

export function PolicyCard({ policy, onSelect }: PolicyCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900">{policy.policy_id}</h3>
        {onSelect ? (
          <button
            className="rounded-md bg-zinc-900 px-3 py-1 text-xs font-medium text-white"
            onClick={onSelect}
          >
            Use policy
          </button>
        ) : null}
      </div>
      <div className="mt-3 text-xs text-zinc-600">
        <p>Capacity shift: {policy.parameters.capacity_shift_pct}</p>
        <p>Efficiency bonus: {policy.parameters.efficiency_bonus_pct}</p>
        <p>Max reassignments: {policy.parameters.max_reassignments}</p>
      </div>
      {policy.rationale ? (
        <p className="mt-2 text-sm text-zinc-500">{policy.rationale}</p>
      ) : null}
    </div>
  );
}
