-- =====================================================================
-- AgroQuality · 003 — Endurecimiento (defensa en profundidad)
-- La vista aq_resumen_inspeccion, por defecto, corre con privilegios del
-- owner (postgres) e IGNORA el RLS de las tablas base. Hoy NO es un riesgo
-- porque la app la consulta solo vía backend con service-role filtrando por
-- org_id en código — pero si en el futuro el frontend la lee con el JWT del
-- usuario, security_invoker garantiza que se aplique el RLS por org.
-- Requiere PostgreSQL 15+ (Supabase ya lo cumple). Idempotente.
-- =====================================================================

alter view aq_resumen_inspeccion set (security_invoker = true);
