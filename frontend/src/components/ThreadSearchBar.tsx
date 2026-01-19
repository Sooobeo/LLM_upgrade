"use client";

type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  matchIndex: number;
  totalMatches: number;
  onPrev: () => void;
  onNext: () => void;
};

export function ThreadSearchBar({
  query,
  onQueryChange,
  onSubmit,
  matchIndex,
  totalMatches,
  onPrev,
  onNext,
}: Props) {
  return (
    <div className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm">
      <input
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit();
        }}
        placeholder="Search in this thread..."
        className="flex-1 text-sm text-slate-800 outline-none"
      />
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-2 py-1 font-semibold">
          {totalMatches > 0 ? `${matchIndex + 1} / ${totalMatches}` : "0 / 0"}
        </span>
        <button
          onClick={onPrev}
          className="rounded-lg px-2 py-1 font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          Prev
        </button>
        <button
          onClick={onNext}
          className="rounded-lg px-2 py-1 font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          Next
        </button>
      </div>
    </div>
  );
}
