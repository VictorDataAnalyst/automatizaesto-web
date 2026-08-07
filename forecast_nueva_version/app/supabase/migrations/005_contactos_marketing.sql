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
