# AgroQuality · puesta en SaaS (Supabase)

Pasos para pasar AgroQuality de **modo demo** (RAM) a **modo SaaS** (Supabase Auth + persistencia).
Proyecto: **automatizaesto-platform** (el mismo de Forecast y AgroField).

> Requisito previo: las tablas `orgs`, `miembros` y la función `mis_orgs()` ya deben
> existir (las creó la migración `001_saas_schema.sql` de Forecast). AgroQuality las reutiliza.

---

## 1) Aplicar la migración (crea las tablas aq_*)

Supabase Dashboard → **SQL Editor** → New query → pega TODO el contenido de:

    agroquality/supabase/migrations/001_calidad_schema.sql

→ **Run**. Es idempotente (solo crea tablas/políticas nuevas con prefijo `aq_`,
no toca nada de Forecast ni AgroField). Crea:

- `aq_inspeccion` (cabecera del lote)
- `aq_pallet` (pallets, con campo `fotos` jsonb)
- `aq_pallet_defecto` (detalle fino de defectos, opcional)
- vista `aq_resumen_inspeccion` (para el panel del gerente)
- RLS por `org_id` reusando `mis_orgs()`

## 2) Crear el bucket de fotos

Dashboard → **Storage** → **New bucket**:

- Name: **`agroquality-fotos`**
- **Private** (NO público) — la app muestra las fotos con URLs firmadas.

No hace falta agregar políticas de Storage: el backend usa el **service key**
(bypasea RLS) y firma las URLs. El aislamiento por organización lo garantiza el
código (las fotos se guardan bajo el prefijo `{org_id}/...` y se valida al leer).

## 3) Variables de entorno

Copia `agroquality/app/.env.example` a `agroquality/app/.env` y rellena con las MISMAS
credenciales que ya usa Forecast (Dashboard → Settings → API):

    SUPABASE_URL=https://<ref>.supabase.co
    SUPABASE_ANON_KEY=<anon key>
    SUPABASE_SERVICE_KEY=<service_role key>     # secreto — NO lo subas a git
    SUPABASE_JWT_SECRET=<JWT secret>            # Settings → API → JWT Secret
    AGROQUALITY_BUCKET=agroquality-fotos

> `.env` debe estar en `.gitignore` (el service key es secreto). Verifícalo.

## 4) Arrancar en modo SaaS

    cd agroquality/app
    pip install -r requirements.txt
    # carga el .env en tu shell (o usa python-dotenv / el runner que prefieras)
    python server.py
    # http://localhost:8603  → ahora pide login (Supabase Auth)

Con las 4 variables presentes, `config.MODO` pasa a `saas` automáticamente y el
frontend muestra el login. Sin ellas, sigue en demo (sin login, datos sembrados).

## 5) Dar de alta usuarios

Cada usuario que se registre en Supabase Auth recibe su propia `org` automáticamente
(trigger `on_signup` de Forecast). Para que varios usuarios de **Marand** compartan
la misma organización y vean las mismas inspecciones, agrégalos a la misma fila de
`miembros` (mismo `org_id`) — igual que en Forecast/AgroField (ver memoria
`empresa-id-scheme`).

---

## Verificación rápida (ya hecha en demo)

- `GET /api/inspecciones` → lista con pallets anidados.
- `POST /api/inspecciones` → calcula score Good/Fair/Poor en servidor.
- `POST /api/fotos` + `GET /api/fotos/{ref}` → sube y sirve la imagen.
- `GET /api/export.csv` → exporta el período filtrado.
