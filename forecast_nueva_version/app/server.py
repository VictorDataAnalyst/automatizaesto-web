# =====================================================================
# FORECAST — backend FastAPI con frontend propio
# Reutiliza el motor validado de files/app_forecast_universal.py.
# Ejecutar:  python server.py   (abre http://localhost:8602)
# =====================================================================
import io
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
                                    entrenar_y_competir, MOTOR_INFO)
from informe import generar_informe, PAISES, FREQ_PLURAL             # noqa: E402
import config                                                         # noqa: E402
import aprendizaje                                                     # noqa: E402
from auth import usuario_actual                                       # noqa: E402
from db import DB                                                     # noqa: E402


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
class Identidad(BaseModel):
    nombre: str | None = None
    negocio: str | None = None


@app.post("/api/identidad")
def set_identidad(idn: Identidad, user=Depends(usuario_actual)):
    """El usuario 'ingresa su información'. Se guarda en su perfil de org."""
    org_id = _org_de(user)
    perfil = {**aprendizaje.perfil_vacio(), **(DB.get_perfil(org_id) or {})}
    perfil["identidad"] = {
        "nombre": idn.nombre or (perfil.get("identidad") or {}).get("nombre")
                  or user.get("email"),
        "negocio": idn.negocio or (perfil.get("identidad") or {}).get("negocio"),
    }
    perfil["actualizado_en"] = _ahora_iso()
    DB.guardar_perfil(org_id, perfil)
    return {"ok": True, "identidad": perfil["identidad"]}


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
    crudo = await archivo.read()
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


@app.post("/api/validar")
def validar(cfg: ConfigValidar, user=Depends(usuario_actual)):
    org_id = DB.org_de_usuario(user["user_id"])
    ses = _working(org_id, cfg.token)
    res, checks = prevalidar(ses["df"], cfg.fecha, cfg.valor, cfg.serie)
    out = {"checks": [{"nivel": n, "mensaje": m} for n, m in checks]}
    if res is None:
        out["ok"] = False
        return out
    limpio, meta = res
    ses["limpio"], ses["meta"] = limpio, meta
    out.update(ok=True, frecuencia=meta["freq_nombre"],
               frecuencia_plural=FREQ_PLURAL.get(meta["freq_nombre"],
                                                 meta["freq_nombre"] + "es"),
               horizonte_max=int(meta["season"]),
               horizonte_sugerido=int(min(16, meta["season"])),
               n_series=int(limpio["unique_id"].nunique()))
    return out


class ConfigForecast(BaseModel):
    token: str
    horizonte: int
    rol: str = "gerente"            # gerente | analista | operaciones
    pais: str | None = "PE"
    unidad: str = "unidades"


@app.post("/api/forecast")
def forecast(cfg: ConfigForecast, user=Depends(usuario_actual)):
    if cfg.rol not in ("gerente", "analista", "operaciones"):
        raise HTTPException(400, "Rol inválido.")
    org_id = DB.org_de_usuario(user["user_id"])
    ses = _working(org_id, cfg.token)
    if "limpio" not in ses:
        raise HTTPException(409, "Primero valida los datos (paso 2).")
    limpio, meta = ses["limpio"], ses["meta"]
    h = max(2, min(cfg.horizonte, meta["season"]))

    firma = (h,)
    if ses.get("firma") != firma:
        ses["resultados"] = entrenar_y_competir(limpio, meta, h)
        ses["firma"] = firma
    tabla, mejores, fc, cv = ses["resultados"]

    inf = generar_informe(limpio, meta, tabla, mejores, fc, cv,
                          rol=cfg.rol, pais=cfg.pais, unidad=cfg.unidad)

    # --- Memoria: comparar con la historia ANTES de fundir esta corrida ---
    cfg_dict = {"rol": cfg.rol, "pais": cfg.pais, "horizonte": h, "unidad": cfg.unidad}
    perfil = DB.get_perfil(org_id) or {}
    inf["memoria"] = aprendizaje.bloque_memoria(perfil, inf)
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
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        fc.rename(columns={"unique_id": "serie", "ds": "periodo", "Forecast": "proyeccion",
                           "Lo_80": "piso_80", "Hi_80": "techo_80"}).to_excel(
            xw, sheet_name="proyeccion", index=False)
        tabla.rename(columns={"WAPE_%": "error_WAPE_pct", "BIAS_%": "sesgo_pct"}).to_excel(
            xw, sheet_name="metricas", index=False)
        if inf.get("insights"):
            pd.DataFrame([{"hallazgo": f"{i+1}. {x['titulo']}",
                           "resumen": x["resumen"], "detalle": x["detalle"]}
                          for i, x in enumerate(inf["insights"])]).to_excel(
                xw, sheet_name="hallazgos", index=False)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="informe_forecast.xlsx"'})


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
            filas.append(fila)
    df = pd.DataFrame(filas)
    instr = pd.DataFrame({"instrucciones": [
        "fecha: una fila por periodo (día, semana o mes — la app detecta la frecuencia).",
        "serie: opcional — cliente, producto, mercado, campaña… Borra la columna si solo tienes un total.",
        "valor: la métrica numérica que quieres proyectar (ventas, kg, horas…).",
        "stock: opcional (plantilla extendida) — inventario disponible por periodo." if extendida else
        "¿Manejas inventario? Descarga la plantilla extendida para incluir 'stock'.",
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


app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8602)
