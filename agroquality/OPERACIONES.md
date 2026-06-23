# AgroQuality · Operaciones (runbook)

Auditoría e inspección de calidad post-cosecha. Backend FastAPI + frontend
estático, sobre Supabase. **En producción:** https://agroquality.automatizaesto.com (dominio propio; CNAME → agroquality.onrender.com)

## Arquitectura
- `agroquality/app/` — backend FastAPI + frontend (`static/index.html`).
  - `config.py` carga `.env` solo; sin credenciales → **modo DEMO** (RAM), con
    credenciales → **modo SaaS** (Supabase Auth + persistencia).
  - `auth.py` valida el JWT de Supabase (**ES256 vía JWKS**, fallback HS256, `leeway=60`).
  - `db.py` — dos backends (SaaS por PostgREST con service key / demo en RAM).
  - `server.py` — endpoints `/api/*` + sirve el frontend.
- `agroquality/index.html` — landing de marketing (Netlify, sitio estático).
- `agroquality/prototipo.html` — demo localStorage (sin login).
- `agroquality/supabase/migrations/` — esquema (001 base, 002 reporte pro).

## Correr local
```bash
cd agroquality/app
pip install -r requirements.txt
python server.py            # http://localhost:8603
```
Sin `.env` → demo (datos de Marand sembrados, sin login).
Con `.env` (copiar de `.env.example`) → SaaS (pide login).

## Base de datos (Supabase, proyecto automatizaesto-platform)
Aplicar migraciones por **SQL Editor** (el proyecto tiene Network Restrictions
que bloquean Postgres directo; la API REST/Storage NO está restringida):
1. `001_calidad_schema.sql` — tablas aq_inspeccion / aq_pallet / aq_pallet_defecto + vista + RLS.
2. `002_reporte_pro.sql` — columnas/jsonb del reporte pro (fotos, ficha de pallet, defectos, notas, termografía, extras).
Ambas son aditivas e idempotentes. **Regla:** correr la migración ANTES de
desplegar código que use sus campos nuevos.

Bucket de Storage: **`agroquality-fotos`** (privado; la app usa URLs firmadas).

## Deploy (Render)
- `render.yaml` (raíz) + `agroquality/app/Dockerfile`. New → Blueprint → conectar repo.
- Cargar 4 secretos en Environment: `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET` (`AGROQUALITY_BUCKET` ya en el yaml).
- `autoDeploy: true` → cada push a la rama configurada redespliega.
- El runtime NO usa Postgres directo (solo REST/Storage/JWKS) → no le afectan
  las Network Restrictions.

## Usuarios / acceso
- **Mega-admin (vendor):** correos `@automatizaesto.com` (ej. vcardena@). Ven el
  panel de **Solicitudes** y aprueban empresas/dominios nuevos.
- **Empresa cliente:** ej. `mariela@marand.com.pe` (org Marand, rol owner).
- Registro: dominio habilitado → alta directa; dominio nuevo → **pendiente**
  (usuario baneado) hasta que el mega-admin lo aprueba.
- Cambiar contraseña: dentro de la app (sidebar → 🔑 Cambiar contraseña).

## Limitaciones / pendientes conocidos
- **Render free** se duerme ~15 min (1ª visita ~50s). Plan pago o keep-alive si molesta.
- **OAuth (Microsoft/Google):** oculto a propósito (bypasearía la whitelist por
  dominio). Reactivar requiere Azure AD/Google + un Auth Hook que respete el modelo.
- **Recuperar contraseña (email):** requiere SMTP configurado en Supabase.
- **Rama de deploy:** hoy Render sigue la rama del PR; al mergear a `main`,
  cambiar la rama del servicio en Render a `main`.
