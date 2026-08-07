# =====================================================================
# Precisión histórica — cierra el loop del forecast.
# Contrasta las proyecciones que YA emitimos contra lo que realmente
# pasó (los datos que el cliente subió después). Responde la pregunta
# que da confianza: "¿cómo te fue la última vez?".
# ponytail: reutiliza el informe jsonb ya persistido (chart_principal
# guarda fecha+valor de cada proyección). Sin tabla nueva.
# =====================================================================
import pandas as pd

SUF = " · proyección"


def _proyecciones(informe: dict):
    """(uid, fecha_str, valor) de cada punto proyectado de un informe."""
    chart = (informe or {}).get("chart_principal") or {}
    for s in chart.get("series", []):
        if not s.get("banda_lo"):          # solo las series de proyección
            continue
        uid = s.get("nombre", "").replace(SUF, "")
        for f, v in zip(s.get("x", []), s.get("y", [])):
            yield uid, str(f)[:10], float(v)


def evaluar(previos: list, limpio: pd.DataFrame) -> dict | None:
    """`previos` = corridas con informe (más reciente primero).
    `limpio` = datos reales actuales (unique_id, ds, y).
    Devuelve el contraste, o None si aún no hay nada comparable."""
    if limpio is None or limpio.empty or not previos:
        return None

    reales = {}
    for r in limpio.itertuples(index=False):
        reales[(str(r.unique_id), str(pd.Timestamp(r.ds).date()))] = float(r.y)

    corridas, err_abs, tot_real, n_pts = [], 0.0, 0.0, 0
    for c in previos:
        pares = [(v, reales[(uid, f)])
                 for uid, f, v in _proyecciones(c.get("informe"))
                 if (uid, f) in reales]
        if not pares:
            continue                        # esa corrida aún no tiene realidad encima
        e = sum(abs(p - a) for p, a in pares)
        t = sum(abs(a) for p, a in pares)
        wape = 100 * e / t if t else 0.0
        sesgo = 100 * sum(p - a for p, a in pares) / t if t else 0.0
        corridas.append({"corrida_id": c.get("id"),
                         "fecha": str(c.get("creado_en") or "")[:10],
                         "n_puntos": len(pares),
                         "wape": round(wape, 1), "sesgo": round(sesgo, 1)})
        err_abs += e
        tot_real += t
        n_pts += len(pares)

    if not corridas:
        return None

    wape_global = round(100 * err_abs / tot_real, 1) if tot_real else 0.0
    ult = corridas[0]
    tendencia = None
    if len(corridas) >= 2:
        prev = sum(c["wape"] for c in corridas[1:]) / len(corridas[1:])
        if abs(ult["wape"] - prev) >= 1:
            tendencia = "mejorando" if ult["wape"] < prev else "empeorando"

    dir_ = ("sobreestimé" if ult["sesgo"] > 5 else
            "subestimé" if ult["sesgo"] < -5 else None)
    frase = (f"Mi último pronóstico falló {ult['wape']:.1f}% contra lo que realmente pasó "
             f"({ult['n_puntos']} periodos ya verificados).")
    if dir_:
        frase += f" Tendí a {dir_[:-1]}ar ({abs(ult['sesgo']):.0f}%)."

    return {"wape_ultima": ult["wape"], "sesgo_ultima": ult["sesgo"],
            "n_puntos_ultima": ult["n_puntos"], "wape_global": wape_global,
            "n_corridas": len(corridas), "n_puntos": n_pts,
            "tendencia": tendencia, "frase": frase, "corridas": corridas}


if __name__ == "__main__":  # ponytail: check de la lógica no trivial
    inf = {"chart_principal": {"series": [
        {"nombre": "A · histórico", "x": ["2026-01-04"], "y": [90]},          # sin banda: se ignora
        {"nombre": "A · proyección", "x": ["2026-02-01", "2026-02-08"],
         "y": [100.0, 200.0], "banda_lo": [90, 180], "banda_hi": [110, 220]},
    ]}}
    previos = [{"id": "c1", "creado_en": "2026-01-20T10:00:00Z", "informe": inf}]
    # real: 110 y 180  -> |100-110| + |200-180| = 30 sobre 290 => 10.3%
    limpio = pd.DataFrame({"unique_id": ["A", "A"],
                           "ds": pd.to_datetime(["2026-02-01", "2026-02-08"]),
                           "y": [110.0, 180.0]})
    r = evaluar(previos, limpio)
    assert r and r["n_puntos_ultima"] == 2, r
    assert r["wape_ultima"] == 10.3, r["wape_ultima"]
    assert "10.3%" in r["frase"], r["frase"]
    # sin realidad encima (proyección aún futura) -> None
    futuro = pd.DataFrame({"unique_id": ["A"], "ds": pd.to_datetime(["2025-12-01"]), "y": [50.0]})
    assert evaluar(previos, futuro) is None
    # sin historia -> None
    assert evaluar([], limpio) is None
    print("precision OK:", r["frase"])
