# =====================================================================
# Plan operativo por fecha.
# Convierte una META que ingresa el gerente en valores por fecha,
# usando el patrón estacional ya presente en la historia, y estima el
# personal por turno. Compara la meta contra la proyección del modelo
# (pacing): ¿es agresiva, holgada o realista?
# =====================================================================
import math

import numpy as np
import pandas as pd


def _pesos_estacionales(limpio: pd.DataFrame, freq: str) -> pd.Series:
    """Peso relativo de cada 'casillero' de calendario (día de semana si la
    serie es diaria; mes en otro caso), a partir del promedio histórico."""
    d = limpio.copy()
    d["k"] = d["ds"].dt.dayofweek if freq == "D" else d["ds"].dt.month
    pesos = d.groupby("k")["y"].mean()
    return pesos[pesos > 0]


def generar_plan(limpio: pd.DataFrame, forecast: pd.DataFrame, freq: str,
                 meta: float, productividad: float, turnos: int,
                 unidad: str = "unidades") -> dict:
    """Devuelve el plan por fecha + el bloque de pacing, JSON-listo."""
    meta = max(float(meta), 0.0)
    productividad = max(float(productividad), 1e-9)
    turnos = max(int(turnos), 1)

    # Total proyectado por fecha (sumando todas las series del negocio).
    fc = forecast.groupby("ds")["Forecast"].sum().sort_index()
    fechas = list(fc.index)
    proy = fc.values.astype(float)

    # Reparto de la meta proporcional al patrón estacional de cada fecha.
    pesos_map = _pesos_estacionales(limpio, freq)
    media_peso = float(pesos_map.mean()) if len(pesos_map) else 1.0
    claves = [d.dayofweek if freq == "D" else d.month for d in fechas]
    pesos = np.array([float(pesos_map.get(k, media_peso)) for k in claves])
    pesos = np.where(np.isfinite(pesos) & (pesos > 0), pesos, media_peso)
    share = pesos / pesos.sum() if pesos.sum() > 0 else np.full(len(pesos), 1 / len(pesos))
    objetivo = meta * share

    filas = []
    for i, fch in enumerate(fechas):
        vol = float(objetivo[i])
        person_turnos = math.ceil(vol / productividad)          # esfuerzo total
        personas_turno = math.ceil(person_turnos / turnos)      # cabezas por turno
        filas.append({
            "fecha": str(pd.Timestamp(fch).date()),
            "volumen_objetivo": round(vol, 1),
            "proyeccion": round(float(proy[i]), 1),
            "person_turnos": person_turnos,
            "personas_turno": personas_turno,
        })

    proy_total = float(proy.sum())
    diff_pct = 100 * (meta - proy_total) / max(proy_total, 1e-9)
    pico = max(filas, key=lambda f: f["personas_turno"]) if filas else None

    if diff_pct > 10:
        nivel, msg = "agresiva", (
            f"Tu meta de {_fmt(meta)} {unidad} está {diff_pct:+.0f}% por encima de lo que el "
            f"modelo proyecta ({_fmt(proy_total)}). Es una meta exigente: para alcanzarla harás "
            f"falta sostener un ritmo mayor al esperado — asegura el personal del/los día(s) pico.")
    elif diff_pct < -10:
        nivel, msg = "holgada", (
            f"Tu meta de {_fmt(meta)} {unidad} está {abs(diff_pct):.0f}% por debajo de lo proyectado "
            f"({_fmt(proy_total)}): tienes holgura. Puedes ajustar personal a la baja o subir la meta.")
    else:
        nivel, msg = "realista", (
            f"Tu meta de {_fmt(meta)} {unidad} está en línea con la proyección del modelo "
            f"({_fmt(proy_total)}, {diff_pct:+.0f}%): es un plan realista con el ritmo actual.")

    return {
        "meta": round(meta, 1), "meta_fmt": _fmt(meta), "unidad": unidad,
        "productividad": productividad, "turnos": turnos,
        "n_fechas": len(filas),
        "rango_fechas": [filas[0]["fecha"], filas[-1]["fecha"]] if filas else None,
        "proy_total": round(proy_total, 1), "proy_total_fmt": _fmt(proy_total),
        "diff_pct": round(diff_pct, 1),
        "pacing": {"nivel": nivel, "mensaje": msg},
        "personas_pico": pico["personas_turno"] if pico else 0,
        "fecha_pico": pico["fecha"] if pico else None,
        "filas": filas,
    }


def _fmt(x: float) -> str:
    """Miles con espacio fino, sin decimales — coherente con el resto del informe."""
    return f"{round(x):,}".replace(",", " ")
