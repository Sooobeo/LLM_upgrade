"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { createThread, postChat } from "@/lib/threadApi";

const MODEL_OPTIONS = ["gemma3:270m", "llama3.1:8b", "mistral:7b"];
const FALLBACK_MODEL = process.env.NEXT_PUBLIC_FALLBACK_MODEL;

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: (threadId: string) => void;
  token: string | null;
};

export function NewThreadModal({ isOpen, onClose, onCreated, token }: Props) {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2>(1);
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [model, setModel] = useState<string>(MODEL_OPTIONS[0]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setTitle("");
      setMessage("");
      setError(null);
    }
  }, [isOpen]);

  const createMutation = useMutation({
    mutationFn: async () => {
      setError(null);
      if (FALLBACK_MODEL && model !== FALLBACK_MODEL) {
        setError(`현재 사용 가능한 모델은 ${FALLBACK_MODEL} 입니다.`);
        throw new Error("MODEL_NOT_AVAILABLE");
      }
      if (!token) {
        const err: any = new Error("Not logged in");
        err.code = "NO_TOKEN";
        throw err;
      }

      // Simple flow: create with first user message, then ask /chat to get assistant reply.
      // If you ever see duplicated first messages, switch to the workaround:
      // 1) call createThread({ title, messages: [] })
      // 2) then call postChat with the first message
      const createResp = await createThread({
        title: title || "Untitled thread",
        messages: [{ role: "user", content: message }],
      }, token);

      const threadId =
        createResp?.thread_id || createResp?.id || createResp?.threadId;
      if (!threadId) throw new Error("thread_id not returned");

      await postChat(
        threadId,
        {
          content: message,
          model,
          context_limit: 50,
        },
        token,
      );

      return threadId as string;
    },
    onSuccess: (threadId) => {
      onCreated?.(threadId);
      onClose();
      router.push(`/threads/${threadId}`);
    },
    onError: (err: any) => {
      const noToken = err?.code === "NO_TOKEN" ? "Not logged in" : null;
      setError(noToken || err?.message || "새 스레드 생성에 실패했습니다.");
    },
  });

  const canProceed = useMemo(() => title.trim().length > 0 && message.trim().length > 0, [title, message]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">New Thread</p>
            <h2 className="text-xl font-bold text-slate-900">Step {step} / 2</h2>
          </div>
          <button
            className="text-sm text-slate-500 transition hover:text-slate-800"
            onClick={() => {
              setStep(1);
              setTitle("");
              setMessage("");
              onClose();
            }}
          >
            ✕
          </button>
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-700">Title</label>
              <input
                className="w-full rounded-lg border border-slate-200
                          bg-white text-slate-900
                          px-3 py-2 text-sm
                          placeholder:text-slate-400
                          focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Thread title"
              />

            </div>
            <div>
              <label className="mb-1 block text-sm font-semibold text-slate-700">First message</label>
              <textarea
                className="min-h-[120px] w-full rounded-lg border border-slate-200
                          bg-white text-slate-900
                          px-3 py-2 text-sm
                          placeholder:text-slate-400
                          focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="What do you want to ask?"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
                onClick={onClose}
              >
                Cancel
              </button>
              <button
                disabled={!canProceed}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition disabled:opacity-50"
                onClick={() => setStep(2)}
              >
                Next
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-700">Select model</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {MODEL_OPTIONS.map((m) => (
                  <button
                    key={m}
                    onClick={() => setModel(m)}
                    className={`rounded-xl border px-3 py-3 text-sm font-semibold transition ${
                      model === m
                        ? "border-blue-600 bg-blue-50 text-blue-700 shadow-sm"
                        : "border-slate-200 bg-white text-slate-800 hover:border-blue-200"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}

            <div className="flex justify-between gap-2">
              <button
                className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
                onClick={() => setStep(1)}
              >
                Back
              </button>
              <button
                disabled={createMutation.isPending}
                className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition disabled:opacity-60"
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? "Starting..." : "Start"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
