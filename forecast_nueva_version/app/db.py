# =====================================================================
# Persistencia — dos backends tras una misma interfaz:
#   MODO_SAAS  -> Supabase (PostgREST + Storage) con el service key.
#   MODO_DEMO  -> diccionarios en RAM (comportamiento actual de la demo).
# El resto de la app (server.py) no sabe cuál está activo.
# =====================================================================
import io
import uuid
import httpx

import config

# El service key bypasea RLS: el backend filtra SIEMPRE por org_id a mano.
# (Patrón service-role: el aislamiento lo garantiza el código + la org del JWT.)
_HEADERS = {
    "apikey": config.SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


def _rest(path: str) -> str:
    return f"{config.SUPABASE_URL}/rest/v1/{path}"


# ---------------------------------------------------------------------
# Backend SaaS (Supabase)
# ---------------------------------------------------------------------
class _SaasDB:
    def org_de_usuario(self, user_id: str) -> str | None:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("miembros"), headers=_HEADERS,
                      params={"select": "org_id", "user_id": f"eq.{user_id}",
                              "limit": "1"})
        r.raise_for_status()
        filas = r.json()
        return filas[0]["org_id"] if filas else None

    def crear_dataset(self, org_id, meta: dict) -> dict:
        fila = {"org_id": org_id, **meta}
        with httpx.Client(timeout=15) as c:
            r = c.post(_rest("datasets"), headers={**_HEADERS, "Prefer": "return=representation"},
                       json=fila)
        r.raise_for_status()
        return r.json()[0]

    def get_dataset(self, org_id, dataset_id) -> dict | None:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("datasets"), headers=_HEADERS,
                      params={"id": f"eq.{dataset_id}", "org_id": f"eq.{org_id}"})
        r.raise_for_status()
        filas = r.json()
        return filas[0] if filas else None

    def crear_corrida(self, org_id, dataset_id, config_dict) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.post(_rest("corridas"), headers={**_HEADERS, "Prefer": "return=representation"},
                       json={"org_id": org_id, "dataset_id": dataset_id,
                             "estado": "procesando", "config": config_dict})
        r.raise_for_status()
        return r.json()[0]

    def guardar_informe(self, org_id, corrida_id, informe: dict):
        with httpx.Client(timeout=15) as c:
            r = c.patch(_rest("corridas"), headers=_HEADERS,
                        params={"id": f"eq.{corrida_id}", "org_id": f"eq.{org_id}"},
                        json={"estado": "lista", "informe": informe,
                              "terminado_en": "now()"})
        r.raise_for_status()

    def historial(self, org_id, limite=20) -> list:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("corridas"), headers=_HEADERS,
                      params={"select": "id,estado,config,creado_en,dataset_id",
                              "org_id": f"eq.{org_id}", "order": "creado_en.desc",
                              "limit": str(limite)})
        r.raise_for_status()
        return r.json()

    # Perfil aprendido (1:1 con org) — upsert sobre perfil_org
    def get_perfil(self, org_id) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("perfil_org"), headers=_HEADERS,
                      params={"select": "perfil", "org_id": f"eq.{org_id}",
                              "limit": "1"})
        r.raise_for_status()
        filas = r.json()
        return filas[0]["perfil"] if filas else {}

    def guardar_perfil(self, org_id, perfil: dict):
        with httpx.Client(timeout=15) as c:
            r = c.post(_rest("perfil_org"),
                       headers={**_HEADERS, "Prefer": "resolution=merge-duplicates"},
                       params={"on_conflict": "org_id"},
                       json={"org_id": org_id, "perfil": perfil,
                             "actualizado_en": "now()"})
        r.raise_for_status()

    # Insights que el usuario marcó como suyos
    def guardar_insight(self, org_id, corrida_id, insight: dict, nota, creado_por) -> dict:
        with httpx.Client(timeout=15) as c:
            r = c.post(_rest("insights_guardados"),
                       headers={**_HEADERS, "Prefer": "return=representation"},
                       json={"org_id": org_id, "corrida_id": corrida_id,
                             "insight": insight, "nota": nota,
                             "creado_por": creado_por})
        r.raise_for_status()
        return r.json()[0]

    def listar_guardados(self, org_id, limite=50) -> list:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("insights_guardados"), headers=_HEADERS,
                      params={"select": "id,corrida_id,insight,nota,creado_en",
                              "org_id": f"eq.{org_id}", "order": "creado_en.desc",
                              "limit": str(limite)})
        r.raise_for_status()
        return r.json()

    def borrar_guardado(self, org_id, guardado_id) -> bool:
        with httpx.Client(timeout=15) as c:
            r = c.delete(_rest("insights_guardados"), headers=_HEADERS,
                         params={"id": f"eq.{guardado_id}", "org_id": f"eq.{org_id}"})
        r.raise_for_status()
        return True

    # Storage
    def subir_archivo(self, org_id, dataset_id, contenido: bytes, nombre: str) -> str:
        path = f"{org_id}/{dataset_id}/{nombre}"
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.STORAGE_BUCKET}/{path}"
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers={"apikey": config.SUPABASE_SERVICE_KEY,
                                     "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
                                     "Content-Type": "application/octet-stream",
                                     "x-upsert": "true"},
                       content=contenido)
        r.raise_for_status()
        return path

    def bajar_archivo(self, storage_path: str) -> bytes:
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.STORAGE_BUCKET}/{storage_path}"
        with httpx.Client(timeout=30) as c:
            r = c.get(url, headers={"apikey": config.SUPABASE_SERVICE_KEY,
                                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}"})
        r.raise_for_status()
        return r.content


# ---------------------------------------------------------------------
# Backend demo (RAM) — misma interfaz, sin red.
# ---------------------------------------------------------------------
class _DemoDB:
    def __init__(self):
        self._ds, self._co, self._files = {}, {}, {}
        self._perfil, self._guard = {}, {}   # por org_id

    def org_de_usuario(self, user_id):  # demo: una org fija
        return "demo-org"

    def crear_dataset(self, org_id, meta):
        d = {"id": uuid.uuid4().hex[:12], "org_id": org_id, **meta}
        self._ds[d["id"]] = d
        return d

    def get_dataset(self, org_id, dataset_id):
        d = self._ds.get(dataset_id)
        return d if d and d["org_id"] == org_id else None

    def crear_corrida(self, org_id, dataset_id, config_dict):
        c = {"id": uuid.uuid4().hex[:12], "org_id": org_id,
             "dataset_id": dataset_id, "estado": "procesando", "config": config_dict}
        self._co[c["id"]] = c
        return c

    def guardar_informe(self, org_id, corrida_id, informe):
        if corrida_id in self._co:
            self._co[corrida_id].update(estado="lista", informe=informe)

    def historial(self, org_id, limite=20):
        return [c for c in self._co.values() if c["org_id"] == org_id][-limite:][::-1]

    def get_perfil(self, org_id):
        return self._perfil.get(org_id, {})

    def guardar_perfil(self, org_id, perfil):
        self._perfil[org_id] = perfil

    def guardar_insight(self, org_id, corrida_id, insight, nota, creado_por):
        g = {"id": uuid.uuid4().hex[:12], "org_id": org_id,
             "corrida_id": corrida_id, "insight": insight, "nota": nota,
             "creado_en": None}
        self._guard.setdefault(org_id, {})[g["id"]] = g
        return g

    def listar_guardados(self, org_id, limite=50):
        return list(self._guard.get(org_id, {}).values())[::-1][:limite]

    def borrar_guardado(self, org_id, guardado_id):
        return self._guard.get(org_id, {}).pop(guardado_id, None) is not None

    def subir_archivo(self, org_id, dataset_id, contenido, nombre):
        path = f"{org_id}/{dataset_id}/{nombre}"
        self._files[path] = contenido
        return path

    def bajar_archivo(self, storage_path):
        return self._files[storage_path]


DB = _SaasDB() if config.MODO_SAAS else _DemoDB()
