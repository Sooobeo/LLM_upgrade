"use client";

import { createClient } from "@supabase/supabase-js";

const configuredSupabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const fallbackSupabaseUrl = "https://alrazxpdcagyapidcuyf.supabase.co";

function validSupabaseUrl(value?: string) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname.endsWith(".supabase.co")
      ? url.origin
      : null;
  } catch {
    return null;
  }
}

export const SUPABASE_PROJECT_URL =
  validSupabaseUrl(configuredSupabaseUrl) || fallbackSupabaseUrl;

if (typeof window !== "undefined" && (!configuredSupabaseUrl || !supabaseKey)) {
  console.warn("Supabase env missing: check NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY");
}

export const supabase =
  SUPABASE_PROJECT_URL && supabaseKey
    ? createClient(SUPABASE_PROJECT_URL, supabaseKey, {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
          detectSessionInUrl: false,
        },
      })
    : null;
