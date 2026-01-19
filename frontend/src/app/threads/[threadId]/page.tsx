"use client";

import { ChatView } from "@/components/ChatView";

export default function ThreadDetailPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <ChatView />
      </div>
    </div>
  );
}
