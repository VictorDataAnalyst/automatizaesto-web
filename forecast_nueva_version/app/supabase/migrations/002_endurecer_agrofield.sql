-- =====================================================================
-- 002 · Endurecer AgroField — retirar acceso anónimo (auditoría 2026-06-11)
-- Proyecto: automatizaesto-platform (ref zbaaptweszjbqunscldb)
-- =====================================================================
-- ⚠️  DESTRUCTIVO PARA LA APP EN PRODUCCIÓN.
--
-- AgroField hoy funciona SOLO con la anon key (sin login). Aplicar esto
-- ANTES de que AgroField tenga Supabase Auth + login DEJARÁ LA APP SIN
-- ACCESO a sus datos (lecturas/escrituras empezarán a fallar).
--
-- NO ejecutar todavía. Orden correcto:
--   1. Implementar login (Supabase Auth) en AgroField_Mobile.
--   2. Añadir empresa_id / org a las 6 tablas y políticas `authenticated`.
--   3. RECIÉN ENTONCES correr este script para retirar las políticas anon.
--
-- Se incluye aquí para que la migración esté escrita y revisada, no para
-- aplicarla en esta fase. Hay rollback al final.
-- =====================================================================

-- Tablas afectadas: calidad, conteos, fotos, libro, productores, visitas
-- Política actual a retirar: `anon_all` (ALL, qual = true)

do $$
declare t text;
begin
  foreach t in array array['calidad','conteos','fotos','libro','productores','visitas']
  loop
    -- RLS debe quedar ACTIVO (ya lo está); solo se quita la política permisiva
    execute format('drop policy if exists anon_all on public.%I', t);
    -- Defensa en profundidad: revocar privilegios directos del rol anon
    execute format('revoke all on public.%I from anon', t);
  end loop;
end $$;

-- Bucket de fotos: pasar a privado (servir con URLs firmadas desde el backend)
update storage.buckets set public = false where id = 'agrofield-fotos';
drop policy if exists "anon_all_fotos" on storage.objects;  -- nombre real puede variar; verificar

-- A PARTIR DE AQUÍ las 6 tablas y el bucket solo responden al rol
-- `authenticated`. Falta crear esas políticas en la migración 003 (por empresa),
-- que depende del esquema empresa_id de AgroField.

-- =====================================================================
-- ROLLBACK (re-abrir anon — SOLO emergencia, restaura el estado inseguro)
-- =====================================================================
-- do $$
-- declare t text;
-- begin
--   foreach t in array array['calidad','conteos','fotos','libro','productores','visitas']
--   loop
--     execute format('create policy anon_all on public.%I for all to anon using (true) with check (true)', t);
--     execute format('grant all on public.%I to anon', t);
--   end loop;
-- end $$;
-- update storage.buckets set public = true where id = 'agrofield-fotos';
