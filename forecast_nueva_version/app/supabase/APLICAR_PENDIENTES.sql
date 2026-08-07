-- =====================================================================
-- APLICAR EN: Supabase -> SQL Editor -> New query -> pegar todo -> Run
-- Reune las migraciones 003, 004 y 005 (en orden).
-- Idempotente: se puede correr varias veces sin romper nada.
-- NO incluye 002_endurecer_agrofield.sql (dejaria AgroField sin datos).
-- =====================================================================


-- ─────────────────────────────────────────────────────────────────
-- 003_aprendizaje_forecast.sql
-- ─────────────────────────────────────────────────────────────────
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


-- ─────────────────────────────────────────────────────────────────
-- 004_eventos_uso.sql
-- ─────────────────────────────────────────────────────────────────
-- =====================================================================
-- 004 · Eventos de uso — para medir usabilidad durante la etapa gratuita.
-- Responde: ¿vuelve?, ¿qué secciones usa?, ¿dónde abandona?
-- (El "¿vuelve?" ya vivía en `corridas`; esto agrega la interacción fina.)
-- Idempotente.
-- =====================================================================

create table if not exists eventos (
  id        bigserial primary key,
  org_id    uuid not null references orgs(id) on delete cascade,
  tipo      text not null,
  meta      jsonb,
  creado_en timestamptz not null default now()
);

create index if not exists idx_eventos_org_fecha on eventos(org_id, creado_en desc);
create index if not exists idx_eventos_tipo      on eventos(tipo, creado_en desc);

alter table eventos enable row level security;

-- Solo lectura de los eventos de mi propia org (el backend escribe con service key).
-- `to authenticated` explícito, igual que el resto de políticas: sin eso la
-- política también aplica a `anon` y la seguridad depende de que auth.uid()
-- sea NULL. Funciona, pero es mejor cerrar por rol que por efecto secundario.
drop policy if exists "eventos de mi org" on eventos;
create policy "eventos de mi org" on eventos
  for select to authenticated
  using (org_id in (select mis_orgs()));


-- ─────────────────────────────────────────────────────────────────
-- 005_contactos_marketing.sql
-- ─────────────────────────────────────────────────────────────────
-- =====================================================================
-- 005 · Lista de contactos para comunicaciones comerciales.
-- VISTA, no tabla: el dato ya vive en perfil_org.identidad — duplicarlo
-- solo crea copias que se desincronizan y correos a quien ya se dio de baja.
--
-- Solo aparecen quienes dieron consentimiento EXPLÍCITO (Ley 29733).
-- `consentimiento_en` es la prueba de cuándo lo dieron: guárdala.
-- =====================================================================

create or replace view contactos_marketing as
select
  p.org_id,
  o.nombre                                        as organizacion,
  p.perfil->'identidad'->>'email'                 as email,
  p.perfil->'identidad'->>'nombre'                as nombre,
  p.perfil->'identidad'->>'negocio'               as negocio,
  (p.perfil->'identidad'->>'consentimiento_en')::timestamptz as consentimiento_en,
  (p.perfil->>'n_corridas')::int                  as analisis_hechos,
  p.actualizado_en
from perfil_org p
join orgs o on o.id = p.org_id
where (p.perfil->'identidad'->>'acepta_promos')::boolean is true
  and p.perfil->'identidad'->>'email' is not null;

comment on view contactos_marketing is
  'Solo contactos con consentimiento comercial explícito. No enviar a nadie fuera de esta vista.';

-- CRÍTICO: una vista NO aplica el RLS de las tablas que consulta — corre con
-- los permisos de su dueño. Y Supabase concede acceso a anon/authenticated por
-- defecto. Sin estos revoke, cualquier cliente con sesión iniciada podría leer
-- los correos de TODOS los demás clientes.
-- Esta lista se consulta solo con el service key (backend / dashboard).
revoke all on contactos_marketing from anon;
revoke all on contactos_marketing from authenticated;
revoke all on contactos_marketing from public;

