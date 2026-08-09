# =====================================================================
# FORECAST — backend FastAPI con frontend propio
# Reutiliza el motor validado de files/app_forecast_universal.py.
# Ejecutar:  python server.py   (abre http://localhost:8602)
# =====================================================================
import io
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent / "files"))
sys.path.insert(0, str(BASE))
from app_forecast_universal import (detectar_columnas, prevalidar,    # noqa: E402
                                    entrenar_y_competir, MOTOR_INFO,
                                    GRANULARIDADES, horizonte_maximo)
from informe import generar_informe, PAISES, FREQ_PLURAL             # noqa: E402
import config                                                         # noqa: E402
import aprendizaje                                                     # noqa: E402
from auth import usuario_actual                                       # noqa: E402
from db import DB                                                     # noqa: E402
import plan as plan_mod                                               # noqa: E402
import correo as correo_mod                                           # noqa: E402
import asistente                                                      # noqa: E402
import capacidad                                                      # noqa: E402
import precision                                                      # noqa: E402
import fva                                                            # noqa: E402
import excel                                                          # noqa: E402


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _org_de(user: dict) -> str:
    """org del usuario; 403 si no pertenece a ninguna (no debería en demo)."""
    org_id = DB.org_de_usuario(user["user_id"])
    if not org_id:
        raise HTTPException(403, "Tu usuario no pertenece a ninguna organización.")
    return org_id

app = FastAPI(title="Forecast — automatizaesto", docs_url=None, redoc_url=None)

# Caché de cómputo en RAM (objetos pesados de pandas entre pasos del flujo).
# NO es el almacén durable: eso es DB (Supabase en SaaS). Si se pierde la caché
# (reinicio), se reconstruye bajando el archivo de Storage. Clave = dataset_id.
WORKING: dict = {}

import numpy as np  # noqa: E402  (usado por /api/plantilla)

# ---------------------------------------------------------------------
# Detección de rubro y propuestas de análisis según los datos
# ---------------------------------------------------------------------
RUBROS = [
    ("Agroexportación", ["tonelada", "tm", "kg", "kilos", "lote", "fundo", "cosecha",
                         "campo", "palta", "arandano", "uva", "esparrago", "mercado"]),
    ("Retail / Comercio", ["venta", "sku", "tienda", "sucursal", "producto", "ticket",
                           "unidades", "precio"]),
    ("Servicios / BPO", ["hora", "hrs", "llamada", "campana", "campaña", "agente",
                         "ticket", "caso", "facturable"]),
    ("Finanzas", ["ingreso", "facturacion", "cobranza", "monto", "importe", "soles", "usd"]),
]

def detectar_rubro(columnas) -> dict:
    texto = " ".join(str(c).lower() for c in columnas)
    mejor, hits = "General", 0
    for nombre, palabras in RUBROS:
        n = sum(1 for p in palabras if p in texto)
        if n > hits:
            mejor, hits = nombre, n
    return {"nombre": mejor, "confianza": "alta" if hits >= 2 else "media" if hits == 1 else "baja"}


def proponer_analisis(df: pd.DataFrame, sug: dict) -> list:
    """Qué puede hacer la app con ESTOS datos — y qué falta para más."""
    cols_lower = {str(c).lower(): c for c in df.columns}
    tiene_stock = any(p in c for c in cols_lower for p in ("stock", "inventario", "existencia"))
    tiene_serie = sug.get("serie") is not None
    props = [
        {"id": "proyeccion", "titulo": "Proyección de tu métrica",
         "desc": f"Pronóstico de «{sug.get('valor', 'tu valor')}» con rango de confianza, validado contra tu propia historia.",
         "disponible": True, "requiere": None},
        {"id": "estacionalidad", "titulo": "Patrón estacional",
         "desc": "Qué días/meses son tus picos y valles, y cuánto pesan.",
         "disponible": True, "requiere": None},
        {"id": "feriados", "titulo": "Efecto feriados",
         "desc": "Cuántos feriados cruza tu proyección y cómo te afectaron históricamente.",
         "disponible": True, "requiere": None},
    ]
    props.append({"id": "concentracion", "titulo": "Concentración y riesgo",
                  "desc": "Qué series concentran tu volumen (Pareto 80/20).",
                  "disponible": tiene_serie,
                  "requiere": None if tiene_serie else
                  "una columna de serie (cliente, producto, mercado…)"})
    props.append({"id": "stock", "titulo": "Riesgo de quiebre de stock",
                  "desc": "Cruce de demanda proyectada contra tu inventario disponible.",
                  "disponible": False if not tiene_stock else True,
                  "requiere": None if tiene_stock else
                  "una columna de stock/inventario — descarga la plantilla extendida"})
    return props


# ---------------------------------------------------------------------
# Helpers de sesión: la caché de cómputo se reconstruye desde Storage
# ---------------------------------------------------------------------
# Sin esto, si el análisis de un cliente falla en producción nadie se entera:
# el usuario ve un error y el equipo no tiene rastro. Va a stdout, que es lo
# que capturan Render/Railway en su pestaña de Logs.
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("forecast")

MAX_SUBIDA_MB = int(os.environ.get("MAX_SUBIDA_MB", "25"))
# 0 = sin tope. Protege el costo de CPU mientras el producto es gratuito.
MAX_CORRIDAS_DIA = int(os.environ.get("MAX_CORRIDAS_DIA", "50"))


async def _leer_subida(archivo: UploadFile) -> bytes:
    """Lee el archivo en trozos y corta pasado el límite: nunca cargamos en
    memoria más de lo permitido (un Excel gigante tumbaría el proceso)."""
    tope = MAX_SUBIDA_MB * 1024 * 1024
    trozos, total = [], 0
    while trozo := await archivo.read(1024 * 1024):
        total += len(trozo)
        if total > tope:
            raise HTTPException(413, f"El archivo supera el límite de {MAX_SUBIDA_MB} MB.")
        trozos.append(trozo)
    if not total:
        raise HTTPException(400, "El archivo está vacío.")
    return b"".join(trozos)


def _leer_df(crudo: bytes, nombre: str) -> pd.DataFrame:
    if nombre.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(crudo))
    return pd.read_excel(io.BytesIO(crudo))


def _working(org_id: str, token: str) -> dict:
    """Devuelve la caché de cómputo del dataset; si se perdió (reinicio),
    la reconstruye bajando el archivo de Storage. SIEMPRE verifica que el
    dataset pertenezca a la org del usuario (aislamiento, incluso en cache hit)."""
    w = WORKING.get(token)
    if w and w.get("org_id") == org_id:
        return w
    ds = DB.get_dataset(org_id, token)   # filtra por org_id -> None si no es suya
    if not ds:
        raise HTTPException(404, "Sesión expirada: vuelve a subir el archivo.")
    if w:                                # cache hit pero de otra org: revalidado arriba
        return w
    crudo = DB.bajar_archivo(ds["storage_path"])
    w = {"df": _leer_df(crudo, ds["nombre"]), "nombre": ds["nombre"], "org_id": org_id}
    WORKING[token] = w
    return w


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
@app.get("/api/config")
def config_publica():
    """Público (sin auth): el frontend decide si pinta login Supabase o entra
    en modo demo. La anon key es pública por diseño en Supabase."""
    return {"modo": config.MODO,
            "supabase_url": config.SUPABASE_URL or None,
            "supabase_anon_key": config.SUPABASE_ANON_KEY or None}


@app.get("/api/estado")
def estado(user=Depends(usuario_actual)):
    return {"modo": config.MODO, "motor": MOTOR_INFO, "usuario": user.get("email")}


# ---------------------------------------------------------------------
# Cuenta del usuario: identidad, perfil aprendido e insights guardados
# ---------------------------------------------------------------------
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]{2,}$")


class Identidad(BaseModel):
    nombre: str | None = None
    negocio: str | None = None
    email: str | None = None
    # Consentimiento comercial EXPLÍCITO y separado (Ley 29733): tener el correo
    # para operar la cuenta no autoriza a enviar promociones. None = no respondió.
    acepta_promos: bool | None = None


@app.post("/api/identidad")
def set_identidad(idn: Identidad, user=Depends(usuario_actual)):
    """El usuario 'ingresa su información'. Se guarda en su perfil de org."""
    org_id = _org_de(user)
    perfil = {**aprendizaje.perfil_vacio(), **(DB.get_perfil(org_id) or {})}
    previa = perfil.get("identidad") or {}

    email = (idn.email or "").strip().lower() or None
    if email and not _RE_EMAIL.match(email):
        raise HTTPException(400, "Ese correo no parece válido.")
    # En SaaS el correo de la cuenta manda; el del formulario solo aplica en demo.
    email = user.get("email") or email or previa.get("email")

    identidad = {
        "nombre": idn.nombre or previa.get("nombre") or user.get("email"),
        "negocio": idn.negocio or previa.get("negocio"),
        "email": email,
        "acepta_promos": previa.get("acepta_promos", False),
        "consentimiento_en": previa.get("consentimiento_en"),
    }
    # Solo sellamos fecha cuando el usuario responde de verdad (no en cada guardado).
    if idn.acepta_promos is not None and idn.acepta_promos != previa.get("acepta_promos"):
        identidad["acepta_promos"] = bool(idn.acepta_promos)
        identidad["consentimiento_en"] = _ahora_iso() if idn.acepta_promos else None

    perfil["identidad"] = identidad
    perfil["actualizado_en"] = _ahora_iso()
    DB.guardar_perfil(org_id, perfil)
    return {"ok": True, "identidad": identidad}


@app.get("/api/perfil")
def get_perfil(user=Depends(usuario_actual)):
    """Lo que la app aprendió del negocio + defaults sugeridos + guardados.
    Es lo que el usuario ve al entrar a su cuenta."""
    org_id = _org_de(user)
    perfil = DB.get_perfil(org_id) or {}
    return {
        "usuario": user.get("email"),
        "perfil": aprendizaje.resumen_perfil(perfil),
        "sugerencias": aprendizaje.defaults_sugeridos(perfil),
        "historial": DB.historial(org_id),
        "guardados": DB.listar_guardados(org_id),
    }


class GuardarInsight(BaseModel):
    corrida_id: str | None = None
    insight: dict
    nota: str | None = None


@app.post("/api/guardados")
def crear_guardado(body: GuardarInsight, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    creado_por = None if user["modo"] == "demo" else user["user_id"]
    g = DB.guardar_insight(org_id, body.corrida_id, body.insight, body.nota, creado_por)
    return {"ok": True, "guardado": g}


@app.delete("/api/guardados/{guardado_id}")
def borrar_guardado(guardado_id: str, user=Depends(usuario_actual)):
    org_id = _org_de(user)
    return {"ok": DB.borrar_guardado(org_id, guardado_id)}


@app.post("/api/analizar")
async def analizar(archivo: UploadFile = File(...), user=Depends(usuario_actual)):
    crudo = await _leer_subida(archivo)
    try:
        df = _leer_df(crudo, archivo.filename)
    except Exception as e:
        raise HTTPException(400, f"No pude leer el archivo: {e}")
    if df.empty or len(df.columns) < 2:
        raise HTTPException(400, "El archivo necesita al menos una columna de fecha y una numérica.")

    org_id = DB.org_de_usuario(user["user_id"])
    if not org_id:
        raise HTTPException(403, "Tu usuario no pertenece a ninguna organización.")
    sug = detectar_columnas(df)

    # Persistir metadato + archivo; el id del dataset ES el token del flujo.
    ds = DB.crear_dataset(org_id, {
        "nombre": archivo.filename, "storage_path": "",
        "filas": int(len(df)),
        "columnas": {k: (str(v) if v else None) for k, v in sug.items()},
        "rubro": detectar_rubro(df.columns)["nombre"],
        "creado_por": None if user["modo"] == "demo" else user["user_id"],
    })
    token = ds["id"]
    ds["storage_path"] = DB.subir_archivo(org_id, token, crudo, archivo.filename)
    WORKING[token] = {"df": df, "nombre": archivo.filename, "org_id": org_id}
    DB.registrar_evento(org_id, "datos_subidos",
                        {"filas": int(len(df)), "columnas": int(len(df.columns)),
                         "rubro": detectar_rubro(df.columns)["nombre"]})

    return {
        "token": token, "archivo": archivo.filename, "filas": int(len(df)),
        "columnas": [{"nombre": str(c),
                      "tipo": ("fecha" if c == sug["fecha"] else
                               "numérica" if pd.api.types.is_numeric_dtype(df[c]) else "texto"),
                      "muestra": [str(v) for v in df[c].dropna().head(3)]}
                     for c in df.columns],
        "sugerencia": sug,
        "rubro": detectar_rubro(df.columns),
        "propuestas": proponer_analisis(df, sug),
        "paises": PAISES,
        "motor": MOTOR_INFO,
        # Defaults aprendidos de corridas previas (rol/pais/unidad/horizonte)
        "aprendido": aprendizaje.defaults_sugeridos(DB.get_perfil(org_id) or {}),
    }


class ConfigValidar(BaseModel):
    token: str
    fecha: str
    valor: str
    serie: str | None = None
    granularidad: str | None = None      # diaria|semanal|quincenal|mensual|trimestral


# Cuántos periodos equivalen a ~3 meses en cada granularidad (para sugerir).
_TRES_MESES = {"diaria": 90, "semanal": 13, "quincenal": 6, "mensual": 3, "trimestral": 1}


@app.post("/api/validar")
def validar(cfg: ConfigValidar, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = _working(org_id, cfg.token)
    res, checks = prevalidar(ses["df"], cfg.fecha, cfg.valor, cfg.serie, cfg.granularidad)
    out = {"checks": [{"nivel": n, "mensaje": m} for n, m in checks]}
    if res is None:
        out["ok"] = False
        return out
    limpio, meta = res
    ses["limpio"], ses["meta"] = limpio, meta
    fnom, nativa = meta["freq_nombre"], meta["freq_nativa"]
    # Ofrecemos la granularidad nativa y todas las más gruesas: agregar sí,
    # desagregar no (no se puede inventar detalle que los datos no tienen).
    opciones = [g for g, (_, _, r) in GRANULARIDADES.items()
                if r >= GRANULARIDADES[nativa][2]]
    # El tope lo pone la historia disponible, no solo la estacionalidad: pedir
    # más de lo que los datos pueden validar rompía el entrenamiento.
    h_max = horizonte_maximo(limpio, meta)
    out.update(ok=True, frecuencia=fnom,
               frecuencia_plural=FREQ_PLURAL.get(fnom, fnom + "es"),
               horizonte_max=h_max,
               horizonte_sugerido=int(min(_TRES_MESES.get(fnom, 8), h_max)),
               granularidad=fnom, granularidad_nativa=nativa,
               granularidades=opciones,
               n_series=int(limpio["unique_id"].nunique()))
    if h_max < _TRES_MESES.get(fnom, 8):
        out["checks"].append({"nivel": "warn", "mensaje":
            f"Con {int(limpio.groupby('unique_id').size().min())} periodos de historia "
            f"puedo proyectar hasta {h_max}. Para llegar más lejos, agrupa en periodos "
            f"más grandes o carga más historia."})
    return out


class ConfigForecast(BaseModel):
    token: str
    horizonte: int
    rol: str = "gerente"            # gerente | analista | operaciones
    pais: str | None = "PE"
    unidad: str = "unidades"
    # Análisis limpio: ignora lo aprendido de corridas anteriores (memoria,
    # track record, perfil). Útil cuando el negocio cambió o se quiere una
    # segunda opinión sin sesgo de la historia.
    sin_memoria: bool = False


@app.post("/api/forecast")
def forecast(cfg: ConfigForecast, user=Depends(usuario_actual)):
    if cfg.rol not in ("gerente", "analista", "operaciones"):
        raise HTTPException(400, "Rol inválido.")
    org_id = DB.org_de_usuario(user["user_id"])
    # Tope de protección, NO monetización: cada corrida entrena 4 modelos.
    # Generoso a propósito — un usuario real nunca lo toca; frena bucles y abusos.
    if MAX_CORRIDAS_DIA and org_id:
        desde = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                                   microsecond=0).isoformat()
        if DB.corridas_desde(org_id, desde) >= MAX_CORRIDAS_DIA:
            raise HTTPException(429, f"Llegaste al máximo de {MAX_CORRIDAS_DIA} análisis "
                                     f"por día. Escríbenos si necesitas más.")
    ses = _working(org_id, cfg.token)
    if "limpio" not in ses:
        raise HTTPException(409, "Primero valida los datos (paso 2).")
    limpio, meta = ses["limpio"], ses["meta"]
    # Tope por historia disponible (no solo estacionalidad): ver horizonte_maximo.
    h = max(2, min(cfg.horizonte, horizonte_maximo(limpio, meta)))

    firma = (h,)
    if ses.get("firma") != firma:
        try:
            ses["resultados"] = entrenar_y_competir(limpio, meta, h)
        except Exception as e:   # noqa: BLE001 — el usuario nunca debe ver un 500
            log.error("entrenamiento falló | org=%s h=%s freq=%s series=%s: %s",
                      org_id, h, meta.get("freq_nombre"),
                      limpio["unique_id"].nunique(), e)
            raise HTTPException(422, f"No pude entrenar con esta configuración: {e}. "
                                     f"Prueba un horizonte más corto o agrupa los "
                                     f"periodos en unidades más grandes.")
        ses["firma"] = firma
    tabla, mejores, fc, cv = ses["resultados"]

    inf = generar_informe(limpio, meta, tabla, mejores, fc, cv,
                          rol=cfg.rol, pais=cfg.pais, unidad=cfg.unidad)
    # Fase 2: capacidad vs demanda desde la columna de stock, si el cliente la subió.
    cap_ins = capacidad.insight_capacidad(ses["df"], detectar_columnas(ses["df"]),
                                          fc, meta["season"], cfg.unidad)
    if cap_ins:
        inf["insights"].append(cap_ins)
    # --- Memoria: comparar con la historia ANTES de fundir esta corrida ---
    cfg_dict = {"rol": cfg.rol, "pais": cfg.pais, "horizonte": h, "unidad": cfg.unidad,
                "sin_memoria": cfg.sin_memoria}
    perfil = DB.get_perfil(org_id) or {}
    # Análisis limpio: el usuario pidió una lectura sin el contexto acumulado.
    inf["sin_memoria"] = cfg.sin_memoria
    inf["memoria"] = None if cfg.sin_memoria else aprendizaje.bloque_memoria(perfil, inf)

    # Precisión histórica: contrasta proyecciones ya emitidas contra lo real
    # (se evalúa ANTES de persistir esta corrida, para no compararse consigo misma).
    inf["precision"] = None if cfg.sin_memoria else \
        precision.evaluar(DB.informes_previos(org_id), limpio)

    # Comparación contra la proyección manual del equipo (FVA), si la subieron.
    inf["fva"] = fva.evaluar(ses["df"], detectar_columnas(ses["df"]), limpio, cv,
                             mejores, meta, cfg.unidad)

    # Asistente ejecutivo: decisiones + evidencia + confianza + riesgos + plan (determinista).
    rubro_nom = detectar_rubro(ses["df"].columns)["nombre"]
    inf["rubro"] = rubro_nom
    inf["asistente"] = asistente.construir(inf, rubro_nom,
                                           {} if cfg.sin_memoria else aprendizaje.resumen_perfil(perfil),
                                           inf["precision"], inf["fva"])
    ses["cfg"] = cfg_dict   # para re-narrar escenarios what-if sin re-entrenar
    DB.registrar_evento(org_id, "informe_generado",
                        {"rol": cfg.rol, "horizonte": h, "rubro": rubro_nom,
                         "n_series": int(inf["kpis"]["n_series"]),
                         "con_capacidad": bool(cap_ins),
                         "con_track_record": bool(inf["precision"])})
    log.info("informe generado | org=%s rubro=%s rol=%s h=%s series=%s error=%s%%",
             org_id, rubro_nom, cfg.rol, h, inf["kpis"]["n_series"], inf["kpis"]["wape_pct"])
    ses["informe"] = inf

    # Persistir la corrida (metadatos + informe jsonb) para el historial.
    corrida = DB.crear_corrida(org_id, cfg.token, cfg_dict)
    inf["corrida_id"] = corrida["id"]
    DB.guardar_informe(org_id, corrida["id"], inf)

    # --- Aprender: fundir esta corrida en el perfil del negocio ---
    rubro = detectar_rubro(ses["df"].columns)["nombre"]
    perfil_nuevo = aprendizaje.fundir_corrida(perfil, cfg_dict, inf, rubro, _ahora_iso())
    DB.guardar_perfil(org_id, perfil_nuevo)
    return inf


# ---------------------------------------------------------------------
# Medición de uso (etapa gratuita): ¿vuelve?, ¿qué usa?, ¿dónde abandona?
# ---------------------------------------------------------------------
# Lista blanca: el endpoint es superficie pública; no aceptamos tipos libres.
EVENTOS_VALIDOS = {
    "datos_subidos", "validacion_ok", "validacion_error", "informe_generado",
    "rol_cambiado", "porque_abierto", "escenario_simulado", "plan_generado",
    "insight_guardado", "descarga_excel", "correo_preview", "abandono",
}


class Evento(BaseModel):
    tipo: str
    meta: dict | None = None


@app.post("/api/evento")
def registrar_evento(ev: Evento, user=Depends(usuario_actual)):
    if ev.tipo not in EVENTOS_VALIDOS:
        raise HTTPException(400, "Tipo de evento no reconocido.")
    org_id = DB.org_de_usuario(user["user_id"])
    if org_id:
        # meta acotado: no queremos datos del negocio del cliente en telemetría.
        meta = {k: v for k, v in list((ev.meta or {}).items())[:8]
                if isinstance(v, (str, int, float, bool))}
        DB.registrar_evento(org_id, ev.tipo, meta)
    return {"ok": True}


@app.get("/api/uso")
def uso(user=Depends(usuario_actual)):
    """Resumen de uso de TU organización. Para la vista global de todos los
    clientes, consulta la tabla `eventos` en Supabase (no exponemos cross-org)."""
    org_id = DB.org_de_usuario(user["user_id"])
    if not org_id:
        return {"eventos": {}, "corridas": 0}
    evs = DB.eventos(org_id)
    conteo: dict = {}
    for e in evs:
        conteo[e["tipo"]] = conteo.get(e["tipo"], 0) + 1
    corridas = DB.historial(org_id)
    return {"eventos": conteo, "total_eventos": len(evs),
            "corridas": len(corridas),
            "dias_activos": len({(c.get("creado_en") or "")[:10] for c in corridas} - {""}),
            "ultimo": (corridas[0].get("creado_en") if corridas else None)}


@app.get("/api/historial")
def historial(user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    return {"corridas": DB.historial(org_id)}


@app.get("/api/descargar/{token}")
def descargar(token: str, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = WORKING.get(token)
    if not ses or "resultados" not in ses or (org_id and DB.get_dataset(org_id, token) is None):
        raise HTTPException(404, "No hay resultados para descargar.")
    tabla, mejores, fc, _ = ses["resultados"]
    inf = ses.get("informe", {})
    # El libro abre en un resumen ejecutivo; el detalle queda en hojas aparte.
    buf = io.BytesIO()
    excel.construir_libro(fc, tabla, inf).save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="informe_forecast.xlsx"'})


# ---------------------------------------------------------------------
# Escenario what-if (Fase 3): escala la demanda y re-narra, sin re-entrenar.
# El sistema NO afirma causas (Mundial, clima…): el usuario activa el factor.
# ---------------------------------------------------------------------
class ConfigEscenario(BaseModel):
    token: str
    factor_demanda: float = 0.0        # +0.20 = +20% de demanda proyectada


@app.post("/api/escenario")
def escenario(cfg: ConfigEscenario, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = _working(org_id, cfg.token)
    if "resultados" not in ses or "cfg" not in ses:
        raise HTTPException(409, "Genera el informe base antes de simular escenarios.")
    tabla, mejores, fc, cv = ses["resultados"]
    f = 1.0 + float(cfg.factor_demanda)
    fc2 = fc.copy()
    for c in ("Forecast", "Lo_80", "Hi_80"):
        if c in fc2:
            fc2[c] = fc2[c] * f
    c = ses["cfg"]
    inf = generar_informe(ses["limpio"], ses["meta"], tabla, mejores, fc2, cv,
                          rol=c["rol"], pais=c["pais"], unidad=c["unidad"])
    cap_ins = capacidad.insight_capacidad(ses["df"], detectar_columnas(ses["df"]),
                                          fc2, ses["meta"]["season"], c["unidad"])
    if cap_ins:
        inf["insights"].append(cap_ins)
    rubro_nom = detectar_rubro(ses["df"].columns)["nombre"]
    inf["rubro"] = rubro_nom
    inf["precision"] = (ses.get("informe") or {}).get("precision")   # ya evaluada en la corrida base
    inf["asistente"] = asistente.construir(inf, rubro_nom,
                                           aprendizaje.resumen_perfil(DB.get_perfil(org_id) or {}),
                                           inf["precision"])
    inf["escenario"] = {"factor_demanda": cfg.factor_demanda}
    return inf   # no se persiste: es una simulación


# ---------------------------------------------------------------------
# Plan operativo por fecha (meta -> volumen por fecha + personal por turno)
# ---------------------------------------------------------------------
class ConfigPlan(BaseModel):
    token: str
    metodo: str = "lineal"                 # lineal | erlang
    # lineal
    meta: float | None = None
    productividad: float | None = None
    turnos: int = 1
    # erlang (BPO/colas)
    aht_seg: float | None = None
    intervalo_seg: float = 1800
    nivel_servicio: float = 0.8
    tiempo_objetivo_seg: float = 20
    shrinkage: float = 0.0


def _plan_de_sesion(org_id: str, cfg: ConfigPlan) -> tuple[dict, dict]:
    """Recalcula el plan desde la sesión (no se confía en el cliente) y lo guarda."""
    ses = _working(org_id, cfg.token)
    if "resultados" not in ses or "meta" not in ses:
        raise HTTPException(409, "Primero genera el informe (paso 3) antes del plan.")
    _, _, fc, _ = ses["resultados"]
    unidad = (ses.get("informe", {}).get("kpis", {}) or {}).get("unidad", "unidades")
    if cfg.metodo == "erlang":
        if not cfg.aht_seg or cfg.aht_seg <= 0:
            raise HTTPException(400, "Erlang necesita el AHT (tiempo medio de atención) en segundos.")
        p = plan_mod.generar_plan_erlang(fc, cfg.aht_seg, cfg.intervalo_seg,
                                         cfg.nivel_servicio, cfg.tiempo_objetivo_seg,
                                         cfg.shrinkage, unidad)
    else:
        if not cfg.meta or not cfg.productividad:
            raise HTTPException(400, "El plan lineal necesita meta y productividad.")
        p = plan_mod.generar_plan(ses["limpio"], fc, ses["meta"]["freq"],
                                  cfg.meta, cfg.productividad, cfg.turnos, unidad)
    ses["plan"] = p
    return p, ses


@app.post("/api/plan")
def crear_plan(cfg: ConfigPlan, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    p, _ = _plan_de_sesion(org_id, cfg)
    return p


@app.get("/api/plan/descargar/{token}")
def descargar_plan(token: str, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = WORKING.get(token)
    if not ses or "plan" not in ses or (org_id and DB.get_dataset(org_id, token) is None):
        raise HTTPException(404, "No hay un plan generado para descargar.")
    p = ses["plan"]
    df = pd.DataFrame(p["filas"])
    # Resumen genérico: todos los escalares del plan (sirve para lineal y erlang).
    resumen = pd.DataFrame(
        [{"campo": k, "valor": (v.get("mensaje") if isinstance(v, dict) else v)}
         for k, v in p.items() if k != "filas"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="plan_por_fecha", index=False)
        resumen.to_excel(xw, sheet_name="resumen", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="plan_operativo.xlsx"'})


# ---------------------------------------------------------------------
# Correo del informe + plan
# ---------------------------------------------------------------------
class ConfigCorreo(BaseModel):
    token: str
    destino: str
    asunto: str | None = None
    incluir_plan: bool = True


@app.post("/api/correo")
def enviar_correo(cfg: ConfigCorreo, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = _working(org_id, cfg.token)
    inf = ses.get("informe")
    if not inf:
        raise HTTPException(409, "Genera el informe antes de enviarlo por correo.")
    p = ses.get("plan") if cfg.incluir_plan else None
    nombre = (((DB.get_perfil(org_id) or {}).get("identidad") or {}).get("nombre")
              if org_id else None)
    html = correo_mod.construir_html(inf, p, nombre)
    asunto = cfg.asunto or f"Tu proyección: {inf.get('kpis', {}).get('total_fmt', '')} " \
                           f"{inf.get('kpis', {}).get('unidad', '')}"
    res = correo_mod.enviar(cfg.destino, asunto, html)
    return {**res, "asunto": asunto, "html": html,
            "proveedor_configurado": correo_mod.proveedor() is not None}


@app.get("/api/plantilla")
def plantilla(extendida: bool = False):
    """Plantilla Excel con datos de ejemplo (sirve también para probar la app)."""
    rng = np.random.default_rng(7)
    fechas = pd.date_range("2025-01-05", periods=72, freq="W-SUN")
    filas = []
    for serie, base, amp in [("Producto A", 120, 35), ("Producto B", 60, 18)]:
        est = amp * np.sin(np.arange(72) * 2 * np.pi / 52)
        tend = np.linspace(0, base * 0.15, 72)
        vals = np.clip(base + est + tend + rng.normal(0, base * 0.07, 72), 0, None)
        for f, v in zip(fechas, vals):
            fila = {"fecha": f.date(), "serie": serie, "valor": round(float(v), 1)}
            if extendida:
                fila["stock"] = round(float(v) * rng.uniform(1.5, 3.0), 0)
                # Proyección que habría hecho el equipo a mano: sirve para que la
                # app compare "tu gente vs el modelo" (FVA) sobre lo ya ocurrido.
                fila["proyeccion_manual"] = round(float(v) * rng.uniform(0.82, 1.22), 1)
            filas.append(fila)
    df = pd.DataFrame(filas)
    instr = pd.DataFrame({"instrucciones": [
        "fecha: una fila por periodo (día, semana o mes — la app detecta la frecuencia).",
        "serie: opcional — cliente, producto, mercado, campaña… Borra la columna si solo tienes un total.",
        "valor: la métrica numérica que quieres proyectar (ventas, kg, horas…).",
        "stock: opcional (plantilla extendida) — capacidad o inventario disponible por periodo." if extendida else
        "¿Manejas inventario o capacidad? Descarga la plantilla extendida para incluir 'stock'.",
        "proyeccion_manual: opcional — lo que tu equipo proyectó a mano para ese periodo. "
        "Si la llenas, la app compara quién acertó más: tu gente o el modelo." if extendida else
        "¿Tu equipo ya hace proyecciones a mano? La plantilla extendida trae "
        "'proyeccion_manual' para comparar quién acierta más.",
        "Reemplaza los datos de ejemplo por los tuyos y sube el archivo a la app.",
    ]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        df.to_excel(xw, sheet_name="datos", index=False)
        instr.to_excel(xw, sheet_name="leeme", index=False)
    buf.seek(0)
    nombre = "plantilla_forecast_extendida.xlsx" if extendida else "plantilla_forecast.xlsx"
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.exception_handler(Exception)
async def _registrar_fallo(request, exc):
    """Todo error no controlado queda registrado con su ruta, para poder
    diagnosticarlo después. El usuario recibe un mensaje limpio, no la traza."""
    log.exception("FALLO en %s %s: %s", request.method, request.url.path, exc)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={
        "detail": "Algo falló de nuestro lado. Ya quedó registrado; "
                  "vuelve a intentarlo en un momento."})


@app.middleware("http")
async def _sin_cache_html(request, call_next):
    """El HTML lleva la app entera embebida: si el navegador lo cachea, el
    cliente se queda con una versión vieja tras cada despliegue."""
    resp = await call_next(request)
    if resp.headers.get("content-type", "").startswith("text/html"):
        resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8602)
