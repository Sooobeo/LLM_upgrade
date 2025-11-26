"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

type CurrentUser = {
  id: string;
  email?: string | null;
};

type Options = {
  redirectIfMissing?: boolean;
};

export function useCurrentUser(options: Options = {}) {
  const { redirectIfMissing = true } = options;
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    if (!token) {
      setLoading(false);
      if (redirectIfMissing) {
        router.push("/");
      }
      return;
    }

    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await api("/me", { method: "GET" });
        if (cancelled) return;
        setUser({ id: data.id, email: data.email });
      } catch (err: any) {
        if (cancelled) return;
        const message = err?.message || "사용자 정보를 불러오지 못했습니다.";
        setError(message);
        if (redirectIfMissing) {
          router.push("/");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [redirectIfMissing, router]);

  const displayName = useMemo(() => {
    if (!user?.email) return "";
    // Use the local-part (text before '@') so the header shows only the user's id portion.
    return user.email.split("@")[0];
  }, [user]);

  return { user, displayName, loading, error };
}
