# =====================================================================
# FVA — Forecast Value Added (estándar del sector: IBF, o9, Lokad).
# Responde: "¿qué habría pasado si usaba la proyección que mandó mi equipo?"
# Compara, sobre los MISMOS periodos y contra lo que realmente pasó:
#   proyección manual  vs  modelo  vs  naive (repetir la temporada anterior)
# Si el humano gana, se dice claro y se recomienda seguirlo. El sistema no
# está para tener la razón, está para que el cliente decida mejor.
#
# El plan manual se lee de una columna del MISMO archivo (plan / presupuesto /
# proyeccion_manual…), así no hace falta un flujo de carga aparte.
# =====================================================================
import numpy as np
import pandas as pd

CLAVES_MANUAL = ("proyeccion_manual", "pronostico_manual", "forecast_manual",
                 "plan", "presupuesto", "meta_equipo", "manual")


def _col_manual(columnas):
    cols = {str(c).lower().strip(): c for c in columnas}
    for clave in CLAVES_MANUAL:
        for baja, orig in cols.items():
            if clave in baja:
                return orig
    return None


def _wape(y, yhat) -> float:
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    tot = np.abs(y).sum()
    return float(100 * np.abs(y - yhat).sum() / tot) if tot else 0.0


def evaluar(df: pd.DataFrame, sug: dict, limpio: pd.DataFrame, cv: pd.DataFrame,
            mejores: dict, meta: dict, unidad: str = "unidades") -> dict | None:
    """None si el cliente no subió columna de proyección manual."""
    col = _col_manual(df.columns)
    if col is None or cv is None or cv.empty:
        return None
    fcol, scol = sug.get("fecha"), sug.get("serie")
    if not fcol:
        return None

    d = df[[fcol, col] + ([scol] if scol else [])].copy()
    d[col] = pd.to_numeric(d[col], errors="coerce")
    d[fcol] = pd.to_datetime(d[fcol], errors="coerce")
    d = d.dropna(subset=[fcol, col])
    if d.empty:
        return None
    d["unique_id"] = d[scol].astype(str) if scol else "TOTAL"

    # Agregar el plan manual a la MISMA granularidad con la que se modeló.
    partes = []
    for uid, g in d.groupby("unique_id"):
        g = g.set_index(fcol).sort_index()[[col]].resample(meta["freq"]).sum()
        g = g.reset_index()
        g.columns = ["ds", "manual"]
        g["unique_id"] = uid
        partes.append(g)
    manual = pd.concat(partes)

    # Cruzar con la validación del modelo: mismos periodos, misma realidad.
    j = cv.merge(manual, on=["unique_id", "ds"], how="inner")
    j = j[j["manual"] > 0]
    if len(j) < 3:
        return None

    filas, e_mod, e_man, e_nai, tot = [], 0.0, 0.0, 0.0, 0.0
    for uid, g in j.groupby("unique_id"):
        pred = g[mejores[uid]].mean(axis=1) if uid in mejores else g.iloc[:, 3]
        w_mod, w_man = _wape(g["y"], pred), _wape(g["y"], g["manual"])
        w_nai = _wape(g["y"], g["SeasonalNaive"]) if "SeasonalNaive" in g else None
        filas.append({"serie": str(uid), "n_periodos": int(len(g)),
                      "wape_modelo": round(w_mod, 1), "wape_manual": round(w_man, 1),
                      "wape_naive": round(w_nai, 1) if w_nai is not None else None,
                      "gana": "modelo" if w_mod < w_man else "manual"})
        t = float(np.abs(g["y"]).sum())
        e_mod += w_mod * t / 100
        e_man += w_man * t / 100
        e_nai += (w_nai or 0) * t / 100
        tot += t

    w_mod = round(100 * e_mod / tot, 1) if tot else 0.0
    w_man = round(100 * e_man / tot, 1) if tot else 0.0
    w_nai = round(100 * e_nai / tot, 1) if tot else 0.0
    fva_vs_manual = round(w_man - w_mod, 1)          # + = el modelo aporta
    fva_vs_naive = round(w_nai - w_mod, 1)

    if fva_vs_manual > 1:
        gana, titulo = "modelo", "El modelo mejora la proyección de tu equipo"
        mensaje = (f"Sobre los mismos {int(j.groupby('unique_id').size().sum())} periodos ya "
                   f"ocurridos, tu plan manual se equivocó {w_man}% y el modelo {w_mod}%. "
                   f"Usar el modelo te habría acercado {fva_vs_manual} puntos a la realidad.")
        accion = "Usa la proyección del modelo como base y ajústala con tu criterio."
    elif fva_vs_manual < -1:
        gana, titulo = "manual", "Tu equipo pronostica mejor que el modelo"
        mensaje = (f"Sobre los mismos periodos, tu plan manual se equivocó {w_man}% y el "
                   f"modelo {w_mod}%. Tu equipo sabe algo que los datos no muestran.")
        accion = ("Sigue tu plan manual y cuéntanos qué información usan "
                  "(promociones, clientes, clima): con esa columna el modelo puede aprenderlo.")
    else:
        gana, titulo = "empate", "Tu equipo y el modelo pronostican casi igual"
        mensaje = (f"Ambos se equivocan parecido ({w_man}% manual vs {w_mod}% modelo). "
                   f"El modelo te ahorra el tiempo de armarlo a mano.")
        accion = "Automatiza con el modelo y usa tu tiempo en decidir, no en calcular."

    return {"col_manual": str(col), "gana": gana, "titulo": titulo,
            "mensaje": mensaje, "accion": accion,
            "wape_modelo": w_mod, "wape_manual": w_man, "wape_naive": w_nai,
            "fva_vs_manual": fva_vs_manual, "fva_vs_naive": fva_vs_naive,
            "unidad": unidad, "series": filas}


if __name__ == "__main__":  # ponytail: check de la lógica no trivial
    n = 12
    ds = pd.date_range("2026-01-01", periods=n, freq="MS")
    real = np.array([100, 110, 105, 120, 130, 125, 140, 135, 150, 145, 160, 155], float)
    cv = pd.DataFrame({"unique_id": "A", "ds": ds, "y": real,
                       "AutoETS": real * 1.02,          # modelo casi perfecto
                       "SeasonalNaive": real * 1.20})
    df = pd.DataFrame({"fecha": ds, "serie": "A", "valor": real,
                       "plan": real * 1.15})            # manual peor que el modelo
    r = evaluar(df, {"fecha": "fecha", "serie": "serie"}, None, cv, {"A": ["AutoETS"]},
                {"freq": "MS"}, "kg")
    assert r and r["gana"] == "modelo", r
    assert r["wape_modelo"] < r["wape_manual"] and r["fva_vs_manual"] > 0
    # ahora el manual es mejor -> el sistema debe admitirlo
    df["plan"] = real * 1.01
    cv["AutoETS"] = real * 1.18
    r2 = evaluar(df, {"fecha": "fecha", "serie": "serie"}, None, cv, {"A": ["AutoETS"]},
                 {"freq": "MS"}, "kg")
    assert r2["gana"] == "manual", r2
    assert "sabe algo que los datos no muestran" in r2["mensaje"]
    # sin columna manual -> None
    assert evaluar(df[["fecha", "serie", "valor"]], {"fecha": "fecha", "serie": "serie"},
                   None, cv, {"A": ["AutoETS"]}, {"freq": "MS"}) is None
    print("fva OK | modelo:", r["wape_modelo"], "% vs manual:", r["wape_manual"],
          "% | FVA:", r["fva_vs_manual"], "pts")
