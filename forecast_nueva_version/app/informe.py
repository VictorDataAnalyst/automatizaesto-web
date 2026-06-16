# =====================================================================
# INFORME EJECUTIVO — generación de insights en español, por rol
# El motor de modelos vive en files/app_forecast_universal.py; aquí solo
# se interpreta y narra. Todo serializable a JSON (sin objetos plotly).
# =====================================================================
import numpy as np
import pandas as pd

DIAS_ES = {"Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles",
           "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado",
           "Sunday": "domingo"}
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

PAISES = {"PE": "Perú", "CO": "Colombia", "MX": "México", "CL": "Chile",
          "EC": "Ecuador", "BO": "Bolivia", "AR": "Argentina", "ES": "España"}

# "periodos diarios / semanales / mensuales / trimestrales"
FREQ_PLURAL = {"diaria": "diarios", "semanal": "semanales",
               "mensual": "mensuales", "trimestral": "trimestrales"}


def fecha_es(d) -> str:
    d = pd.Timestamp(d)
    return f"{d.day} de {MESES_ES[d.month - 1]} de {d.year}"


def _num(x):
    """numpy -> tipos nativos para JSON."""
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    return x


def _fmt(x):
    return f"{x:,.0f}".replace(",", " ")  # 12 345 (espacio fino, neutro es/en)


def wape(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(np.abs(y - yhat)) / max(np.sum(np.abs(y)), 1e-9)


def bias_pct(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(yhat - y) / max(np.sum(np.abs(y)), 1e-9)


# ---------------------------------------------------------------------
# Feriados
# ---------------------------------------------------------------------
def feriados_rango(pais: str, desde, hasta) -> list:
    """Lista [(fecha, nombre)] de feriados del país entre dos fechas."""
    try:
        import holidays as _hol
        desde, hasta = pd.Timestamp(desde), pd.Timestamp(hasta)
        anios = list(range(desde.year, hasta.year + 1))
        cal = _hol.country_holidays(pais, years=anios, language="es")
        out = [(pd.Timestamp(f), n) for f, n in sorted(cal.items())
               if desde <= pd.Timestamp(f) <= hasta]
        return out
    except Exception:
        return []


def efecto_feriados(limpio: pd.DataFrame, pais: str):
    """Para series diarias: promedio en feriado vs día normal (%)."""
    fer = feriados_rango(pais, limpio["ds"].min(), limpio["ds"].max())
    if not fer:
        return None
    fechas_fer = {f.normalize() for f, _ in fer}
    d = limpio.copy()
    d["_fer"] = d["ds"].dt.normalize().isin(fechas_fer)
    if d["_fer"].sum() < 3:
        return None
    prom_fer = d.loc[d["_fer"], "y"].mean()
    prom_nor = d.loc[~d["_fer"], "y"].mean()
    if prom_nor <= 0:
        return None
    return {"n_feriados_hist": int(d.groupby(d["ds"].dt.normalize())["_fer"].first().sum()),
            "delta_pct": float(100 * (prom_fer - prom_nor) / prom_nor)}


# ---------------------------------------------------------------------
# Gráficas (JSON para ECharts)
# ---------------------------------------------------------------------
def _chart_proyeccion(limpio, forecast, season):
    series = []
    for uid, g in limpio.groupby("unique_id"):
        g = g.sort_values("ds").tail(season * 3)
        series.append({"nombre": f"{uid} · histórico", "tipo": "linea",
                       "x": [str(d.date()) for d in g["ds"]],
                       "y": [round(_num(v), 2) for v in g["y"]]})
    for uid, g in forecast.groupby("unique_id"):
        g = g.sort_values("ds")
        series.append({"nombre": f"{uid} · proyección", "tipo": "linea",
                       "discontinua": True,
                       "x": [str(pd.Timestamp(d).date()) for d in g["ds"]],
                       "y": [round(_num(v), 2) for v in g["Forecast"]],
                       "banda_lo": [round(_num(v), 2) for v in g["Lo_80"]],
                       "banda_hi": [round(_num(v), 2) for v in g["Hi_80"]]})
    return {"tipo": "lineas", "series": series}


def _chart_barras(labels, valores, nombre):
    return {"tipo": "barras",
            "series": [{"nombre": nombre, "x": [str(l) for l in labels],
                        "y": [round(_num(v), 2) for v in valores]}]}


# ---------------------------------------------------------------------
# Informe principal
# ---------------------------------------------------------------------
def generar_informe(limpio, meta, tabla, mejores, forecast, cv,
                    rol: str, pais: str | None, unidad: str = "unidades") -> dict:
    """rol: gerente | analista | operaciones. Devuelve dict JSON-listo."""
    season, fnom, freq = meta["season"], meta["freq_nombre"], meta["freq"]
    fplu = FREQ_PLURAL.get(fnom, fnom + "es")
    horizonte = forecast.groupby("unique_id").size().max()

    # ---- Cifras base ----
    mejor_global = tabla.loc[tabla.groupby("serie")["WAPE_%"].idxmin()]
    wape_prom = float(mejor_global["WAPE_%"].mean())
    tot_fc = float(forecast["Forecast"].sum())
    ult = float(sum(g.tail(len(forecast[forecast.unique_id == uid]))["y"].sum()
                    for uid, g in limpio.groupby("unique_id")))
    var_pct = 100 * (tot_fc - ult) / max(ult, 1e-9)
    piso, techo = float(forecast["Lo_80"].sum()), float(forecast["Hi_80"].sum())

    confianza = ("alta" if wape_prom < 15 else
                 "media" if wape_prom < 25 else "limitada")
    veredicto = {
        "alta": f"Confianza alta: validado contra tu propia historia con {wape_prom:.0f}% de error promedio.",
        "media": f"Confianza media ({wape_prom:.0f}% de error): útil para planificar, no para comprometer al detalle.",
        "limitada": f"Confianza limitada ({wape_prom:.0f}% de error): úsalo como referencia direccional, no como compromiso.",
    }[confianza]

    insights = []

    def add(id_, icono, titulo, cifra, resumen, detalle_por_rol, chart=None):
        insights.append({"id": id_, "icono": icono, "titulo": titulo,
                         "cifra": cifra, "resumen": resumen,
                         "detalle": detalle_por_rol.get(rol, detalle_por_rol["gerente"]),
                         "chart": chart})

    # 1 · Proyección total
    add("proyeccion", "📈", "Proyección del periodo", f"{_fmt(tot_fc)} {unidad}",
        f"{var_pct:+.1f}% frente a los últimos {horizonte} periodos {fplu} reales.",
        {"gerente": f"En los próximos {horizonte} periodos {fplu} proyectamos {_fmt(tot_fc)} {unidad} "
                    f"({var_pct:+.1f}% vs el periodo anterior comparable). Úsalo para fijar metas "
                    f"comerciales y compromisos con clientes.",
         "analista": f"Suma del horizonte h={horizonte} ({fnom}): {_fmt(tot_fc)} {unidad}, "
                     f"variación {var_pct:+.1f}% vs los {horizonte} periodos previos. "
                     f"Modelos ganadores por serie en el anexo técnico.",
         "operaciones": f"Volumen esperado: {_fmt(tot_fc)} {unidad} en {horizonte} periodos {fplu} "
                        f"({var_pct:+.1f}% vs el ciclo anterior). Dimensiona personal, turnos y "
                        f"logística con este número como base."},
        _chart_proyeccion(limpio, forecast, season))

    # 2 · Rango de planificación
    add("rango", "🎯", "Rango de planificación", f"{_fmt(piso)} – {_fmt(techo)}",
        "Con 80% de probabilidad, el total caerá dentro de este rango.",
        {"gerente": f"Compromete con clientes usando el piso ({_fmt(piso)}) y prepara capacidad "
                    f"para el techo ({_fmt(techo)}). Trabajar con el punto medio a secas es la "
                    f"fuente más común de sobrecostos.",
         "analista": f"Intervalo empírico al 80% construido con los residuos de validación "
                     f"walk-forward: [{_fmt(piso)}, {_fmt(techo)}]. Amplía a 95% multiplicando "
                     f"el semi-ancho por ~1.5 si necesitas cobertura contractual.",
         "operaciones": f"Planifica el estándar con {_fmt(piso)} asegurado y deja prevista la "
                        f"flexibilidad (horas extra, terceros) para llegar a {_fmt(techo)} si la "
                        f"demanda acompaña."})

    # 3 · Confiabilidad
    detalle_modelos = "; ".join(f"{r.serie}: {r.modelo} ({r['WAPE_%']:.1f}%)"
                                for _, r in mejor_global.iterrows())
    add("confianza", "🛡️", "Qué tan confiable es", f"{wape_prom:.0f}% error",
        veredicto,
        {"gerente": f"Probamos los modelos contra tus últimos periodos reales (sin que los vieran). "
                    f"Se equivocaron {wape_prom:.0f}% en promedio. {veredicto}",
         "analista": f"WAPE promedio de los ganadores: {wape_prom:.1f}% (validación walk-forward, "
                     f"3 ventanas). Por serie → {detalle_modelos}.",
         "operaciones": f"El margen de error promedio es {wape_prom:.0f}%: si planificas 100, "
                        f"la realidad suele caer entre {100 - wape_prom:.0f} y {100 + wape_prom:.0f}."})

    # 4 · Estacionalidad
    d = limpio.copy()
    if freq == "D":
        d["periodo"] = d["ds"].dt.day_name().map(DIAS_ES)
        orden = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        etiqueta = "día de la semana"
    else:
        d["periodo"] = d["ds"].dt.month.map(lambda m: MESES_ES[m - 1])
        orden = MESES_ES
        etiqueta = "mes"
    perfil = d.groupby("periodo")["y"].mean().reindex(orden).dropna()
    if len(perfil) >= 3:
        pico, valle = str(perfil.idxmax()), str(perfil.idxmin())
        amp = 100 * (perfil.max() - perfil.min()) / max(perfil.mean(), 1e-9)
        add("estacionalidad", "🌊", "Tu patrón estacional", f"pico: {pico}",
            f"El {etiqueta} más fuerte es {pico} y el más débil {valle} ({amp:.0f}% de amplitud).",
            {"gerente": f"Tu negocio respira por {etiqueta}: {pico} concentra los máximos y {valle} "
                        f"los mínimos, con {amp:.0f}% de diferencia. Negocia recursos y promociones "
                        f"alrededor del pico.",
             "analista": f"Perfil estacional por {etiqueta}: máximo en {pico}, mínimo en {valle}, "
                         f"amplitud {amp:.0f}% sobre la media. El componente está incorporado vía "
                         f"MSTL en los estadísticos y como feature de calendario en LightGBM.",
             "operaciones": f"Refuerza turnos y stock antes de {pico} y aprovecha {valle} para "
                            f"mantenimiento, vacaciones y tareas de fondo."},
            _chart_barras(perfil.index.tolist(), perfil.values, f"promedio por {etiqueta}"))

    # 5 · Feriados
    if pais:
        nombre_pais = PAISES.get(pais, pais)
        fer_hor = feriados_rango(pais, forecast["ds"].min(), forecast["ds"].max())
        efecto = efecto_feriados(limpio, pais) if freq == "D" else None
        if fer_hor:
            lista = "; ".join(f"{fecha_es(f)} ({n})" for f, n in fer_hor[:5])
            extra = ""
            if efecto:
                dir_ = "sube" if efecto["delta_pct"] > 0 else "cae"
                extra = (f" Históricamente, en feriado tu valor {dir_} "
                         f"{abs(efecto['delta_pct']):.0f}% frente a un día normal "
                         f"({efecto['n_feriados_hist']} feriados observados).")
            add("feriados", "📅", f"Feriados de {nombre_pais} en tu horizonte",
                f"{len(fer_hor)} feriado{'s' if len(fer_hor) != 1 else ''}",
                f"{lista}." + extra,
                {"gerente": f"Tu proyección cruza {len(fer_hor)} feriado(s): {lista}.{extra} "
                            f"Ajusta compromisos de entrega alrededor de esas fechas.",
                 "analista": f"Feriados {nombre_pais} dentro del horizonte: {lista}.{extra} "
                             f"Si el efecto es material, etiquétalos como variable exógena en la "
                             f"siguiente iteración.",
                 "operaciones": f"Fechas a blindar en el plan de turnos: {lista}.{extra}"})
        else:
            add("feriados", "📅", f"Feriados de {nombre_pais}", "0 en el horizonte",
                "Tu horizonte de proyección no cruza ningún feriado nacional.",
                {"gerente": "Sin feriados en el periodo proyectado: no esperes distorsiones de calendario.",
                 "analista": "Horizonte libre de feriados nacionales; el calendario no introduce exógenas.",
                 "operaciones": "Sin feriados en el periodo: planifica turnos estándar."})

    # 6 · Tendencia
    from scipy import stats as scs
    t_txt = []
    for uid, g in limpio.groupby("unique_id"):
        mm = g["y"].rolling(season, min_periods=max(2, season // 2)).mean().dropna()
        if len(mm) > 10:
            pend, _, _, p, _ = scs.linregress(np.arange(len(mm)), mm.values)
            cambio = 100 * pend * len(mm) / max(abs(mm.iloc[0]), 1e-9)
            dir_ = "creció" if cambio > 5 else "cayó" if cambio < -5 else "se mantuvo estable"
            t_txt.append(f"{uid} {dir_} ({cambio:+.0f}%)")
    if t_txt:
        add("tendencia", "🧭", "Tendencia de fondo", None,
            "; ".join(t_txt) + " a lo largo de tu historia (sin el ruido estacional).",
            {"gerente": "Quitando la estacionalidad, " + "; ".join(t_txt) +
                        ". La tendencia de fondo es la que define si el negocio crece o solo fluctúa.",
             "analista": "Regresión sobre media móvil desestacionalizada (ventana = 1 estación): " +
                         "; ".join(t_txt) + ".",
             "operaciones": "Dirección de fondo del volumen: " + "; ".join(t_txt) +
                            ". Úsala para decisiones de capacidad estructural (contratar vs tercerizar)."})

    # 7 · Concentración (si hay varias series)
    tot = limpio.groupby("unique_id")["y"].sum().sort_values(ascending=False)
    if len(tot) > 1:
        acum = tot.cumsum() / tot.sum()
        n80 = int((acum <= 0.8).sum()) + 1
        lider_pct = 100 * tot.iloc[0] / tot.sum()
        add("concentracion", "⚖️", "Concentración del negocio",
            f"{n80} de {len(tot)} series",
            f"{n80} serie(s) concentran ~80% del volumen; la líder ({tot.index[0]}) pesa {lider_pct:.0f}%.",
            {"gerente": f"Dependes fuertemente de {tot.index[0]} ({lider_pct:.0f}% del total). "
                        f"Es tu cliente/producto a blindar — y tu mayor riesgo si se cae.",
             "analista": f"Pareto: {n80}/{len(tot)} series ≈ 80% del volumen. Prioriza la precisión "
                         f"del modelo en las series top; el error en la cola pesa poco.",
             "operaciones": f"Asigna tus mejores recursos a {tot.index[0]} y las series top: "
                            f"un quiebre ahí golpea {lider_pct:.0f}% de la operación."},
            _chart_barras(tot.index.tolist(), tot.values, "volumen total por serie"))

    # 8 · Volatilidad
    vol = limpio.groupby("unique_id")["y"].agg(
        lambda s: 100 * s.std() / max(s.mean(), 1e-9)).sort_values()
    if len(vol) > 1:
        add("volatilidad", "🌪️", "Estabilidad por serie", None,
            f"Más estable: {vol.index[0]} (±{vol.iloc[0]:.0f}%); más volátil: {vol.index[-1]} (±{vol.iloc[-1]:.0f}%).",
            {"gerente": f"{vol.index[-1]} es tu serie más impredecible (±{vol.iloc[-1]:.0f}%): "
                        f"exige más colchón de inventario/capacidad que {vol.index[0]} (±{vol.iloc[0]:.0f}%).",
             "analista": f"Coeficiente de variación por serie: {vol.index[0]} {vol.iloc[0]:.0f}% → "
                         f"{vol.index[-1]} {vol.iloc[-1]:.0f}%. En las volátiles conviene ensanchar "
                         f"intervalos y buscar exógenas que expliquen los saltos.",
             "operaciones": f"Para {vol.index[-1]} trabaja con buffer amplio y revisión semanal; "
                            f"{vol.index[0]} tolera planificación rígida."})

    # 9 · Anomalías (analista y operaciones)
    if rol in ("analista", "operaciones"):
        from scipy import stats as scs2
        anom = []
        for uid, g in limpio.groupby("unique_id"):
            if g["y"].std() > 0:
                z = np.abs(scs2.zscore(g["y"]))
                if (z > 3).any():
                    peor = g.iloc[int(np.argmax(z))]
                    anom.append(f"{uid}: {int((z > 3).sum())} valores atípicos "
                                f"(mayor: {fecha_es(peor['ds'])} = {_fmt(peor['y'])})")
        add("anomalias", "🚨", "Valores atípicos", None,
            ("; ".join(anom) + ".") if anom else "Sin anomalías severas: series limpias.",
            {"gerente": ("; ".join(anom) + ".") if anom else "Series limpias.",
             "analista": (("; ".join(anom) + ". Verifica si corresponden a eventos reales "
                          "(feriados, paros, promociones) para etiquetarlos como exógenas.")
                          if anom else "Ningún |z| > 3: no hay outliers que distorsionen el ajuste."),
             "operaciones": (("; ".join(anom) + ". Si fueron quiebres o paros, documenta la causa "
                             "para anticipar la próxima.") if anom else "Sin eventos atípicos registrados.")})

    # 10 · Valor del modelo y sesgo (solo analista)
    if rol == "analista":
        mejora_txt, sesgo_txt = [], []
        for uid, g in cv.groupby("unique_id"):
            w_base = wape(g["y"], g["SeasonalNaive"])
            pred = g[mejores[uid]].mean(axis=1)
            mejora_txt.append(f"{uid}: {100 * (w_base - wape(g['y'], pred)) / max(w_base, 1e-9):+.0f}%")
            b = bias_pct(g["y"], pred)
            if abs(b) > 5:
                sesgo_txt.append(f"{uid} {'sobre' if b > 0 else 'sub'}estima {abs(b):.1f}%")
        add("valor_modelo", "⚙️", "Valor del modelo vs naive", None,
            "Mejora frente a repetir la última estación: " + "; ".join(mejora_txt) + ".",
            {"gerente": "", "operaciones": "",
             "analista": "Mejora WAPE vs SeasonalNaive: " + "; ".join(mejora_txt) +
                         ". Si ≤0%, el patrón es tan estable que el naive basta (también es un hallazgo). " +
                         (("Sesgo a corregir → " + "; ".join(sesgo_txt) + ".") if sesgo_txt
                          else "Sesgo <5% en todas las series.")})

    # ---- Orden según rol ----
    orden_rol = {
        "gerente": ["proyeccion", "confianza", "rango", "concentracion",
                    "estacionalidad", "feriados", "tendencia", "volatilidad"],
        "analista": ["proyeccion", "confianza", "valor_modelo", "tendencia",
                     "estacionalidad", "feriados", "anomalias", "concentracion",
                     "volatilidad", "rango"],
        "operaciones": ["proyeccion", "rango", "estacionalidad", "feriados",
                        "volatilidad", "concentracion", "anomalias", "tendencia"],
    }[rol]
    pos = {k: i for i, k in enumerate(orden_rol)}
    insights.sort(key=lambda x: pos.get(x["id"], 99))

    return {
        "rol": rol,
        "kpis": {
            "total": round(tot_fc, 1), "total_fmt": _fmt(tot_fc),
            "variacion_pct": round(var_pct, 1),
            "wape_pct": round(wape_prom, 1),
            "confianza": confianza, "veredicto": veredicto,
            "piso": round(piso, 1), "techo": round(techo, 1),
            "piso_fmt": _fmt(piso), "techo_fmt": _fmt(techo),
            "horizonte": int(horizonte), "frecuencia": fnom,
            "frecuencia_plural": fplu,
            "n_series": int(forecast["unique_id"].nunique()),
            "unidad": unidad,
        },
        "chart_principal": _chart_proyeccion(limpio, forecast, season),
        "insights": insights,
        "anexo": {
            "ranking": [{k: _num(v) for k, v in r.items()}
                        for r in tabla.rename(columns={
                            "WAPE_%": "error_WAPE_pct", "BIAS_%": "sesgo_pct"
                        }).to_dict("records")],
            "ganadores": {u: list(m) for u, m in mejores.items()},
        },
    }
