-- =====================================================================
-- AgroQuality · 004 — Panel ejecutivo + motor de alertas (Fase 0 del roadmap)
-- Vistas agregadas para el dashboard del gerente y tablas del sistema de
-- alertas por organización. SEGURO: solo objetos nuevos (prefijo aq_).
-- Idempotente. Aplicar por SQL Editor, ANTES de desplegar el código que las use.
-- =====================================================================

-- ---------- 1. Vista: score semanal (curva de tendencia del panel) ----------
create or replace view aq_v_score_semanal
with (security_invoker = true) as
select
  org_id,
  date_trunc('week', coalesce(fecha_frigorifico, creado_en::date))::date as semana,
  count(*)                                   as inspecciones,
  sum(total_pallets)                         as pallets,
  round(avg(pct_total_prom), 2)              as score_promedio,
  count(*) filter (where score_global = 'good') as n_good,
  count(*) filter (where score_global = 'fair') as n_fair,
  count(*) filter (where score_global = 'poor') as n_poor
from aq_inspeccion
where estado = 'cerrada'
group by org_id, 2;

-- ---------- 2. Vista: Pareto de defectos (heatmap / barras del panel) ----------
create or replace view aq_v_pareto_defectos
with (security_invoker = true) as
select
  d.org_id,
  date_trunc('week', coalesce(i.fecha_frigorifico, i.creado_en::date))::date as semana,
  i.frigorifico,
  d.nombre                                   as defecto,
  count(*)                                   as ocurrencias,
  round(avg(d.pct), 2)                       as pct_promedio,
  round(max(d.pct), 2)                       as pct_maximo
from aq_pallet_defecto d
join aq_pallet p on p.id = d.pallet_id
join aq_inspeccion i on i.id = p.inspeccion_id
group by d.org_id, 2, i.frigorifico, d.nombre;

-- ---------- 3. Reglas de alerta por organización ----------
create table if not exists aq_alerta_regla (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references orgs(id) on delete cascade,
  nombre      text not null,                  -- "Defecto crítico sobre umbral"
  tipo        text not null,                  -- defecto_pct | score_poor | sin_actividad
  parametro   jsonb not null default '{}',    -- {"defecto":"pudricion","umbral":3.0}
  canal       text not null default 'app',    -- app | email | whatsapp
  activa      boolean not null default true,
  creado_en   timestamptz not null default now()
);

-- ---------- 4. Alertas disparadas ----------
create table if not exists aq_alerta (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references orgs(id) on delete cascade,
  regla_id       uuid references aq_alerta_regla(id) on delete set null,
  inspeccion_id  uuid references aq_inspeccion(id) on delete cascade,
  pallet_id      uuid references aq_pallet(id) on delete set null,
  severidad      text not null default 'media',   -- critica | media | info
  titulo         text not null,                   -- "PAL-2214 · pudrición 4,1 %"
  detalle        jsonb,                           -- evidencia: valores, umbral, refs
  leida          boolean not null default false,
  notificada_en  timestamptz,                     -- cuándo salió por correo/WhatsApp
  creado_en      timestamptz not null default now()
);
create index if not exists aq_alerta_org_creado on aq_alerta (org_id, creado_en desc);
create index if not exists aq_alerta_org_noleida on aq_alerta (org_id) where not leida;

-- ---------- 5. RLS: aislamiento por organización (patrón del 001) ----------
alter table aq_alerta_regla enable row level security;
alter table aq_alerta enable row level security;

drop policy if exists "aq_regla de mi org" on aq_alerta_regla;
create policy "aq_regla de mi org" on aq_alerta_regla for all to authenticated
  using (org_id in (select mis_orgs())) with check (org_id in (select mis_orgs()));

drop policy if exists "aq_alerta de mi org" on aq_alerta;
create policy "aq_alerta de mi org" on aq_alerta for all to authenticated
  using (org_id in (select mis_orgs())) with check (org_id in (select mis_orgs()));

-- ---------- 6. Reglas por defecto para orgs existentes (solo si no tienen) ----------
insert into aq_alerta_regla (org_id, nombre, tipo, parametro, canal)
select o.id, 'Pallet con score POOR', 'score_poor', '{}', 'app'
from orgs o
where not exists (select 1 from aq_alerta_regla r where r.org_id = o.id and r.tipo = 'score_poor');
