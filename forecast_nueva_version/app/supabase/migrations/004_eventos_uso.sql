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
