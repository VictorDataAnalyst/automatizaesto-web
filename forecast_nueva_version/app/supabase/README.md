# Migraciones Supabase — Forecast SaaS (Fase 0/1)

Proyecto: **automatizaesto-platform** · ref `zbaaptweszjbqunscldb`
Aplicación: SQL Editor de Supabase (Dashboard → SQL Editor → New query → pega y Run).

> No se ejecutan desde aquí: el token de Management API fue revocado y, más
> importante, la 002 es destructiva para AgroField en producción. Estas
> migraciones son **revisables y se aplican manualmente**, en el orden de abajo.

## Orden de aplicación

| # | Archivo | ¿Seguro ahora? | Efecto |
|---|---|---|---|
| 001 | `001_saas_schema.sql` | ✅ **Sí** | Crea tablas nuevas del SaaS (orgs, miembros, datasets, corridas) con RLS por tenant. No toca AgroField |
| 002 | `002_endurecer_agrofield.sql` | ⛔ **No todavía** | Retira el acceso anónimo de AgroField. **Rompe la app hasta que tenga login** |

### Aplica 001 cuando quieras
Es aditivo y aislado. Tras correrlo, verifica:
```sql
select tablename, rowsecurity from pg_tables
 where schemaname='public' and tablename in ('orgs','miembros','datasets','corridas');
-- rowsecurity debe ser true en las cuatro
```
Y prueba el trigger creando un usuario de prueba en Auth → debe aparecer su
fila en `orgs` y `miembros`.

### NO apliques 002 hasta cerrar esta secuencia
1. Login (Supabase Auth) en `AgroField_Mobile`.
2. `empresa_id` / org en las 6 tablas + políticas `authenticated` por empresa
   (será la migración 003, depende del esquema empresa_id — ver nota de proyecto
   "Empresa ID scheme").
3. Recién entonces 002, para retirar las políticas anon sin dejar la app ciega.

La 002 trae su propio bloque de **rollback** comentado por si algo sale mal.

## Por qué este orden

La auditoría (2026-06-11) encontró RLS abierto a `anon` en las 6 tablas de
AgroField + bucket público. Cerrarlo es correcto para producción, pero AgroField
depende hoy de ese acceso anónimo. Por eso el SaaS de Forecast **nace bien**
(001, RLS estricto desde el día 0) mientras que AgroField se endurece de forma
**coordinada con su login** (002 + 003), sin downtime sorpresa.
