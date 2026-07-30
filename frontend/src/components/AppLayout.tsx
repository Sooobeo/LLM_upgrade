"use client";

import { ReactNode } from "react";

import { AppHeader } from "./AppHeader";

type Props = {
  children: ReactNode;
};

export function AppLayout({ children }: Props) {
  return (
    <div className="min-h-[100dvh] bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
      <AppHeader />
      <main className="min-w-0 pt-[calc(3.5rem+env(safe-area-inset-top))]">
        {children}
      </main>
    </div>
  );
}
