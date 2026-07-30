"use client";

import { ChatView } from "@/components/ChatView";

export default function ThreadDetailPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022]">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <ChatView />
      </div>
    </div>
  );
}
