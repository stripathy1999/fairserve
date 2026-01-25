type MemoViewerProps = {
  title: string;
  parsed: any;
  rawText?: string | null;
  validationStatus?: string | null;
};

const statusBadge = (status?: string | null) => {
  if (status === "valid") {
    return (
      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">
        ✅ Valid
      </span>
    );
  }
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
      ⚠️ Check
    </span>
  );
};

export function MemoViewer({ title, parsed, rawText, validationStatus }: MemoViewerProps) {
  const renderContent = () => {
    if (!parsed || typeof parsed !== "object") {
      return (
        <p className="mt-2 text-sm text-zinc-600">No structured output available yet.</p>
      );
    }

    if (Array.isArray(parsed?.summary) || typeof parsed?.memo === "string") {
      return (
        <div className="mt-2 space-y-3 text-sm text-zinc-700">
          {Array.isArray(parsed.summary) ? (
            <ul className="list-disc space-y-1 pl-5">
              {parsed.summary.map((item: string, idx: number) => (
                <li key={`${title}-summary-${idx}`}>{item}</li>
              ))}
            </ul>
          ) : null}
          {parsed.memo ? <p className="text-sm text-zinc-600">{parsed.memo}</p> : null}
        </div>
      );
    }

    if (Array.isArray(parsed?.risks) || Array.isArray(parsed?.recommendations)) {
      return (
        <div className="mt-2 grid gap-3 text-sm text-zinc-700">
          {Array.isArray(parsed.risks) ? (
            <div>
              <div className="text-xs font-semibold uppercase text-zinc-400">Risks</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {parsed.risks.map((risk: string, idx: number) => (
                  <li key={`${title}-risk-${idx}`}>{risk}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {Array.isArray(parsed.recommendations) ? (
            <div>
              <div className="text-xs font-semibold uppercase text-zinc-400">Recommendations</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {parsed.recommendations.map((rec: string, idx: number) => (
                  <li key={`${title}-rec-${idx}`}>{rec}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      );
    }

    return (
      <pre className="mt-2 whitespace-pre-wrap text-sm text-zinc-600">
        {JSON.stringify(parsed, null, 2)}
      </pre>
    );
  };

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-900">{title}</h3>
        {statusBadge(validationStatus)}
      </div>
      {renderContent()}
      {rawText ? (
        <details className="mt-3 text-xs text-zinc-500">
          <summary className="cursor-pointer">View raw</summary>
          <pre className="mt-2 whitespace-pre-wrap text-xs text-zinc-500">
            {rawText}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
