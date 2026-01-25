"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { auth } from "@/lib/auth";
import { supabase } from "@/lib/supabaseClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token;
      if (token) {
        auth.setSession({ accessToken: token, refreshToken: data.session?.refresh_token || undefined });
        router.replace("/threads");
      }
    });
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { data, error: err } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (err) {
      setError(err.message);
      return;
    }
    const accessToken = data.session?.access_token;
    if (accessToken) {
      auth.setSession({ accessToken, refreshToken: data.session?.refresh_token || undefined });
    }
    router.replace("/threads");
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 px-4">
      {/* Login Card */}
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-white/5 p-8 text-white shadow-2xl backdrop-blur">
        <h1 className="text-2xl font-bold">Log in</h1>
        <p className="mt-1 text-sm text-blue-100">
          Sign in with your Supabase credentials.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleLogin}>
          <div>
            <label className="text-sm font-semibold text-blue-50">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="name@example.com"
            />
          </div>

          <div>
            <label className="text-sm font-semibold text-blue-50">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white focus:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>

      {/* Back to landing (caption) */}
      <button
        onClick={() => router.push("/")}
        className="mt-4 text-xs text-blue-200/70 transition hover:text-white"
      >
        ← Back to landing page
      </button>
    </div>
  );
}