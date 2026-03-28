create table if not exists public.scheduler_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null,
  message text,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_scheduler_runs_started_at_desc
  on public.scheduler_runs(started_at desc);

alter table public.scheduler_runs enable row level security;

drop policy if exists scheduler_runs_select_authenticated on public.scheduler_runs;
create policy scheduler_runs_select_authenticated on public.scheduler_runs
for select
using (auth.role() = 'authenticated');
