// Shared HTTP client for the three FamilyVault services.
//
// - Attaches the signed-in user's Supabase access token, from cookies in
//   Server Components and from the browser session in Client Components.
//   The backends derive clan, household and role from that token, so a
//   request without it only works against a local DEBUG backend.
// - Unwraps the Core Backend's { success, message, data } envelope.
// - Times out instead of hanging the page when a service is asleep
//   (free-tier hosts cold-start), so callers can fall back to mock data.

export const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "";
export const GRAPH_URL = process.env.NEXT_PUBLIC_GRAPH_API_URL ?? "";
export const BIOMETRICS_URL = process.env.NEXT_PUBLIC_BIOMETRICS_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

// Server Components read the session from request cookies, which needs
// next/headers and so can never be imported here (this module is also bundled
// for the browser). lib/supabase/server-token.ts registers that reader instead.
let serverTokenProvider: (() => Promise<string>) | null = null;

export function registerServerTokenProvider(provider: () => Promise<string>) {
  serverTokenProvider = provider;
}

export async function getAccessToken(): Promise<string> {
  try {
    if (typeof window === "undefined") {
      return serverTokenProvider ? await serverTokenProvider() : "";
    }
    const { createClient } = await import("./supabase/client");
    const { data } = await createClient().auth.getSession();
    return data.session?.access_token ?? "";
  } catch {
    // No Supabase project configured (local demo) or outside a request scope.
    return "";
  }
}

/** The signed-in user's id (= users.id = Neo4j Person.id), or "" for demo visitors. */
export async function getSessionUserId(): Promise<string> {
  try {
    const { createClient } = await import("./supabase/client");
    const { data } = await createClient().auth.getSession();
    return data.session?.user.id ?? "";
  } catch {
    return "";
  }
}

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  timeoutMs?: number;
};

async function request(baseUrl: string, path: string, options: RequestOptions = {}): Promise<Response> {
  if (!baseUrl) throw new ApiError("Service URL is not configured", 0);
  const { body, timeoutMs = 8000, headers, ...rest } = options;
  const token = await getAccessToken();
  return fetch(`${baseUrl}${path}`, {
    cache: "no-store",
    ...rest,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
}

async function errorFrom(res: Response): Promise<ApiError> {
  const json = await res.json().catch(() => ({}));
  const detail = json.detail ?? json.message ?? `Request failed (${res.status})`;
  return new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
}

/** Core Backend call; resolves to the envelope's `data`. */
export async function backendFetch<T>(path: string, options?: RequestOptions): Promise<T> {
  const res = await request(BACKEND_URL, path, options);
  if (!res.ok) throw await errorFrom(res);
  const json = await res.json();
  return (json && typeof json === "object" && "data" in json ? json.data : json) as T;
}

/** Graph service call; its responses are not enveloped. */
export async function graphFetch<T>(path: string, options?: RequestOptions): Promise<T> {
  const res = await request(GRAPH_URL, path, options);
  if (!res.ok) throw await errorFrom(res);
  return (await res.json()) as T;
}

/**
 * Seeded demo media lives in the frontend's public/ folder ("demo/..." keys);
 * everything else is served by the biometrics service's media route.
 */
export function mediaUrl(storageKey: string): string {
  if (!storageKey) return "";
  if (/^https?:\/\//.test(storageKey)) return storageKey;
  if (storageKey.startsWith("demo/")) return `/${storageKey.slice("demo/".length)}`;
  if (!BIOMETRICS_URL) return "";
  return `${BIOMETRICS_URL}/api/v1/biometrics/media/${storageKey.split("/").pop()}`;
}
