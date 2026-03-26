import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

let supabaseClient: SupabaseClient | null = null;

export function hasSupabaseConfig(): boolean {
  return Boolean(supabaseUrl && supabaseAnonKey);
}

export function isSupabaseReal(): boolean {
  // Check if this is a REAL Supabase config (not fake/test keys)
  // Fake keys contain "test_anon_key" or URL is the fake invest-explorer one with test key
  if (!supabaseUrl || !supabaseAnonKey) return false;
  if (supabaseAnonKey.includes("test_anon_key")) return false;
  if (supabaseAnonKey.includes("eyJ") && supabaseAnonKey.includes("test")) return false;
  return true;
}

export function getSupabaseClient(): SupabaseClient {
  if (!hasSupabaseConfig()) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY");
  }

  if (supabaseClient) return supabaseClient;

  supabaseClient = createClient(supabaseUrl as string, supabaseAnonKey as string, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true
    }
  });

  return supabaseClient;
}
