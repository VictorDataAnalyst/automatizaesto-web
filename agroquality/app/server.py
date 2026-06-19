# =====================================================================
# AgroQuality — backend FastAPI con frontend propio.
# Auditoría de calidad post-cosecha: inspección (lote) → pallets.
# Ejecutar:  python server.py   (abre http://localhost:8603)
# Mismo patrón que forecast_nueva_version/app/server.py.
# =====================================================================
import io
import csv
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from auth import usuario_actual
from db import DB
from seed import score_de

BASE = Path(__file__).resolve().parent
app = FastAPI(title="AgroQuality — automatizaesto", docs_url=None, redoc_url=None)

# Campos de cabecera que aceptamos del cliente (lista blanca).
CABECERA = [
    "codigo", "lote", "container", "num_factura", "compania", "exportador",
    "consignatario", "producto", "variedad", "embalaje", "tipo_producto",
    "locacion", "pais_origen", "barco", "tipo_carrier", "frigorifico",
    "fumigacion", "tipo_inspeccion", "inspector", "cajas", "total_pallets",
    "hora_frigorifico", "fecha_embalaje", "fecha_arribo", "fecha_frigorifico",
    "estado", "fotos",
    # Fase B/C — notas y extras de cabecera
    "notas_calidad", "notas_inspector", "digitado_por", "tecnologia_postcosecha",
    "tipo_atmosfera", "tipo_bolsa", "upc", "numero_reporte", "termografia",
]
MAX_FOTOS = 15  # por galería (pallet / muestra / contenedor), igual que el formato QIMA


def _cap_fotos(fotos):
    """Limita a 15 fotos por tipo de galería."""
    if not fotos:
        return None
    por_tipo, out = {}, []
    for f in fotos:
        t = (f or {}).get("tipo", "pallet")
        por_tipo[t] = por_tipo.get(t, 0) + 1
        if por_tipo[t] <= MAX_FOTOS:
            out.append(f)
    return out or None
PALLET = [
    "codigo", "productor", "clase", "calibre", "temp_prom", "peso_neto_prom",
    "brix_prom", "cajas_muestra", "tamano_muestra", "pct_calidad",
    "pct_condicion", "defecto_principal", "fotos",
    # Fase B
    "variedad", "fecha_embalaje", "etiqueta", "embalaje", "firmeza_psi_min",
    "firmeza_psi_max", "plu_pct", "golpe_vista", "trazabilidad", "pti",
    "base_pallet_danado", "qc_embalaje", "defectos",
]
EXT_OK = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic"}


def _org_de(user: dict) -> str:
    org_id = DB.org_de_usuario(user["user_id"])
    if not org_id:
        raise HTTPException(403, "Tu usuario no pertenece a ninguna organización.")
    return org_id


# ---------------------------------------------------------------------
# Config / estado
# ---------------------------------------------------------------------
@app.get("/api/config")
def config_publica():
    return {"modo": config.MODO,
            "supabase_url": config.SUPABASE_URL or None,
            "supabase_anon_key": config.SUPABASE_ANON_KEY or None}


@app.get("/api/estado")
def estado(user=Depends(usuario_actual)):
    return {"modo": config.MODO, "usuario": user.get("email"),
            "es_admin": _es_admin(user.get("email"))}


# ---------------------------------------------------------------------
# Inspecciones
# ---------------------------------------------------------------------
@app.get("/api/inspecciones")
def listar(user=Depends(usuario_actual)):
    org_id = _org_de(user)
    return {"inspecciones": DB.listar_inspecciones(org_id)}


@app.get("/api/inspecciones/{insp_id}")
def obtener(insp_id: str, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    ins = DB.get_inspeccion(org_id, insp_id)
    if not ins:
        raise HTTPException(404, "Inspección no encontrada.")
    return ins


class PalletIn(BaseModel):
    codigo: str
    productor: str | None = None
    clase: str | None = "1"
    calibre: int | None = None
    temp_prom: float | None = None
    peso_neto_prom: float | None = 10
    brix_prom: float | None = None
    cajas_muestra: int | None = None
    tamano_muestra: int | None = None
    pct_calidad: float = 0
    pct_condicion: float = 0
    defecto_principal: str | None = None
    # Fase B — ficha completa de pallet
    variedad: str | None = None
    fecha_embalaje: str | None = None
    etiqueta: str | None = None
    embalaje: str | None = None
    firmeza_psi_min: float | None = None
    firmeza_psi_max: float | None = None
    plu_pct: float | None = None
    golpe_vista: str | None = None          # good | fair | poor
    trazabilidad: bool | None = None
    pti: bool | None = None
    base_pallet_danado: bool | None = None
    qc_embalaje: str | None = None
    defectos: list[dict] | None = None      # [{nombre, categoria, pct}]
    fotos: list[dict] | None = None         # [{tipo, ref}]


class InspeccionIn(BaseModel):
    codigo: str | None = None
    lote: str
    container: str | None = None
    num_factura: str | None = None
    compania: str | None = None
    exportador: str | None = None
    consignatario: str | None = None
    producto: str | None = "Avocados"
    variedad: str | None = "Hass"
    embalaje: str | None = None
    tipo_producto: str | None = "CONV"
    locacion: str | None = None
    pais_origen: str | None = "Peru"
    barco: str | None = None
    tipo_carrier: str | None = "Ocean"
    frigorifico: str | None = None
    fumigacion: str | None = "None"
    tipo_inspeccion: str | None = "Normal Inspection"
    inspector: str | None = None
    cajas: int | None = None
    total_pallets: int | None = None
    hora_frigorifico: str | None = None
    fecha_embalaje: str | None = None
    fecha_arribo: str | None = None
    fecha_frigorifico: str | None = None
    fotos: list[dict] | None = None   # galería del contenedor [{tipo:'contenedor', ref}]
    notas_calidad: str | None = None
    notas_inspector: str | None = None
    digitado_por: str | None = None
    # Fase C — extras de cabecera + termografía
    tecnologia_postcosecha: str | None = None
    tipo_atmosfera: str | None = None
    tipo_bolsa: str | None = None
    upc: str | None = None
    numero_reporte: str | None = None
    termografia: list[dict] | None = None   # [{serial, trip_length_dias, temp_min, temp_max, temp_avg}]
    pallets: list[PalletIn] = []


def _preparar(body: InspeccionIn) -> tuple[dict, list]:
    if not body.lote:
        raise HTTPException(400, "Falta el Lote.")
    if not body.fecha_frigorifico:
        raise HTTPException(400, "Falta la fecha de ingreso al frigorífico.")
    if not body.pallets:
        raise HTTPException(400, "Agrega al menos un pallet.")

    cab = {k: getattr(body, k) for k in CABECERA if getattr(body, k, None) is not None}
    cab.setdefault("estado", "cerrada")
    if cab.get("fotos"):
        cab["fotos"] = _cap_fotos(cab["fotos"])

    pallets, cont = [], {"good": 0, "fair": 0, "poor": 0}
    suma_tot = 0.0
    for p in body.pallets:
        pcal = float(p.pct_calidad or 0)
        pcond = float(p.pct_condicion or 0)
        ptot = round(pcal + pcond, 2)
        sc = score_de(ptot)
        cont[sc] += 1
        suma_tot += ptot
        row = {k: getattr(p, k) for k in PALLET if getattr(p, k, None) is not None}
        row.update(pct_calidad=pcal, pct_condicion=pcond, pct_total=ptot,
                   pallet_score=sc, sample_score=sc)
        if row.get("fotos"):
            row["fotos"] = _cap_fotos(row["fotos"])
        pallets.append(row)

    n = len(pallets)
    cab["pct_total_prom"] = round(suma_tot / n, 2)
    cab["score_global"] = score_de(suma_tot / n)
    cab["resumen"] = {"pallets": n, **cont}
    cab.setdefault("total_pallets", n)
    return cab, pallets


@app.post("/api/inspecciones")
def crear(body: InspeccionIn, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    cab, pallets = _preparar(body)
    ins = DB.crear_inspeccion(org_id, cab, pallets)
    return {"ok": True, "inspeccion": ins}


@app.delete("/api/inspecciones/{insp_id}")
def borrar(insp_id: str, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    return {"ok": DB.borrar_inspeccion(org_id, insp_id)}


# ---------------------------------------------------------------------
# Registro de usuarios por DOMINIO de empresa.
#  - Si el dominio ya tiene una empresa (algún usuario con ese dominio),
#    el nuevo usuario se asocia a esa misma organización.
#  - Si el dominio es nuevo, se crea la organización y los siguientes
#    usuarios con ese dominio se asociarán a ella.
# Todo con el service key; no toca el trigger on_signup (compartido).
# ---------------------------------------------------------------------
def _admin_h():
    sk = config.SUPABASE_SERVICE_KEY
    return {"apikey": sk, "Authorization": f"Bearer {sk}", "Content-Type": "application/json"}


def _nombre_empresa(dominio: str) -> str:
    """Nombre legible para una empresa nueva a partir del dominio."""
    etiqueta = dominio.split(".")[0]
    return etiqueta[:1].upper() + etiqueta[1:] if etiqueta else dominio


# El "admin" (super-admin del vendor) es quien valida nuevos dominios.
SUPERADMIN_DOMINIO = "automatizaesto.com"


def _es_admin(email: str | None) -> bool:
    return bool(email) and email.lower().endswith("@" + SUPERADMIN_DOMINIO)


def _users(c: httpx.Client) -> list:
    r = c.get(config.SUPABASE_URL + "/auth/v1/admin/users",
              headers=_admin_h(), params={"per_page": "200"})
    r.raise_for_status()
    return r.json().get("users", [])


def _estado(u: dict) -> str:
    return (u.get("app_metadata") or {}).get("estado", "activo")


def _org_activa_dominio(c: httpx.Client, dominio: str):
    """org_id de la empresa del dominio considerando SOLO usuarios activos
    (los 'pendiente' no cuentan). None si el dominio aún no está habilitado."""
    activos = [u["id"] for u in _users(c)
               if (u.get("email") or "").lower().endswith("@" + dominio)
               and _estado(u) != "pendiente"]
    if not activos:
        return None
    r = c.get(config.SUPABASE_URL + "/rest/v1/miembros", headers=_admin_h(),
              params={"select": "org_id", "user_id": f"in.({','.join(activos)})", "limit": "1"})
    r.raise_for_status()
    return r.json()[0]["org_id"] if r.json() else None


def _crear_user(c: httpx.Client, email, password, app_metadata, banned=False) -> str:
    admin = config.SUPABASE_URL + "/auth/v1/admin/users"
    r = c.post(admin, headers=_admin_h(),
               json={"email": email, "password": password, "email_confirm": True,
                     "app_metadata": app_metadata})
    if r.status_code not in (200, 201):
        if r.status_code in (409, 422) or "already" in r.text.lower() \
                or "registered" in r.text.lower():
            raise HTTPException(409, "Ese correo ya tiene una cuenta o solicitud pendiente.")
        raise HTTPException(502, "No se pudo crear el usuario en Supabase.")
    uid = r.json()["id"]
    if banned:   # bloqueado hasta que un admin lo apruebe
        c.put(f"{admin}/{uid}", headers=_admin_h(), json={"ban_duration": "876000h"}).raise_for_status()
    return uid


def _asociar(c: httpx.Client, uid: str, org: str, rol: str):
    """Mueve la membresía del usuario a `org` (borrando su org personal si la tuviera)."""
    rest = config.SUPABASE_URL + "/rest/v1/"
    r = c.get(rest + "miembros", headers=_admin_h(),
              params={"select": "org_id", "user_id": f"eq.{uid}"})
    r.raise_for_status()
    actuales = [m["org_id"] for m in r.json()]
    if org in actuales:
        c.patch(rest + "miembros", headers=_admin_h(),
                params={"user_id": f"eq.{uid}", "org_id": f"eq.{org}"}, json={"rol": rol})
        return
    personal = actuales[0] if actuales else None
    if personal:
        c.patch(rest + "miembros", headers=_admin_h(),
                params={"user_id": f"eq.{uid}", "org_id": f"eq.{personal}"},
                json={"org_id": org, "rol": rol}).raise_for_status()
        c.delete(rest + "orgs", headers=_admin_h(), params={"id": f"eq.{personal}"})
    else:
        c.post(rest + "miembros", headers=_admin_h(),
               json={"user_id": uid, "org_id": org, "rol": rol}).raise_for_status()


def _quitar_orgs(c: httpx.Client, uid: str):
    """Borra las orgs del usuario (su org personal) — usado para dejar a un pendiente sin empresa."""
    rest = config.SUPABASE_URL + "/rest/v1/"
    r = c.get(rest + "miembros", headers=_admin_h(),
              params={"select": "org_id", "user_id": f"eq.{uid}"})
    r.raise_for_status()
    for m in r.json():
        c.delete(rest + "orgs", headers=_admin_h(), params={"id": f"eq.{m['org_id']}"})


class RegistroIn(BaseModel):
    email: str
    password: str


@app.post("/api/registro")
def registro(body: RegistroIn):
    if not config.MODO_SAAS:
        raise HTTPException(400, "El registro solo está disponible en modo SaaS.")
    email = (body.email or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Ingresa un correo válido.")
    if len(body.password or "") < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres.")
    dominio = email.split("@")[-1]
    with httpx.Client(timeout=30) as c:
        org = _org_activa_dominio(c, dominio)
        if org:
            # Dominio habilitado -> alta inmediata, asociado a su empresa.
            uid = _crear_user(c, email, body.password, {"estado": "activo", "dominio": dominio})
            _asociar(c, uid, org, "analista")
            return {"ok": True, "estado": "activo"}
        # Dominio no habilitado -> queda PENDIENTE (bloqueado) hasta aprobación.
        uid = _crear_user(c, email, body.password,
                          {"estado": "pendiente", "dominio": dominio}, banned=True)
        _quitar_orgs(c, uid)
        return {"ok": True, "estado": "pendiente"}


# ---------------------------------------------------------------------
# Aprobación de solicitudes (solo super-admin del vendor).
# ---------------------------------------------------------------------
def _exigir_admin(user: dict):
    if not _es_admin(user.get("email")):
        raise HTTPException(403, "Solo un administrador de automatizaesto puede hacer esto.")


@app.get("/api/solicitudes")
def listar_solicitudes(user=Depends(usuario_actual)):
    _exigir_admin(user)
    with httpx.Client(timeout=20) as c:
        out = [{"id": u["id"], "email": u.get("email"),
                "dominio": (u.get("app_metadata") or {}).get("dominio"),
                "creado_en": u.get("created_at")}
               for u in _users(c) if _estado(u) == "pendiente"]
    out.sort(key=lambda s: s.get("creado_en") or "", reverse=True)
    return {"solicitudes": out}


@app.post("/api/solicitudes/{uid}/aprobar")
def aprobar_solicitud(uid: str, user=Depends(usuario_actual)):
    _exigir_admin(user)
    admin = config.SUPABASE_URL + "/auth/v1/admin/users"
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{admin}/{uid}", headers=_admin_h())
        r.raise_for_status()
        u = r.json()
        if _estado(u) != "pendiente":
            raise HTTPException(409, "Esa solicitud ya fue resuelta.")
        dominio = (u.get("email") or "").lower().split("@")[-1]
        org = _org_activa_dominio(c, dominio)
        nueva = org is None
        if nueva:   # primera empresa de ese dominio -> crear la org
            r = c.post(config.SUPABASE_URL + "/rest/v1/orgs",
                       headers={**_admin_h(), "Prefer": "return=representation"},
                       json={"nombre": _nombre_empresa(dominio), "plan": "business"})
            r.raise_for_status()
            org = r.json()[0]["id"]
        _asociar(c, uid, org, "owner" if nueva else "analista")
        c.put(f"{admin}/{uid}", headers=_admin_h(),
              json={"ban_duration": "none",
                    "app_metadata": {"estado": "activo", "dominio": dominio}}).raise_for_status()
    return {"ok": True, "empresa": _nombre_empresa(dominio), "empresa_nueva": nueva}


@app.post("/api/solicitudes/{uid}/rechazar")
def rechazar_solicitud(uid: str, user=Depends(usuario_actual)):
    _exigir_admin(user)
    with httpx.Client(timeout=20) as c:
        c.delete(f"{config.SUPABASE_URL}/auth/v1/admin/users/{uid}",
                 headers=_admin_h()).raise_for_status()
    return {"ok": True}


# ---------------------------------------------------------------------
# Fotos de inspección (galería pallet / muestra)
# ---------------------------------------------------------------------
@app.post("/api/fotos")
async def subir_foto(archivo: UploadFile = File(...), tipo: str = Form("pallet"),
                     user=Depends(usuario_actual)):
    org_id = _org_de(user)
    ext = EXT_OK.get(archivo.content_type or "")
    if not ext:
        raise HTTPException(400, "Formato no soportado (usa JPG, PNG, WEBP o HEIC).")
    contenido = await archivo.read()
    if len(contenido) > 8 * 1024 * 1024:
        raise HTTPException(400, "La foto supera los 8 MB.")
    ref = DB.subir_foto(org_id, contenido, archivo.content_type, ext)
    return {"ref": ref, "tipo": tipo, "url": DB.url_foto(org_id, ref)}


@app.get("/api/fotos-url")
def foto_url(ref: str, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    try:
        return {"url": DB.url_foto(org_id, ref)}
    except PermissionError as e:
        raise HTTPException(403, str(e))


@app.get("/api/fotos/{ref:path}")
def ver_foto(ref: str, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    try:
        contenido, ct = DB.bajar_foto(org_id, ref)
    except (KeyError, FileNotFoundError):
        raise HTTPException(404, "Foto no encontrada.")
    except PermissionError as e:
        raise HTTPException(403, str(e))
    return Response(content=contenido, media_type=ct,
                    headers={"Cache-Control": "private, max-age=3600"})


# ---------------------------------------------------------------------
# Exportación CSV — el gerente baja el período filtrado
# ---------------------------------------------------------------------
@app.get("/api/export.csv")
def exportar(d1: str | None = None, d2: str | None = None,
             score: str | None = None, consignatario: str | None = None,
             user=Depends(usuario_actual)):
    org_id = _org_de(user)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Inspeccion", "Lote", "Consignatario", "Locacion",
                "Ingreso_frigorifico", "Pallet", "Score", "Calibre", "Productor",
                "Pct_Calidad", "Pct_Condicion", "Pct_Total", "Defecto_principal",
                "Muestra"])
    for i in DB.listar_inspecciones(org_id):
        f = i.get("fecha_frigorifico") or ""
        if d1 and f < d1:
            continue
        if d2 and f > d2:
            continue
        if consignatario and i.get("consignatario") != consignatario:
            continue
        if score and i.get("score_global") != score:
            continue
        for p in i.get("pallets", []):
            w.writerow([i.get("codigo") or i.get("id"), i.get("lote"),
                        i.get("consignatario"), i.get("locacion"), f,
                        p.get("codigo"), p.get("pallet_score"), p.get("calibre"),
                        p.get("productor"), p.get("pct_calidad"),
                        p.get("pct_condicion"), p.get("pct_total"),
                        p.get("defecto_principal"), p.get("tamano_muestra")])
    buf.seek(0)
    data = "﻿" + buf.getvalue()
    return StreamingResponse(
        io.BytesIO(data.encode("utf-8")), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="agroquality.csv"'})


app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8603)
