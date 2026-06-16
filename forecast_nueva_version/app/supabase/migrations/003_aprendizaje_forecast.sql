-- =====================================================================
-- 003 · Memoria del usuario para Forecast
-- Proyecto: automatizaesto-platform (ref zbaaptweszjbqunscldb)
-- SEGURO de aplicar: crea tablas NUEVAS, no toca AgroField ni el 001.
-- Idempotente. Depende de 001 (orgs, miembros, mis_orgs()).
-- =====================================================================

-- ---------- Perfil aprendido por org (1:1 con orgs) ----------
-- Acumula entre corridas: preferencias, rubro, series, calidad típica
-- y hallazgos recurrentes. Lo escribe la capa aprendizaje.py.
create table if not exists perfil_org (
  org_id        uuid primary key references orgs(id) on delete cascade,
  perfil        jsonb not null default '{}'::jsonb,
  actualizado_en timestamptz not null default now()
);

-- ---------- Insights que el usuario marcó como suyos ----------
create table if not exists insights_guardados (
  id         uuid primary key default gen_random_uuid(),
  org_id     uuid not null references orgs(id) on delete cascade,
  corrida_id uuid references corridas(id) on delete set null,
  insight    jsonb not null,                 -- el insight tal cual (icono, titulo, resumen, detalle…)
  nota       text,                            -- comentario opcional del usuario
  creado_por uuid references auth.users(id),
  creado_en  timestamptz not null default now()
);

create index if not exists idx_guardados_org on insights_guardados(org_id);

-- ---------- RLS: cada usuario solo ve lo de su(s) org(s) ----------
alter table perfil_org         enable row level security;
alter table insights_guardados enable row level security;

drop policy if exists "perfil de mi org" on perfil_org;
create policy "perfil de mi org" on perfil_org
  for all to authenticated
  using (org_id in (select mis_orgs()))
  with check (org_id in (select mis_orgs()));

drop policy if exists "guardados de mi org" on insights_guardados;
create policy "guardados de mi org" on insights_guardados
  for all to authenticated
  using (org_id in (select mis_orgs()))
  with check (org_id in (select mis_orgs()));

-- NOTA: igual que el 001, NO se crea política para `anon`. RLS activo
-- sin política anon = el rol anónimo no ve nada. Correcto para SaaS.
