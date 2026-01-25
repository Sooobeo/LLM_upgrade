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
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            const v = value.trim();
            if (!v) return;
            onAdd(v);
            setValue("");
          }
        }}
        placeholder="코멘트 추가"
        className="flex-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-white placeholder:text-white/40 focus:outline-none focus:ring-1 focus:ring-blue-400"
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
        className="rounded-lg bg-blue-500 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-600"
      >
        추가
      </button>
    </div>
  );
}
