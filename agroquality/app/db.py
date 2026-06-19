# =====================================================================
# AgroQuality — persistencia. Dos backends tras una misma interfaz:
#   MODO_SAAS  -> Supabase (PostgREST) con el service key (filtra por org_id).
#   MODO_DEMO  -> diccionarios en RAM, sembrados con datos reales de Marand.
# Modelo: aq_inspeccion (cabecera) 1──* aq_pallet.
# Mismo patrón que forecast_nueva_version/app/db.py.
# =====================================================================
import uuid
import copy
import httpx

import config
from seed import inspecciones_semilla

_HEADERS = {
    "apikey": config.SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}


def _rest(path: str) -> str:
    return f"{config.SUPABASE_URL}/rest/v1/{path}"


# ---------------------------------------------------------------------
# Backend SaaS (Supabase / PostgREST)
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

    def listar_inspecciones(self, org_id) -> list:
        # Embedding por FK: trae cada inspección con sus pallets anidados.
        with httpx.Client(timeout=20) as c:
            r = c.get(_rest("aq_inspeccion"), headers=_HEADERS,
                      params={"select": "*,aq_pallet(*)", "org_id": f"eq.{org_id}",
                              "order": "fecha_frigorifico.desc"})
        r.raise_for_status()
        return [_normalizar(i) for i in r.json()]

    def get_inspeccion(self, org_id, insp_id) -> dict | None:
        with httpx.Client(timeout=15) as c:
            r = c.get(_rest("aq_inspeccion"), headers=_HEADERS,
                      params={"select": "*,aq_pallet(*)", "id": f"eq.{insp_id}",
                              "org_id": f"eq.{org_id}"})
        r.raise_for_status()
        filas = r.json()
        return _normalizar(filas[0]) if filas else None

    def crear_inspeccion(self, org_id, cabecera: dict, pallets: list) -> dict:
        fila = {"org_id": org_id, **cabecera}
        with httpx.Client(timeout=20) as c:
            r = c.post(_rest("aq_inspeccion"),
                       headers={**_HEADERS, "Prefer": "return=representation"}, json=fila)
            r.raise_for_status()
            insp = r.json()[0]
            if pallets:
                rows = [{"org_id": org_id, "inspeccion_id": insp["id"], **p} for p in pallets]
                rp = c.post(_rest("aq_pallet"),
                            headers={**_HEADERS, "Prefer": "return=representation"}, json=rows)
                rp.raise_for_status()
                insp["aq_pallet"] = rp.json()
        return _normalizar(insp)

    def borrar_inspeccion(self, org_id, insp_id) -> bool:
        # aq_pallet cae por ON DELETE CASCADE.
        with httpx.Client(timeout=15) as c:
            r = c.delete(_rest("aq_inspeccion"), headers=_HEADERS,
                         params={"id": f"eq.{insp_id}", "org_id": f"eq.{org_id}"})
        r.raise_for_status()
        return True

    # ---- Fotos (Supabase Storage). Path siempre con prefijo de org. ----
    def subir_foto(self, org_id, contenido: bytes, content_type: str, ext: str) -> str:
        ref = f"{org_id}/{uuid.uuid4().hex}.{ext}"
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.STORAGE_BUCKET}/{ref}"
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers={"apikey": config.SUPABASE_SERVICE_KEY,
                                     "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
                                     "Content-Type": content_type or "application/octet-stream",
                                     "x-upsert": "true"}, content=contenido)
        r.raise_for_status()
        return ref

    def bajar_foto(self, org_id, ref: str):
        if not ref.startswith(f"{org_id}/"):
            raise PermissionError("Foto fuera de tu organización.")
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.STORAGE_BUCKET}/{ref}"
        with httpx.Client(timeout=30) as c:
            r = c.get(url, headers={"apikey": config.SUPABASE_SERVICE_KEY,
                                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}"})
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "application/octet-stream")

    def url_foto(self, org_id, ref: str) -> str:
        # URL firmada (1 semana) para mostrar en <img> sin exponer el bucket.
        if not ref.startswith(f"{org_id}/"):
            raise PermissionError("Foto fuera de tu organización.")
        url = f"{config.SUPABASE_URL}/storage/v1/object/sign/{config.STORAGE_BUCKET}/{ref}"
        with httpx.Client(timeout=15) as c:
            r = c.post(url, headers=_HEADERS, json={"expiresIn": 604800})
        r.raise_for_status()
        return f"{config.SUPABASE_URL}/storage/v1{r.json()['signedURL']}"


# ---------------------------------------------------------------------
# Backend demo (RAM) — misma interfaz, sin red. Sembrado con Marand.
# ---------------------------------------------------------------------
class _DemoDB:
    def __init__(self):
        self._insp: dict = {}
        self._fotos: dict = {}   # ref -> (bytes, content_type)
        for ins in copy.deepcopy(inspecciones_semilla()):
            self._insp[ins["id"]] = {**ins, "org_id": "demo-org"}

    def org_de_usuario(self, user_id):
        return "demo-org"

    def listar_inspecciones(self, org_id):
        out = [i for i in self._insp.values() if i["org_id"] == org_id]
        out.sort(key=lambda i: i.get("fecha_frigorifico") or "", reverse=True)
        return [_normalizar(i) for i in out]

    def get_inspeccion(self, org_id, insp_id):
        i = self._insp.get(insp_id)
        return _normalizar(i) if i and i["org_id"] == org_id else None

    def crear_inspeccion(self, org_id, cabecera, pallets):
        insp_id = uuid.uuid4().hex[:12]
        pal = [{"id": uuid.uuid4().hex[:12], "inspeccion_id": insp_id, "org_id": org_id, **p}
               for p in pallets]
        ins = {"id": insp_id, "org_id": org_id, **cabecera, "aq_pallet": pal}
        self._insp[insp_id] = ins
        return _normalizar(ins)

    def borrar_inspeccion(self, org_id, insp_id):
        i = self._insp.get(insp_id)
        if i and i["org_id"] == org_id:
            del self._insp[insp_id]
            return True
        return False

    def subir_foto(self, org_id, contenido, content_type, ext):
        ref = f"demo/{uuid.uuid4().hex}.{ext}"
        self._fotos[ref] = (contenido, content_type or "application/octet-stream")
        return ref

    def bajar_foto(self, org_id, ref):
        if ref not in self._fotos:
            raise KeyError(ref)
        return self._fotos[ref]

    def url_foto(self, org_id, ref):
        return f"/api/fotos/{ref}"


def _normalizar(ins: dict) -> dict:
    """Aplana: el frontend espera 'pallets' (no la clave PostgREST 'aq_pallet')."""
    ins = dict(ins)
    ins["pallets"] = ins.pop("aq_pallet", ins.get("pallets", [])) or []
    return ins


DB = _SaasDB() if config.MODO_SAAS else _DemoDB()
