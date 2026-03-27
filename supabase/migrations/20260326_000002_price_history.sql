create table if not exists public.price_history (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  asset_id uuid not null references public.assets(id) on delete restrict,
  snapshot_id uuid references public.snapshots(id) on delete set null,
  price numeric(20, 8),
  valuation_brl numeric(20, 8),
  currency text not null,
  fx_to_brl numeric(20, 8),
  data_quality text,
  collected_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_price_history_owner_collected
  on public.price_history(owner_id, collected_at desc);

create index if not exists idx_price_history_asset_collected
  on public.price_history(asset_id, collected_at desc);

create index if not exists idx_price_history_snapshot
  on public.price_history(snapshot_id);

alter table public.price_history enable row level security;

drop policy if exists price_history_select_own on public.price_history;
create policy price_history_select_own on public.price_history
for select
using (owner_id = auth.uid());

drop policy if exists price_history_insert_own on public.price_history;
create policy price_history_insert_own on public.price_history
for insert
with check (owner_id = auth.uid());