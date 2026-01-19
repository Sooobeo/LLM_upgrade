"use client";

import Link from "next/link";

type Props = {
  title?: string;
  message?: string;
};

export function InlineLoginPrompt({
  title = "Sign in required",
  message = "Sign in to view this content.",
}: Props) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-slate-800 shadow-sm">
      <div className="text-lg font-semibold">{title}</div>
      <p className="mt-2 text-sm text-slate-600">{message}</p>
      <div className="mt-4 flex gap-3">
        <Link
          href="/login"
          className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
        >
          Go to login
        </Link>
      </div>
    </div>
  );
}
