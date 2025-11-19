// src/app/login/page.tsx
"use client";

import { useState } from "react";

// ⭐ 여기서 API_BASE_URL 꼭 선언해줘야 함
// .env.local에 NEXT_PUBLIC_API_BASE_URL이 있으면 그거 쓰고,
// 없으면 기본값으로 127.0.0.1:8000 사용
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

console.log("API_BASE_URL =", API_BASE_URL);

export default function LoginPage() {
  const [email, setEmail] = useState("soob@gmail.com");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/login/password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      // 🔴 절대 바로 res.json() 하지 말고, 우선 text/헤더부터 확인
      const contentType = res.headers.get("content-type") || "";
      const text = await res.text();

      console.log(
        "[login] raw response:",
        res.status,
        contentType,
        text.slice(0, 200) // 너무 길면 앞부분만
      );

      let data: any = null;

      if (contentType.includes("application/json")) {
        try {
          data = text ? JSON.parse(text) : null;
        } catch (e) {
          console.error("[login] JSON parse error:", e);
          setError("서버 JSON 파싱 중 오류가 발생했습니다.");
          return;
        }
      } else {
        // 여기로 오면 서버가 HTML 같은 걸 보낸 거라서,
        // SyntaxError 대신 메시지만 띄우고 끝낼 거야.
        setError(
          `서버가 JSON이 아닌 응답을 보냈습니다. (status ${res.status})`
        );
        return;
      }

      if (!res.ok) {
        console.error("[login] Login failed:", data);
        setError(data?.detail?.message || data?.detail || "로그인 실패");
        return;
      }

      const accessToken = data.access_token;
      if (!accessToken) {
        setError("access_token이 응답에 없습니다.");
        return;
      }

      // 일단 간단하게 localStorage에만 저장
      window.localStorage.setItem("access_token", accessToken);

      // 스레드 페이지로 이동
      window.location.href = "/threads";
    } catch (err: any) {
      console.error("[login] 네트워크/기타 오류:", err);
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 border p-6 rounded-lg">
        <h1 className="text-xl font-semibold">로그인</h1>

        <div className="space-y-1">
          <label className="block text-sm">Email</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
          />
        </div>

        <div className="space-y-1">
          <label className="block text-sm">Password</label>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
          />
        </div>

        {error && <p className="text-sm text-red-500 whitespace-pre-wrap">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded bg-black text-white text-sm disabled:opacity-60"
        >
          {loading ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </main>
  );
}
