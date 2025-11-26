"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppLayout } from "@/components/AppLayout";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { api } from "@/lib/api";

type ExtensionFile = {
  id: number;
  name: string;
  description?: string | null;
  created_at?: string | null;
};

export default function MyPage() {
  const router = useRouter();
  const { user, loading: userLoading } = useCurrentUser({ redirectIfMissing: true });
  const [files, setFiles] = useState<ExtensionFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    if (!token) {
      if (!userLoading) {
        router.push("/");
      }
      setLoading(false);
      return;
    }

    async function load() {
      try {
        setLoading(true);
        setError(null);
        // Explicitly attach the access token so the backend knows who we are.
        const data = await api("/extension-files", {
          method: "GET",
          headers: { Authorization: `Bearer ${token}` },
        });
        const list: ExtensionFile[] = Array.isArray(data) ? data : data?.items ?? [];
        setFiles(list);
      } catch (err: any) {
        setError(err?.message || "확장 파일 기록을 불러오지 못했습니다.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [router, userLoading]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <p className="inline-flex items-center rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-200">
              My Page
            </p>
            <div>
              <h1 className="text-3xl font-bold">마이페이지</h1>
              <p className="mt-2 text-sm text-blue-100">
                내가 만든 확장 파일 기록들을 확인할 수 있는 페이지입니다.
              </p>
            </div>
          </div>

          <button
            onClick={() => router.push("/threads")}
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-white/20"
          >
            ← 스레드 목록으로
          </button>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-5 text-sm text-blue-100 shadow-lg backdrop-blur">
            불러오는 중…
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-6 py-5 text-sm text-red-50 shadow-lg backdrop-blur">
            {error}
          </div>
        ) : files.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-8 text-sm text-blue-100 shadow-lg backdrop-blur">
            아직 저장된 확장 파일 기록이 없습니다.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-lg backdrop-blur">
            <div className="grid grid-cols-3 bg-white/5 px-4 py-3 text-xs font-semibold uppercase tracking-wide text-blue-200">
              <span>파일 이름</span>
              <span>설명</span>
              <span className="text-right">생성일</span>
            </div>
            <div className="divide-y divide-white/10">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="grid grid-cols-3 items-center px-4 py-3 text-sm text-white transition hover:bg-white/10"
                >
                  <span className="font-semibold">{file.name}</span>
                  <span className="text-blue-100">{file.description || "—"}</span>
                  <span className="text-right text-xs text-blue-200">
                    {file.created_at
                      ? new Date(file.created_at).toLocaleString()
                      : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
