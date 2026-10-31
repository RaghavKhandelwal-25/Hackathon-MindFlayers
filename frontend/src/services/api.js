const BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000/api" : "");
if (!BASE) throw new Error("VITE_API_URL is missing");

// const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
export const USE_MOCK = false;
// Real backend endpoints for profile, goals, budget analysis, and dashboard
export const USE_NON_CHAT_MOCK = false;

export async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok)
    throw new Error(
      (await res.text().catch(() => "")) || `Request failed (${res.status})`,
    );
  return res.status === 204 ? null : res.json();
}
const wait = (ms = 600) => new Promise((r) => setTimeout(r, ms));
// Temporary in-memory mock store. Delete when the backend is ready.
export const mock = { profile: null, goals: [], wait };
