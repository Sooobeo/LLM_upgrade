"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/auth";

type TokenParams = Record<string, string>;

function parseParams(input: string): TokenParams {
  const trimmed = input.startsWith("#") || input.startsWith("?") ? input.substring(1) : input;
  const params = new URLSearchParams(trimmed);
  const out: TokenParams = {};
  params.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

export default function AuthCallbackPage() {
  const router = useRouter();
  const callbackStarted = useRef(false);
  const [message, setMessage] = useState("로그인 세션을 확인하는 중입니다...");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // React Strict Mode runs effects twice in development. A Supabase refresh
    // token is rotating/single-use, so submitting it twice makes the second
    // request fail even though the first request created the session.
    if (callbackStarted.current) return;
    callbackStarted.current = true;

    const hashParams = parseParams(window.location.hash || "");
    const searchParams = parseParams(window.location.search || "");
    const allParams = { ...searchParams, ...hashParams };
    const accessToken = allParams["access_token"];
    const refreshToken = allParams["refresh_token"];
    const oauthError =
      allParams["error_description"] ||
      allParams["error"] ||
      allParams["error_code"];
    window.history.replaceState(null, "", window.location.pathname);

    if (oauthError) {
      setFailed(true);
      setMessage(`Google 로그인에 실패했습니다. ${oauthError}`);
      return;
    }

    if (!accessToken || !refreshToken) {
      setFailed(true);
      setMessage("로그인 정보가 없습니다. 다시 로그인해주세요.");
      return;
    }

    const establishSession = async () => {
      let response: Response | null = null;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        response = await fetch("/api/auth/google-session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          credentials: "include",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (![502, 503].includes(response.status) || attempt === 1) {
          return response;
        }
        await new Promise((resolve) => window.setTimeout(resolve, 800));
      }
      return response!;
    };

    establishSession()
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok || !data?.access_token) {
          const detail = data?.detail;
          const detailMessage =
            typeof detail === "string"
              ? detail
              : detail?.message || "세션 설정에 실패했습니다.";
          throw new Error(detailMessage);
        }
        // Keep the access token in memory for the client-side route change.
        // The rotating refresh token remains in the backend's HttpOnly cookie.
        auth.setToken(data.access_token);
        setMessage("로그인 완료! 스레드로 이동합니다...");
        router.replace("/threads");
      })
      .catch((err) => {
        setFailed(true);
        setMessage(
          `로그인 세션을 만들지 못했습니다. 다시 시도해 주세요. (${err.message})`,
        );
      });
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#0c1424] text-white">
      <div className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-center shadow-lg backdrop-blur">
        {!failed && (
          <span
            aria-hidden="true"
            className="mx-auto mb-3 block h-6 w-6 animate-spin rounded-full border-2 border-blue-200/30 border-t-cyan-300"
          />
        )}
        <p className="text-sm text-blue-100">{message}</p>
        {failed && (
          <button
            type="button"
            onClick={() => router.replace("/")}
            className="mt-4 rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-400"
          >
            로그인 화면으로 돌아가기
          </button>
        )}
      </div>
    </main>
  );
}
