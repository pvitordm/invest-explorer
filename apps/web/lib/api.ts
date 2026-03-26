import { getSupabaseClient } from "@/lib/supabase";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export type ApiWatchlistItem = {
  id: string;
  notes: string | null;
  created_at: string;
  asset: {
    id: string;
    name: string;
    symbol: string;
    exchange: string;
    currency: string;
    asset_class?: string;
    country_code?: string | null;
  };
  display: string;
};

export type ApiWatchlistResponse = {
  read_only: boolean;
  owner: {
    sub: string;
    role: string;
    email?: string;
  };
  watchlist: {
    id: string;
    name: string;
    is_default: boolean;
  };
  items: ApiWatchlistItem[];
};

export type ApiRefreshResponse = {
  status: string;
  message: string;
  snapshot_id?: string;
  snapshot_asset_count?: number;
};

async function getAccessToken(): Promise<string> {
  try {
    const supabase = getSupabaseClient();
    const { data, error } = await supabase.auth.getSession();
    if (error) throw error;
    const token = data.session?.access_token;
    if (!token) throw new Error("No active Supabase session");
    return token;
  } catch (e) {
    // Dev mode fallback: return a fake token that API will accept in fallback mode
    return "dev-token-" + Date.now();
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiBaseUrl) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }

  const token = await getAccessToken();
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`API ${response.status}: ${body}`);
  }

  return (await response.json()) as T;
}

export async function fetchWatchlist(): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist", { method: "GET" });
}

export async function triggerRefresh(): Promise<ApiRefreshResponse> {
  return apiRequest<ApiRefreshResponse>("/refresh", { method: "POST", body: "{}" });
}
