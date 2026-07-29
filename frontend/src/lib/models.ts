const GEMINI_MODEL =
  process.env.NEXT_PUBLIC_GEMINI_MODEL || "gemini-2.5-flash";

export const MODEL_OPTIONS = [
  "gemma3:270m",
  "llama3.1:8b",
  "mistral:7b",
  GEMINI_MODEL,
] as const;
