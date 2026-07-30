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
    <div className="flex w-full flex-col gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex-row sm:items-center">
      <input
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit();
        }}
        placeholder="Search in this thread..."
        className="min-h-10 w-full min-w-0 flex-1 text-sm text-slate-800 outline-none"
      />
      <div className="flex w-full items-center gap-1.5 text-xs text-slate-500 sm:w-auto sm:gap-2">
        <span className="mr-auto shrink-0 rounded-full bg-slate-100 px-2 py-1 font-semibold sm:mr-0">
          {totalMatches > 0 ? `${matchIndex + 1} / ${totalMatches}` : "0 / 0"}
        </span>
        <button
          onClick={onPrev}
          aria-label="이전 검색 결과"
          className="min-h-9 rounded-lg px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          이전
        </button>
        <button
          onClick={onNext}
          aria-label="다음 검색 결과"
          className="min-h-9 rounded-lg px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-100"
        >
          다음
        </button>
      </div>
    </div>
  );
}
