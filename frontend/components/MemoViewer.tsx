type MemoViewerProps = {
  title: string;
  content: string;
};

export function MemoViewer({ title, content }: MemoViewerProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-900">{title}</h3>
      <pre className="mt-2 whitespace-pre-wrap text-sm text-zinc-600">
        {content}
      </pre>
    </div>
  );
}
