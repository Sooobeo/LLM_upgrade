"use client";

import { ReactNode } from "react";

import { AppHeader } from "./AppHeader";

type Props = {
  children: ReactNode;
};

export function AppLayout({ children }: Props) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
      <AppHeader />
      <main className="pt-16">{children}</main>
    </div>
  );
}
