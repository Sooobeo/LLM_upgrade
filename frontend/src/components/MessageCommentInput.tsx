"use client";

import { useState } from "react";

type Props = {
  onAdd: (text: string) => void;
};

export function MessageCommentInput({ onAdd }: Props) {
  const [value, setValue] = useState("");
  return (
    <div className="flex flex-col gap-2 sm:flex-row">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            const v = value.trim();
            if (!v) return;
            onAdd(v);
            setValue("");
          }
        }}
        placeholder="코멘트를 입력하세요"
        className="min-h-10 min-w-0 flex-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-white placeholder:text-white/40 focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <button
        type="button"
        onClick={() => {
          const v = value.trim();
          if (!v) return;
          onAdd(v);
          setValue("");
        }}
        disabled={!value.trim()}
        className="min-h-10 rounded-lg bg-blue-500 px-3 py-1 text-xs font-semibold text-white hover:bg-blue-600 sm:min-h-0"
      >
        추가
      </button>
    </div>
  );
}
