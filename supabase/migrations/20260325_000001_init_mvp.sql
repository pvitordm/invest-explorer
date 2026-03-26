create extension if not exists pgcrypto;

create table if not exists public.assets (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  symbol text not null,
  exchange text not null,
  currency text not null,
  asset_class text not null,
  country_code text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (symbol, exchange)
);

create table if not exists public.watchlists (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  name text not null default 'Default',
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, name)
);

create table if not exists public.watchlist_items (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references public.watchlists(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete restrict,
  notes text,
  created_at timestamptz not null default now(),
  unique (watchlist_id, asset_id)
);

create table if not exists public.portfolio_positions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  asset_id uuid not null references public.assets(id) on delete restrict,
  quantity numeric(20, 8) not null check (quantity > 0),
  avg_cost numeric(20, 8),
  avg_cost_currency text not null default 'BRL',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, asset_id)
);

create table if not exists public.snapshots (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  snapshot_type text not null default 'manual_refresh',
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_assets_exchange_symbol on public.assets(exchange, symbol);
create index if not exists idx_watchlists_owner on public.watchlists(owner_id);
create index if not exists idx_watchlist_items_watchlist on public.watchlist_items(watchlist_id);
create index if not exists idx_positions_owner on public.portfolio_positions(owner_id);
create index if not exists idx_snapshots_owner_created on public.snapshots(owner_id, created_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_assets_set_updated_at on public.assets;
create trigger trg_assets_set_updated_at
before update on public.assets
for each row
execute procedure public.set_updated_at();

drop trigger if exists trg_watchlists_set_updated_at on public.watchlists;
create trigger trg_watchlists_set_updated_at
before update on public.watchlists
for each row
execute procedure public.set_updated_at();

drop trigger if exists trg_positions_set_updated_at on public.portfolio_positions;
create trigger trg_positions_set_updated_at
before update on public.portfolio_positions
for each row
execute procedure public.set_updated_at();

alter table public.assets enable row level security;
alter table public.watchlists enable row level security;
alter table public.watchlist_items enable row level security;
alter table public.portfolio_positions enable row level security;
alter table public.snapshots enable row level security;

drop policy if exists assets_select_authenticated on public.assets;
create policy assets_select_authenticated on public.assets
for select
using (auth.role() = 'authenticated');

drop policy if exists watchlists_select_own on public.watchlists;
create policy watchlists_select_own on public.watchlists
for select
using (owner_id = auth.uid());

drop policy if exists watchlists_insert_own on public.watchlists;
create policy watchlists_insert_own on public.watchlists
for insert
with check (owner_id = auth.uid());

drop policy if exists watchlists_update_own on public.watchlists;
create policy watchlists_update_own on public.watchlists
for update
using (owner_id = auth.uid())
with check (owner_id = auth.uid());

drop policy if exists watchlists_delete_own on public.watchlists;
create policy watchlists_delete_own on public.watchlists
for delete
using (owner_id = auth.uid());

drop policy if exists watchlist_items_select_own on public.watchlist_items;
create policy watchlist_items_select_own on public.watchlist_items
for select
using (
  exists (
    select 1
    from public.watchlists w
    where w.id = watchlist_items.watchlist_id
      and w.owner_id = auth.uid()
  )
);

drop policy if exists watchlist_items_insert_own on public.watchlist_items;
create policy watchlist_items_insert_own on public.watchlist_items
for insert
with check (
  exists (
    select 1
    from public.watchlists w
    where w.id = watchlist_items.watchlist_id
      and w.owner_id = auth.uid()
  )
);

drop policy if exists watchlist_items_delete_own on public.watchlist_items;
create policy watchlist_items_delete_own on public.watchlist_items
for delete
using (
  exists (
    select 1
    from public.watchlists w
    where w.id = watchlist_items.watchlist_id
      and w.owner_id = auth.uid()
  )
);

drop policy if exists portfolio_positions_select_own on public.portfolio_positions;
create policy portfolio_positions_select_own on public.portfolio_positions
for select
using (owner_id = auth.uid());

drop policy if exists portfolio_positions_insert_own on public.portfolio_positions;
create policy portfolio_positions_insert_own on public.portfolio_positions
for insert
with check (owner_id = auth.uid());

drop policy if exists portfolio_positions_update_own on public.portfolio_positions;
create policy portfolio_positions_update_own on public.portfolio_positions
for update
using (owner_id = auth.uid())
with check (owner_id = auth.uid());

drop policy if exists portfolio_positions_delete_own on public.portfolio_positions;
create policy portfolio_positions_delete_own on public.portfolio_positions
for delete
using (owner_id = auth.uid());

drop policy if exists snapshots_select_own on public.snapshots;
create policy snapshots_select_own on public.snapshots
for select
using (owner_id = auth.uid());

drop policy if exists snapshots_insert_own on public.snapshots;
create policy snapshots_insert_own on public.snapshots
for insert
with check (owner_id = auth.uid());

insert into public.assets (name, symbol, exchange, currency, asset_class, country_code)
values
  ('Petrobras PN', 'PETR4', 'B3', 'BRL', 'equity', 'BR'),
  ('Vale ON', 'VALE3', 'B3', 'BRL', 'equity', 'BR'),
  ('Itaú Unibanco PN', 'ITUB4', 'B3', 'BRL', 'equity', 'BR'),
  ('WEG ON', 'WEGE3', 'B3', 'BRL', 'equity', 'BR'),
  ('Apple Inc.', 'AAPL', 'NASDAQ', 'USD', 'equity', 'US'),
  ('Microsoft Corp.', 'MSFT', 'NASDAQ', 'USD', 'equity', 'US'),
  ('NVIDIA Corp.', 'NVDA', 'NASDAQ', 'USD', 'equity', 'US'),
  ('Amazon.com Inc.', 'AMZN', 'NASDAQ', 'USD', 'equity', 'US'),
  ('Alphabet Inc. C', 'GOOG', 'NASDAQ', 'USD', 'equity', 'US'),
  ('Tesla Inc.', 'TSLA', 'NASDAQ', 'USD', 'equity', 'US'),
  ('Toyota Motor', '7203', 'TSE', 'JPY', 'equity', 'JP'),
  ('Sony Group', '6758', 'TSE', 'JPY', 'equity', 'JP'),
  ('Mitsubishi UFJ', '8306', 'TSE', 'JPY', 'equity', 'JP'),
  ('Keyence', '6861', 'TSE', 'JPY', 'equity', 'JP'),
  ('Nintendo', '7974', 'TSE', 'JPY', 'equity', 'JP'),
  ('SoftBank Group', '9984', 'TSE', 'JPY', 'equity', 'JP'),
  ('Bitcoin', 'BTC', 'CRYPTO', 'USD', 'crypto', null),
  ('Ethereum', 'ETH', 'CRYPTO', 'USD', 'crypto', null),
  ('Solana', 'SOL', 'CRYPTO', 'USD', 'crypto', null),
  ('BNB', 'BNB', 'CRYPTO', 'USD', 'crypto', null)
on conflict (symbol, exchange) do update
set
  name = excluded.name,
  currency = excluded.currency,
  asset_class = excluded.asset_class,
  country_code = excluded.country_code,
  is_active = true,
  updated_at = now();
