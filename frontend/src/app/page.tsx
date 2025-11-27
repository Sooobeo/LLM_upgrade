"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import { auth } from "@/lib/auth";

export default function LandingPage() {
  const [showLogin, setShowLogin] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleGoogleLogin = useCallback(() => {
    const redirectTo = `${window.location.origin}/auth/callback`;
    const base = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;
    const url = `${base}/auth/google/login?redirect_to=${encodeURIComponent(redirectTo)}`;
    window.location.href = url;
  }, []);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const base = process.env.NEXT_PUBLIC_BACKEND_API_BASE_URL;
      const res = await fetch(`${base}/auth/login/password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail;
        // Normalize error to string to avoid rendering objects in React
        const message =
          typeof detail === "string"
            ? detail
            : detail?.message ||
              detail?.error ||
              detail?.msg ||
              data?.msg ||
              data?.error ||
              "로그인에 실패했습니다.";
        setError(message);
        return;
      }
      const accessToken = data?.access_token;
      const refreshToken = data?.refresh_token;
      if (!accessToken) {
        setError("유효한 토큰을 받지 못했습니다.");
        return;
      }
      auth.setSession({ accessToken, refreshToken });
      router.push("/threads");
    } catch (err: any) {
      setError(err?.message || "네트워크 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-[#0c1424] via-[#0d1b33] to-[#0a1022] text-white">
      {/* Landing slide */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-in-out ${
          showLogin ? "-translate-y-full" : "translate-y-0"
        }`}
      >
        <div className="max-w-4xl text-center space-y-6">
          <p className="inline-flex items-center rounded-full bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-200">
            LLM Workspace
          </p>
          <h1 className="text-5xl font-bold md:text-6xl">LLM Upgrade, more clarity</h1>
          <p className="text-lg text-blue-100 md:text-xl">
            Organize conversations and jump into your workspace quickly.
          </p>
          <div className="flex items-center justify-center gap-3 text-sm text-blue-100">
            <span className="rounded-full border border-white/20 px-3 py-1">Fast lookup</span>
            <span className="rounded-full border border-white/20 px-3 py-1">Secure</span>
            <span className="rounded-full border border-white/20 px-3 py-1">Team friendly</span>
          </div>
        </div>

        <button
          aria-label="Start"
          onClick={() => setShowLogin(true)}
          className="absolute bottom-10 inline-flex h-14 w-14 items-center justify-center rounded-full bg-white text-[#0d1b33] shadow-xl ring-2 ring-white/40 transition hover:translate-y-1 hover:bg-blue-50"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="h-6 w-6 animate-bounce"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 9.75 12 17.25 19.5 9.75" />
          </svg>
        </button>
      </div>

      {/* Login slide */}
      <div
        className={`absolute inset-0 flex items-center justify-center px-6 transition-transform duration-700 ease-in-out ${
          showLogin ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="relative w-full max-w-5xl overflow-hidden rounded-3xl border border-white/15 bg-white/5 backdrop-blur-xl">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-cyan-400/10" />
          <div className="relative grid gap-0 md:grid-cols-2">
            <div className="flex flex-col justify-center space-y-6 px-8 py-10 md:px-12 md:py-14">
              <p className="text-sm font-semibold uppercase tracking-[0.25em] text-blue-100">Login</p>
              <h2 className="text-3xl font-bold md:text-4xl">Ready to start?</h2>
              <p className="text-sm leading-6 text-blue-100">
                Sign in with Google or go straight to your workspace. If you need an account, you can sign up.
              </p>
              <div className="flex flex-wrap gap-3 text-xs text-blue-100">
                <span className="rounded-full border border-white/20 px-3 py-1">SSO</span>
                <span className="rounded-full border border-white/20 px-3 py-1">Shared</span>
                <span className="rounded-full border border-white/20 px-3 py-1">Secure</span>
              </div>
            </div>

            <div className="relative bg-white text-slate-900 md:rounded-l-3xl md:rounded-r-none">
              <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-blue-600 via-indigo-500 to-cyan-400" />
              <div className="flex flex-col gap-6 px-8 py-10 md:px-10 md:py-14">
                <div className="space-y-1">
                  <h3 className="text-2xl font-semibold">LLM Upgrade</h3>
                  <p className="text-sm text-slate-600">Jump in with Google or continue to workspace.</p>
                </div>

                <button
                  onClick={handleGoogleLogin}
                  className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  <svg className="h-5 w-5" viewBox="0 0 533.5 544.3" xmlns="http://www.w3.org/2000/svg">
                    <path
                      d="M533.5 278.4c0-17.4-1.5-34.2-4.3-50.4H272v95.3h146.9c-6.3 33.9-25 62.6-53.5 81.8v68.2h86.7c50.8-46.8 80.4-115.8 80.4-194.9z"
                      fill="#4285f4"
                    />
                    <path
                      d="M272 544.3c72.6 0 133.6-24 178.2-65.2l-86.7-68.2c-24.1 16.2-55 25.7-91.5 25.7-70.4 0-130.1-47.5-151.5-111.4H31.4v69.9C75.3 487.7 167.2 544.3 272 544.3z"
                      fill="#34a853"
                    />
                    <path
                      d="M120.5 325.2c-5.6-16.6-8.8-34.2-8.8-52.3s3.2-35.7 8.8-52.3V150.7H31.4C11.3 190.1 0 233.4 0 278c0 44.6 11.3 87.9 31.4 127.3l89.1-70.1z"
                      fill="#fbbc05"
                    />
                    <path
                      d="M272 107.3c39.5 0 75 13.6 103 40.3l77.1-77.1C405.6 24.1 344.6 0 272 0 167.2 0 75.3 56.6 31.4 150.7l89.1 69.9C141.9 154.8 201.6 107.3 272 107.3z"
                      fill="#ea4335"
                    />
                  </svg>
                  Continue with Google
                </button>

                <form className="space-y-3" onSubmit={handlePasswordLogin}>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      placeholder="name@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-slate-700">Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      placeholder="••••••••"
                    />
                  </div>

                  {error && (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-600">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full rounded-xl bg-[#0d1b33] px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:-translate-y-0.5 hover:bg-[#0f223e] disabled:opacity-60"
                  >
                    {loading ? "Logging in..." : "Log in"}
                  </button>
                  <Link
                    href="/signup"
                    className="block w-full text-center text-sm font-semibold text-blue-700 underline underline-offset-4"
                  >
                    Need an account? Sign up
                  </Link>
                </form>
              </div>
              <button
                aria-label="Back to landing"
                onClick={() => setShowLogin(false)}
                className="absolute left-4 top-4 inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:scale-105"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-5 w-5"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
