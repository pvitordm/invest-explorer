with ranked as (
  select
    id,
    row_number() over (
      partition by owner_id, asset_id, collected_at
      order by created_at desc, id desc
    ) as rn
  from public.price_history
)
delete from public.price_history ph
using ranked r
where ph.id = r.id
  and r.rn > 1;

create unique index if not exists uq_price_history_owner_asset_collected
  on public.price_history(owner_id, asset_id, collected_at);
