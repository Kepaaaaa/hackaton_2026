-- KBC Fit personas: one row per demo customer of the synthetic bank database.
-- `record` holds the JSON exported by datasets/export_personas.py; the app builds each persona from it.
-- 100% synthetic data. The site reads it server-side with the publishable key: read-only, no writes.

create table public.personas (
  id text primary key check (id in ('lucas', 'thomas', 'monique', 'claire')),
  customer_id text not null unique,
  as_of date not null,
  record jsonb not null,
  updated_at timestamptz not null default now()
);

comment on table public.personas is 'KBC Fit demo customers (synthetic). Read-only through the Data API.';

alter table public.personas enable row level security;

-- Read-only for the Data API roles. Writes only through the SQL editor or the service role.
revoke all on table public.personas from anon, authenticated;
grant select on table public.personas to anon, authenticated;
grant select, insert, update, delete on table public.personas to service_role;

create policy "Demo personas are readable by everyone"
  on public.personas
  for select
  to anon, authenticated
  using (true);
