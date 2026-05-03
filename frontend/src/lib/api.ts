const RAW_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
export const API_BASE = RAW_BASE.replace(/\/$/, "");

const TOKEN_KEY = "cb_token";

export const tokenStore = {
  get: () => (typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY)),
  set: (t: string) => window.localStorage.setItem(TOKEN_KEY, t),
  clear: () => window.localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type Options = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | undefined>;
  auth?: boolean;
};

export async function api<T = unknown>(path: string, opts: Options = {}): Promise<T> {
  const { method = "GET", body, formData, query, auth = true } = opts;

  let url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
  if (query) {
    const sp = new URLSearchParams();
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null) sp.set(k, String(v));
    });
    const qs = sp.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (auth) {
    const t = tokenStore.get();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  let payload: BodyInit | undefined;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(url, { method, headers, body: payload });

  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      try {
        msg = (await res.text()) || msg;
      } catch {
        /* ignore */
      }
    }
    throw new ApiError(msg, res.status);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

// ---- Domain types ----
export type User = { id: number; email: string; full_name?: string | null };

export type SkillCandidate = {
  display_name: string;
  category: "language" | "framework" | "database" | "tool" | "cloud" | "soft" | "other" | string;
  confidence?: number;
};

export type UserSkill = {
  id: number;
  name: string;
  display_name?: string;
  category: string;
  level?: "beginner" | "intermediate" | "advanced" | null;
};

export type GapItem = {
  name: string;
  category: string;
  frequency: number;
  coverage: number;
  weight: number;
};

export type GapResponse = {
  target_role: string;
  jobs_analyzed: number;
  have: GapItem[];
  missing: GapItem[];
  market_top: GapItem[];
};

export type RoadmapNode = {
  id: string;
  title: string;
  skill: string;
  level: "beginner" | "intermediate" | "advanced";
  estimated_hours: number;
  resource_url?: string;
  resource_title?: string;
  description?: string;
};

export type RoadmapEdge = { from: string; to: string };

export type RoadmapResponse = {
  target_role: string;
  nodes: RoadmapNode[];
  edges: RoadmapEdge[];
};