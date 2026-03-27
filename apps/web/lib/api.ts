import { getSupabaseClient } from "@/lib/supabase";

// Use proxy path to avoid CORS issues; Next.js rewrites /api-proxy/* to the real API
const apiBaseUrl = "/api-proxy";

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

export type WatchlistAssetInput = {
  symbol: string;
  exchange: string;
  notes?: string | null;
};

export type ApiRefreshResponse = {
  status: string;
  message: string;
  snapshot_id?: string;
  snapshot_asset_count?: number;
  data?: Record<string, unknown>;
};

async function getAccessToken(): Promise<string> {
  try {
    const supabase = getSupabaseClient();
    const { data, error } = await supabase.auth.getSession();
    if (error) throw error;
    const token = data?.session?.access_token;
    if (token && token.length > 10) {
      return token;
    }
    throw new Error("No active Supabase session");
  } catch (e) {
    // Dev mode fallback: return a fake token that API will accept in fallback mode
    console.warn("Using dev-token fallback", e);
    return "dev-token-" + Date.now();
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
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

export async function addWatchlistItem(input: WatchlistAssetInput): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist/items", {
    method: "POST",
    body: JSON.stringify({
      symbol: input.symbol,
      exchange: input.exchange,
      notes: input.notes ?? null
    })
  });
}

export async function removeWatchlistItem(input: WatchlistAssetInput): Promise<ApiWatchlistResponse> {
  return apiRequest<ApiWatchlistResponse>("/watchlist/items", {
    method: "DELETE",
    body: JSON.stringify({
      symbol: input.symbol,
      exchange: input.exchange
    })
  });
}
