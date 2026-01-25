"use client";

import { useState } from "react";

type Props = {
  onAdd: (text: string) => void;
};

export function WorkspaceCommentInput({ onAdd }: Props) {
  const [value, setValue] = useState("");
  return (
    <div className="flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="코멘트 추가"
        className="flex-1 rounded-lg border border-slate-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
      />
      <button
        type="button"
        onClick={() => {
          const v = value.trim();
          if (!v) return;
          onAdd(v);
          setValue("");
        }}
        className="rounded-lg bg-blue-500 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-600"
      >
        추가
      </button>
    </div>
  );
}
