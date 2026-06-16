# Forecast — Arquitectura SaaS

Plan para convertir la app actual (demo de un usuario, estado en RAM) en un
SaaS multi-tenant. Aterrizado en los activos existentes: el motor validado en
`files/`, el frontend propio en `app/static/`, y el proyecto **Supabase
automatizaesto-platform** ya configurado.

> Estado hoy: `server.py` guarda todo en `SESIONES = {}` (RAM), sin login,
> forecast síncrono (~8 s bloqueando). Funciona para demos; no sobrevive a dos
> clientes a la vez. El **motor** (`app_forecast_universal.py`) y la **lógica de
> informe** (`informe.py`) se reutilizan tal cual — no se reescriben.

---

## 0. Principio rector

**No reescribir el motor. Envolverlo.** Todo lo de abajo es infraestructura
alrededor de `entrenar_y_competir()` y `generar_informe()`, que ya están
probados contra datos reales (Ubycall, Marand). El SaaS es el envoltorio
comercial; el cerebro ya existe.

---

## 1. Fases (orden de ejecución)

| Fase | Entregable | Por qué en este orden |
|---|---|---|
| **0 · Seguridad** | Cerrar RLS de Supabase (auditoría pendiente) | Antes de un solo dato real de cliente |
| **1 · MVP cerrado** | Auth + persistencia + RLS por tenant + host real | Ya es un "SaaS privado" para 2-3 pilotos |
| **2 · Escala** | Cola async + límites por plan | Cuando haya concurrencia real |
| **3 · Negocio** | Billing + planes self-service | Solo cuando el producto retenga |

No saltar fases. Cobrar (fase 3) antes de retener es prematuro.

---

## 2. Modelo de datos (Supabase Postgres)

Multi-tenancy por `org_id` en cada tabla, con RLS que filtra por la org del
usuario autenticado. Esquema mínimo:

```sql
-- Organizaciones (tenant)
create table orgs (
  id          uuid primary key default gen_random_uuid(),
  nombre      text not null,
  plan        text not null default 'free',   -- free | pro | business
  creado_en   timestamptz default now()
);

-- Vínculo usuario <-> org (un usuario puede estar en varias orgs)
create table miembros (
  user_id   uuid references auth.users(id) on delete cascade,
  org_id    uuid references orgs(id) on delete cascade,
  rol       text not null default 'analista', -- owner | analista | viewer
  primary key (user_id, org_id)
);

-- Datasets subidos (el archivo vive en Storage; aquí va el metadato)
create table datasets (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid references orgs(id) on delete cascade,
  nombre       text not null,
  storage_path text not null,              -- ruta en el bucket privado
  filas        int,
  columnas     jsonb,                       -- mapeo detectado (fecha/valor/serie)
  rubro        text,
  creado_por   uuid references auth.users(id),
  creado_en    timestamptz default now()
);

-- Corridas de forecast (una por ejecución)
create table corridas (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid references orgs(id) on delete cascade,
  dataset_id   uuid references datasets(id) on delete cascade,
  estado       text not null default 'encolada', -- encolada|procesando|lista|error
  config       jsonb,                       -- rol, pais, horizonte, unidad
  informe      jsonb,                       -- salida de generar_informe() (cacheada)
  error_msg    text,
  creado_en    timestamptz default now(),
  terminado_en timestamptz
);
```

**Por qué `informe` como `jsonb`:** `generar_informe()` ya devuelve un dict
JSON-listo. Se guarda tal cual → el historial se sirve sin recomputar.

### RLS (el corazón del aislamiento)

```sql
alter table orgs      enable row level security;
alter table datasets  enable row level security;
alter table corridas  enable row level security;

-- Un usuario solo ve filas de orgs a las que pertenece
create policy "datasets de mi org" on datasets
  for all using (
    org_id in (select org_id from miembros where user_id = auth.uid())
  );
-- (misma política para corridas; orgs se filtra por miembros)
```

> **Fase 0 obligatoria:** la auditoría marcó *RLS abierto a anon en todo + bucket
> público*. Eso es exactamente lo contrario de lo que pide la tabla de arriba.
> Cerrar eso es el prerrequisito #1. Ver [[supabase-security-audit]].

---

## 3. Autenticación

**Supabase Auth** (ya disponible en el proyecto). Flujo:

1. Frontend usa `@supabase/supabase-js` → login con email/contraseña o magic link.
2. Supabase emite un **JWT**; el frontend lo manda en `Authorization: Bearer`.
3. FastAPI valida el JWT (clave pública del proyecto) y extrae `user_id`.
4. Toda query a Postgres pasa por RLS → el aislamiento es automático, no depende
   de que el backend "se acuerde" de filtrar.

Al registrarse, un trigger crea una `org` y un `miembro` con rol `owner`.

```sql
-- Trigger: cada usuario nuevo obtiene su org
create function on_signup() returns trigger as $$
declare new_org uuid;
begin
  insert into orgs(nombre) values (new.email) returning id into new_org;
  insert into miembros(user_id, org_id, rol) values (new.id, new_org, 'owner');
  return new;
end; $$ language plpgsql security definer;
create trigger trg_signup after insert on auth.users
  for each row execute function on_signup();
```

---

## 4. Persistencia y archivos

- **Archivos subidos** → bucket **privado** de Supabase Storage, ruta
  `org_id/dataset_id.xlsx`. Nunca público (regresión de la auditoría).
- **Lectura** → el backend baja el archivo del bucket por su `storage_path`
  cuando hay que (re)entrenar; no se vuelve a subir.
- **Reemplazo del `SESIONES` en RAM** → el `token` efímero actual se sustituye
  por `dataset_id` / `corrida_id` persistentes. Esto elimina el punto más frágil
  del código actual.

---

## 5. Procesamiento asíncrono

El forecast tarda ~8 s y hoy bloquea el request. En SaaS:

```
POST /api/corridas        → crea corrida (estado=encolada), encola job, responde 202 + corrida_id
   worker                 → toma el job: estado=procesando → entrena → guarda informe → estado=lista
GET  /api/corridas/{id}   → el frontend hace polling (o Realtime de Supabase) hasta estado=lista
```

- **Cola:** RQ (Redis) o Celery. Para empezar, incluso `BackgroundTasks` de
  FastAPI + un flag en la tabla sirve, pero no escala más allá de un proceso.
- **Workers separados del web** → un forecast pesado no tumba la API.
- **Supabase Realtime** puede empujar el cambio de estado al frontend y evitar
  el polling.
- **Caché:** la corrida guarda su `informe` jsonb; cambiar de rol en el informe
  re-llama `generar_informe()` sobre resultados ya entrenados (rápido, como hoy),
  sin re-entrenar.

---

## 6. Planes y límites

| | Free | Pro | Business |
|---|---|---|---|
| Fuentes por análisis | 1 | 3 | Ilimitadas |
| Filas por dataset | 5 000 | 100 000 | 1M+ |
| Historial de corridas | 7 días | 1 año | Ilimitado |
| Horizonte máximo | corto | completo | completo |
| Usuarios por org | 1 | 5 | Ilimitados |
| Analista IA (futuro) | — | ✓ | ✓ |

Los límites se chequean en el backend **antes** de encolar (filas, fuentes) y
en queries (retención del historial). El plan vive en `orgs.plan`.

---

## 7. Hosting

**Netlify NO sirve** — es estático, no corre Python. Separar:

- **Frontend** (`static/`) → Netlify/Vercel, o servido por el mismo backend.
- **Backend FastAPI + workers** → Railway / Render / Fly.io (PaaS, rápido de
  arrancar) o un VPS (más control, más trabajo).
- **Datos** → Supabase gestionado (ya lo tienes).
- **Redis** (si cola con RQ/Celery) → add-on del PaaS.

Recomendación para empezar: **Render o Railway** (deploy desde git, Redis y
cron incluidos) — el menor esfuerzo para validar con pilotos.

---

## 8. Seguridad de datos (no negociable)

Los datos de ventas son el activo más sensible del cliente. Mínimos:

- RLS por tenant (sección 2) — el aislamiento no depende del código de la app.
- Bucket privado, URLs firmadas de vida corta para descargas.
- Cifrado en tránsito (HTTPS) y en reposo (Supabase lo da).
- Política de **retención y borrado**: el cliente puede exportar y eliminar sus
  datos (requisito legal y de confianza).
- Secrets fuera del repo (la fuga del token `sbp_` ya nos enseñó esto).
- Logs sin datos crudos del cliente.

---

## 9. Qué se reutiliza vs. qué es nuevo

| Se reutiliza (sin tocar) | Hay que construir |
|---|---|
| `app_forecast_universal.py` (motor) | Auth + JWT en FastAPI |
| `informe.py` (insights por rol) | Esquema Postgres + RLS |
| `static/index.html` (frontend, + login) | Cola async + workers |
| Endpoints `/api/*` (adaptar a corridas) | Billing (fase 3) |
| Detección de columnas, rubro, propuestas | Panel de cuenta / historial |

---

## 9.bis. Memoria del usuario (implementado)

La app **recuerda y se adapta** por org, sin LLM (memoria determinista; el LLM
real es fase siguiente). Construido sobre lo anterior:

- **`aprendizaje.py`** — funciones puras sobre un `perfil` jsonb. Tras cada
  corrida, `fundir_corrida()` acumula: rol/país/unidad/horizonte preferidos
  (contadores de frecuencia → `defaults_sugeridos()`), rubro, series vistas,
  WAPE promedio incremental, dirección de sesgo y hallazgos recurrentes.
  `bloque_memoria()` se calcula **antes** de fundir, para comparar la corrida
  nueva con la historia ("tu última proyección sumaba X; esta suma Y").
- **Tablas nuevas** (`003_aprendizaje_forecast.sql`): `perfil_org` (1:1 con org)
  e `insights_guardados`. Misma RLS por `mis_orgs()` que el 001; sin política
  `anon`.
- **Endpoints**: `GET /api/config` (público, decide login), `POST /api/identidad`,
  `GET /api/perfil`, `POST`/`DELETE /api/guardados`. `/api/forecast` ahora
  adjunta `memoria` + `corrida_id` al informe y funde el perfil. `/api/analizar`
  devuelve `aprendido` para precargar el próximo análisis.
- **Frontend**: pantalla de login (Supabase Auth en SaaS, identidad en demo),
  panel «Mi cuenta» (perfil aprendido + historial + guardados), banner de
  memoria en el informe, botón ⭐ guardar por insight. Todas las llamadas pasan
  por `api()` con `Authorization: Bearer` en SaaS.
- **Orden seguro**: el perfil se funde **después** de un informe exitoso → un
  error del motor no corrompe la memoria (verificado).

Pendiente para SaaS real: ejecutar el `003` en Supabase y cerrar la Fase 0 (RLS).

## 10. Conexión con el roadmap

Este SaaS es el **envoltorio comercial del Analista con IA** (franja "Próximo"
del roadmap web). La arquitectura de aquí — multi-tenant, datasets persistentes,
corridas async — es exactamente la base sobre la que ese analista corre. No son
dos proyectos: es el mismo, visto desde infraestructura.

Relacionado: [[forecast-app-frontend-propio]], [[supabase-project-config]],
[[supabase-security-audit]], [[empresa-id-scheme]] (el esquema uuid + correlativo
de AgroField aplica igual a `orgs`).
