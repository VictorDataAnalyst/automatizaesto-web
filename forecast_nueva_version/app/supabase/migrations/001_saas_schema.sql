-- =====================================================================
-- 001 · Esquema SaaS multi-tenant para Forecast
-- Proyecto: automatizaesto-platform (ref zbaaptweszjbqunscldb)
-- SEGURO de aplicar: crea tablas NUEVAS, no toca nada de AgroField.
-- Idempotente: se puede correr varias veces sin romper.
-- =====================================================================

-- ---------- Tablas ----------
create table if not exists orgs (
  id        uuid primary key default gen_random_uuid(),
  nombre    text not null,
  plan      text not null default 'free',      -- free | pro | business
  creado_en timestamptz not null default now()
);

create table if not exists miembros (
  user_id uuid not null references auth.users(id) on delete cascade,
  org_id  uuid not null references orgs(id) on delete cascade,
  rol     text not null default 'analista',     -- owner | analista | viewer
  primary key (user_id, org_id)
);

create table if not exists datasets (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  nombre       text not null,
  storage_path text not null,
  filas        int,
  columnas     jsonb,
  rubro        text,
  creado_por   uuid references auth.users(id),
  creado_en    timestamptz not null default now()
);

create table if not exists corridas (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references orgs(id) on delete cascade,
  dataset_id   uuid not null references datasets(id) on delete cascade,
  estado       text not null default 'encolada', -- encolada|procesando|lista|error
  config       jsonb,
  informe      jsonb,
  error_msg    text,
  creado_en    timestamptz not null default now(),
  terminado_en timestamptz
);

create index if not exists idx_miembros_user on miembros(user_id);
create index if not exists idx_datasets_org  on datasets(org_id);
create index if not exists idx_corridas_org  on corridas(org_id);
create index if not exists idx_corridas_ds   on corridas(dataset_id);

-- ---------- RLS: cada usuario solo ve su(s) org(s) ----------
alter table orgs     enable row level security;
alter table miembros enable row level security;
alter table datasets enable row level security;
alter table corridas enable row level security;

-- Helper: orgs del usuario autenticado
create or replace function mis_orgs()
returns setof uuid language sql stable security definer set search_path = public as $$
  select org_id from miembros where user_id = auth.uid()
$$;

-- orgs: ver/editar solo las propias
drop policy if exists "orgs propias" on orgs;
create policy "orgs propias" on orgs
  for all to authenticated
  using (id in (select mis_orgs()))
  with check (id in (select mis_orgs()));

-- miembros: ver la membresía de mis orgs
drop policy if exists "miembros de mi org" on miembros;
create policy "miembros de mi org" on miembros
  for all to authenticated
  using (org_id in (select mis_orgs()))
  with check (org_id in (select mis_orgs()));

-- datasets: aislados por org
drop policy if exists "datasets de mi org" on datasets;
create policy "datasets de mi org" on datasets
  for all to authenticated
  using (org_id in (select mis_orgs()))
  with check (org_id in (select mis_orgs()));

-- corridas: aisladas por org
drop policy if exists "corridas de mi org" on corridas;
create policy "corridas de mi org" on corridas
  for all to authenticated
  using (org_id in (select mis_orgs()))
  with check (org_id in (select mis_orgs()));

-- NOTA: NO se crea ninguna política para el rol `anon`.
-- Sin política anon + RLS activo = el rol anónimo no ve nada. Correcto para SaaS.

-- ---------- Alta automática de org al registrarse ----------
create or replace function on_signup()
returns trigger language plpgsql security definer set search_path = public as $$
declare new_org uuid;
begin
  insert into orgs(nombre) values (coalesce(new.email, 'Mi empresa'))
    returning id into new_org;
  insert into miembros(user_id, org_id, rol) values (new.id, new_org, 'owner');
  return new;
end; $$;

drop trigger if exists trg_signup on auth.users;
create trigger trg_signup after insert on auth.users
  for each row execute function on_signup();
