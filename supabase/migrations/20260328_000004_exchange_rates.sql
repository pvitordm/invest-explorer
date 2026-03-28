create table if not exists public.exchange_rates (
  id uuid primary key default gen_random_uuid(),
  base_currency text not null,
  quote_currency text not null,
  rate numeric(20, 8) not null,
  source text,
  collected_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (base_currency, quote_currency, collected_at)
);

create index if not exists idx_exchange_rates_pair_collected
  on public.exchange_rates(base_currency, quote_currency, collected_at desc);

alter table public.exchange_rates enable row level security;

drop policy if exists exchange_rates_select_authenticated on public.exchange_rates;
create policy exchange_rates_select_authenticated on public.exchange_rates
for select
using (auth.role() = 'authenticated');
