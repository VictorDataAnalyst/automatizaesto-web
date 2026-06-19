-- =====================================================================
-- AgroQuality · 001 — Esquema de auditoría de calidad post-cosecha
-- Proyecto Supabase: automatizaesto-platform (mismo que Forecast/AgroField)
-- Multi-tenant por org_id, reutilizando orgs/miembros/mis_orgs() del 001 de Forecast.
-- SEGURO: solo crea tablas NUEVAS (prefijo aq_). Idempotente.
--
-- Modelo jerárquico (igual que QIMA):
--   aq_inspeccion (cabecera del lote)  1──*  aq_pallet  1──*  aq_pallet_defecto
-- El gerente extrae por "período de ingreso" = aq_inspeccion.fecha_frigorifico.
-- =====================================================================

-- ---------- Cabecera de inspección (1 por lote/container) ----------
create table if not exists aq_inspeccion (
  id                uuid primary key default gen_random_uuid(),
  org_id            uuid not null references orgs(id) on delete cascade,
  codigo            text,                       -- INS-2606-0001 (legible)
  -- Identificación del lote
  lote              text not null,
  container         text,
  num_factura       text,
  compania          text,
  exportador        text,
  consignatario     text,
  -- Producto
  producto          text,                       -- Avocados...
  variedad          text,                       -- Hass...
  embalaje          text,                       -- Plastic Box 10Kg
  tipo_producto     text,                       -- CONV | ORG
  -- Logística / destino
  locacion          text,                       -- China, Shanghai
  pais_origen       text,                       -- Peru
  barco             text,
  tipo_carrier      text,                       -- Ocean | Air
  frigorifico       text,                       -- Supafresh DC
  fumigacion        text,
  -- Inspección
  tipo_inspeccion   text,                       -- Normal Inspection...
  inspector         text,
  cajas             int,
  total_pallets     int,
  hora_frigorifico  text,
  -- Fechas (clave del negocio)
  fecha_embalaje    date,
  fecha_arribo      date,
  fecha_frigorifico date,                       -- ★ período de ingreso (filtro del gerente)
  -- Scoring agregado (cacheado al guardar; recalculable desde los pallets)
  score_global      text,                       -- good | fair | poor
  pct_total_prom    numeric(6,2),
  resumen           jsonb,                      -- KPIs/donut precalculados
  estado            text not null default 'borrador', -- borrador | cerrada
  creado_por        uuid references auth.users(id),
  creado_en         timestamptz not null default now(),
  actualizado_en    timestamptz not null default now()
);

-- ---------- Pallets de una inspección ----------
create table if not exists aq_pallet (
  id              uuid primary key default gen_random_uuid(),
  org_id          uuid not null references orgs(id) on delete cascade,
  inspeccion_id   uuid not null references aq_inspeccion(id) on delete cascade,
  codigo          text not null,               -- R-MAR-10-EX08267
  productor       text,                        -- 004-03006-03
  clase           text,                        -- 1
  calibre         int,
  -- Medidas
  temp_prom       numeric(5,2),
  peso_neto_prom  numeric(6,2),
  brix_prom       numeric(5,2),
  cajas_muestra   int,
  tamano_muestra  int,
  -- Scoring
  pct_calidad     numeric(6,2) not null default 0,   -- Suma Defectos Calidad
  pct_condicion   numeric(6,2) not null default 0,   -- Suma Defectos Condición
  pct_total       numeric(6,2) not null default 0,   -- Suma Defectos Totales
  pallet_score    text,                        -- good | fair | poor
  sample_score    text,
  defecto_principal text,                      -- texto resumido (como QIMA)
  fotos           jsonb,                       -- [{tipo, storage_path}] galería pallet/muestra
  creado_en       timestamptz not null default now()
);

-- ---------- Defectos individuales por pallet (detalle fino, opcional) ----------
create table if not exists aq_pallet_defecto (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references orgs(id) on delete cascade,
  pallet_id   uuid not null references aq_pallet(id) on delete cascade,
  categoria   text not null,                   -- calidad | condicion
  nombre      text not null,                   -- Black Spots, Lenticelosis...
  pct         numeric(6,2) not null default 0,
  conteo      int
);

create index if not exists idx_aq_insp_org   on aq_inspeccion(org_id);
create index if not exists idx_aq_insp_frig  on aq_inspeccion(org_id, fecha_frigorifico);
create index if not exists idx_aq_pallet_org on aq_pallet(org_id);
create index if not exists idx_aq_pallet_ins on aq_pallet(inspeccion_id);
create index if not exists idx_aq_def_pallet on aq_pallet_defecto(pallet_id);

-- ---------- RLS: aislado por org (reusa mis_orgs() de Forecast) ----------
alter table aq_inspeccion     enable row level security;
alter table aq_pallet         enable row level security;
alter table aq_pallet_defecto enable row level security;

drop policy if exists "aq_insp de mi org" on aq_inspeccion;
create policy "aq_insp de mi org" on aq_inspeccion for all to authenticated
  using (org_id in (select mis_orgs())) with check (org_id in (select mis_orgs()));

drop policy if exists "aq_pallet de mi org" on aq_pallet;
create policy "aq_pallet de mi org" on aq_pallet for all to authenticated
  using (org_id in (select mis_orgs())) with check (org_id in (select mis_orgs()));

drop policy if exists "aq_def de mi org" on aq_pallet_defecto;
create policy "aq_def de mi org" on aq_pallet_defecto for all to authenticated
  using (org_id in (select mis_orgs())) with check (org_id in (select mis_orgs()));

-- NOTA: sin política para `anon` => el rol anónimo no ve nada (correcto para SaaS).

-- ---------- Vista para el panel del gerente (extracción por período) ----------
create or replace view aq_resumen_inspeccion as
select
  i.id, i.org_id, i.codigo, i.lote, i.container, i.consignatario, i.locacion,
  i.producto, i.variedad, i.inspector, i.barco,
  i.fecha_arribo, i.fecha_frigorifico, i.score_global, i.cajas,
  count(p.id)                              as pallets,
  count(p.id) filter (where p.pallet_score='good') as pallets_good,
  count(p.id) filter (where p.pallet_score='fair') as pallets_fair,
  count(p.id) filter (where p.pallet_score='poor') as pallets_poor,
  round(avg(p.pct_calidad),2)              as pct_calidad_prom,
  round(avg(p.pct_condicion),2)            as pct_condicion_prom,
  round(avg(p.pct_total),2)                as pct_total_prom,
  round(avg(p.temp_prom),1)                as temp_prom
from aq_inspeccion i
left join aq_pallet p on p.inspeccion_id = i.id
group by i.id;
