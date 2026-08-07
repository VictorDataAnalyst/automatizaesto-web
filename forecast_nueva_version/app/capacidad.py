# =====================================================================
# Capacidad vs demanda (Fase 2).
# Cruza la demanda proyectada contra la capacidad/inventario disponible
# (columna 'stock' que ya se sube en la plantilla extendida) y detecta
# los periodos donde la demanda supera la capacidad — el "vas corto de
# packing" para agro, el "quiebre de stock" para retail.
# ponytail: capacidad futura = mediana histórica del stock por serie.
# Baseline simple; si el cliente quiere fijarla a mano, se agrega un input.
# =====================================================================
import pandas as pd

STOCK_KEYS = ("stock", "inventario", "existencia", "capacidad", "cupo", "disponible")


def _col_stock(columnas):
    for c in columnas:
        if any(k in str(c).lower() for k in STOCK_KEYS):
            return c
    return None


def _fmt(x: float) -> str:
    return f"{round(x):,}".replace(",", " ")


def insight_capacidad(df: pd.DataFrame, sug: dict, forecast: pd.DataFrame,
                      season: int, unidad: str = "unidades") -> dict | None:
    """Devuelve un insight {id:'capacidad', ...} o None si no hay columna de stock."""
    col = _col_stock(df.columns)
    if col is None:
        return None
    scol = sug.get("serie")
    d = df[[col] + ([scol] if scol else [])].copy()
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=[col])
    if d.empty:
        return None

    cap_scalar = float(d[col].median())
    cap_serie = d.groupby(scol)[col].median() if scol else None

    def cap_de(uid):
        if cap_serie is not None and uid in cap_serie.index:
            return float(cap_serie[uid])
        return cap_scalar

    filas = [(r["unique_id"], pd.Timestamp(r["ds"]).date(),
              float(r["Forecast"]), cap_de(r["unique_id"]))
             for _, r in forecast.iterrows()]
    filas = [(uid, f, dem, cap, dem - cap) for uid, f, dem, cap in filas]

    n_total = len(filas)
    excede = [x for x in filas if x[4] > 0]
    peor = max(filas, key=lambda x: x[4]) if filas else None
    deficit_total = sum(x[4] for x in excede)

    if excede:
        cifra = f"{len(excede)} en riesgo"
        resumen = (f"Proyectas superar tu capacidad disponible en {len(excede)} de {n_total} "
                   f"periodos; el más ajustado: {peor[0]} el {peor[1]}, faltarían "
                   f"{_fmt(peor[4])} {unidad}.")
        brief = (f"Vas corto de capacidad en {len(excede)} periodo(s) (déficit total "
                 f"~{_fmt(deficit_total)} {unidad}): adelanta producción, suma turno o "
                 f"reprograma entregas antes del {peor[1]}.")
        detalle = ("Comparamos la demanda proyectada por periodo contra tu capacidad "
                   f"disponible (mediana histórica de «{col}» por serie). Periodos más "
                   "ajustados: " + "; ".join(
                       f"{u} {f}: demanda {_fmt(dem)} vs {_fmt(cap)} ({_fmt(dm)} de más)"
                       for u, f, dem, cap, dm in sorted(excede, key=lambda x: -x[4])[:3]) + ".")
    else:
        cifra = "sin riesgo"
        resumen = (f"Tu capacidad disponible cubre toda la demanda proyectada en los "
                   f"{n_total} periodos. Sin riesgo de quiebre.")
        brief = (f"Capacidad holgada: cubres la demanda de los {n_total} periodos. "
                 "Puedes subir la meta o liberar recursos.")
        detalle = (f"En ningún periodo la demanda proyectada supera tu capacidad disponible "
                   f"(mediana histórica de «{col}» por serie). Margen para crecer o reasignar.")

    dem_total = sum(x[2] for x in filas)
    cap_total = sum(x[3] for x in filas)
    return {"id": "capacidad", "icono": "🏭", "titulo": "Capacidad vs demanda",
            "cifra": cifra, "resumen": resumen, "brief": brief,
            "detalle": detalle, "chart": None,
            "datos": {"demanda_total": round(dem_total, 1),
                      "capacidad_total": round(cap_total, 1),
                      "deficit_total": round(deficit_total, 1),
                      "n_excede": len(excede), "n_total": n_total,
                      "fecha_pico": peor[1].isoformat() if peor and peor[4] > 0 else None,
                      "unidad": unidad, "col": str(col)}}


if __name__ == "__main__":  # ponytail: check de la lógica no trivial
    import numpy as np
    # serie A con capacidad ~100, demanda proyectada 130 -> corto; B holgado
    df = pd.DataFrame({"serie": ["A"] * 10 + ["B"] * 10,
                       "stock": [100] * 10 + [500] * 10})
    fc = pd.DataFrame({"unique_id": ["A", "A", "B"],
                       "ds": pd.to_datetime(["2026-07-05", "2026-07-12", "2026-07-05"]),
                       "Forecast": [130.0, 90.0, 200.0]})
    ins = insight_capacidad(df, {"serie": "serie"}, fc, 8, "contenedores")
    assert ins and ins["id"] == "capacidad"
    assert "1 en riesgo" in ins["cifra"], ins["cifra"]        # solo A semana 1 excede
    assert "Vas corto" in ins["brief"]
    # sin columna de stock -> None
    assert insight_capacidad(pd.DataFrame({"serie": ["A"], "valor": [1]}),
                             {"serie": "serie"}, fc, 8) is None
    print("capacidad OK:", ins["cifra"])
