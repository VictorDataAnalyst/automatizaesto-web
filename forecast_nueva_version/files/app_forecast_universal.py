# =====================================================================
# FORECAST UNIVERSAL - automatizaesto.com
# App Streamlit: cualquier negocio, cualquier formato de datos
# Flujo: Rol -> Carga -> Mapeo asistido -> Prevalidacion -> Modelos -> Insights
# Ejecutar:  streamlit run app_forecast_universal.py
# Autor: Victor Cardena Denegri
# =====================================================================
import io
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# =====================================================================
# NUCLEO (funciones puras, sin Streamlit -> testeables y reutilizables)
# =====================================================================

# ---------- 1. Deteccion automatica de columnas ----------
PALABRAS_FECHA = ["fecha", "date", "dia", "day", "periodo", "semana", "week", "mes", "month", "ds"]
PALABRAS_VALOR = ["venta", "sales", "monto", "importe", "toneladas", "tm", "kg", "unidades",
                  "cantidad", "qty", "hrs", "horas", "hours", "costo", "cost", "ingreso",
                  "revenue", "facturable", "demanda", "valor", "total", "y"]
PALABRAS_SERIE = ["serie", "campana", "campaña", "cliente", "producto", "sku", "mercado",
                  "destino", "sucursal", "tienda", "categoria", "nombre", "nom", "id", "unique_id"]

def detectar_columnas(df: pd.DataFrame) -> dict:
    """Heuristica de mapeo: devuelve sugerencias {fecha, valor, serie} con score."""
    sug = {"fecha": None, "valor": None, "serie": None}

    # Fecha: por dtype o por nombre+parseo
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            sug["fecha"] = c; break
    if sug["fecha"] is None:
        for c in df.columns:
            nombre = str(c).lower()
            if any(p in nombre for p in PALABRAS_FECHA):
                try:
                    pd.to_datetime(df[c].dropna().head(50))
                    sug["fecha"] = c; break
                except Exception:
                    pass

    # Valor: numerica continua con mayor varianza relativa y nombre afin
    numericas = [c for c in df.columns
                 if pd.api.types.is_numeric_dtype(df[c]) and c != sug["fecha"]]
    if numericas:
        scores = {}
        for c in numericas:
            s = 0.0
            nombre = str(c).lower()
            if any(p in nombre for p in PALABRAS_VALOR): s += 2
            if df[c].nunique() > max(20, len(df) * 0.05): s += 1   # continua
            if "id" in nombre or "cod" in nombre: s -= 3            # no es metrica
            scores[c] = s
        sug["valor"] = max(scores, key=scores.get)

    # Serie: categorica de baja cardinalidad (o texto)
    candidatas = []
    for c in df.columns:
        if c in (sug["fecha"], sug["valor"]): continue
        nun = df[c].nunique()
        if 1 < nun <= max(50, len(df) * 0.02):
            s = 1.0
            nombre = str(c).lower()
            if any(p in nombre for p in PALABRAS_SERIE): s += 2
            if df[c].dtype == object: s += 1   # preferir nombres legibles a IDs
            candidatas.append((s, c))
    if candidatas:
        sug["serie"] = sorted(candidatas, reverse=True)[0][1]
    return sug


# ---------- 2. Prevalidacion ----------
def prevalidar(df, col_fecha, col_valor, col_serie):
    """Devuelve (df_limpio, lista de checks). Cada check: (nivel, mensaje).
    nivel: ok | warn | error"""
    checks = []
    d = df.copy()

    # Parseo de fecha
    try:
        d[col_fecha] = pd.to_datetime(d[col_fecha])
        checks.append(("ok", f"Columna de fecha '{col_fecha}' parseada correctamente."))
    except Exception as e:
        checks.append(("error", f"No se pudo convertir '{col_fecha}' a fecha: {e}"))
        return None, checks

    # Valor numerico
    d[col_valor] = pd.to_numeric(d[col_valor], errors="coerce")
    n_nulos = int(d[col_valor].isna().sum())
    if n_nulos:
        checks.append(("warn", f"{n_nulos} valores no numericos/nulos en '{col_valor}' -> se eliminan."))
        d = d.dropna(subset=[col_valor])
    else:
        checks.append(("ok", f"'{col_valor}' 100% numerico, sin nulos."))

    # Serie
    if col_serie is None or col_serie == "(sin serie - una sola)":
        d["_serie"] = "TOTAL"; col_serie = "_serie"
        checks.append(("ok", "Sin columna de serie: se modela una serie unica TOTAL."))
    d[col_serie] = d[col_serie].astype(str)

    # Negativos
    n_neg = int((d[col_valor] < 0).sum())
    if n_neg:
        checks.append(("warn", f"{n_neg} valores negativos detectados (revisar si son devoluciones/ajustes)."))

    # Duplicados fecha+serie -> agregamos
    dup = d.duplicated(subset=[col_fecha, col_serie]).sum()
    if dup:
        checks.append(("warn", f"{dup} filas duplicadas por fecha+serie -> se agregan con suma."))
    d = (d.groupby([col_serie, col_fecha], as_index=False)[col_valor].sum())

    # Frecuencia detectada
    diffs = d.sort_values(col_fecha).groupby(col_serie)[col_fecha].diff().dt.days.dropna()
    mediana = float(diffs.median()) if len(diffs) else 1
    if mediana <= 1.5:   freq, season, fnom = "D", 7, "diaria"
    elif mediana <= 9:   freq, season, fnom = "W-SUN", 52, "semanal"
    elif mediana <= 45:  freq, season, fnom = "MS", 12, "mensual"
    else:                freq, season, fnom = "QS", 4, "trimestral"
    checks.append(("ok", f"Frecuencia detectada: {fnom} (gap mediano {mediana:.0f} dias)."))

    # Gaps -> reindexar y rellenar con 0 (tipico en demanda) si son pocos
    partes = []
    for uid, g in d.groupby(col_serie):
        g = g.set_index(col_fecha).sort_index()[[col_valor]]
        if freq == "D":
            idx = pd.date_range(g.index.min(), g.index.max(), freq="D")
        elif freq.startswith("W"):
            g = g.resample("W-SUN")[ [col_valor] ].sum(); idx = g.index
        elif freq == "MS":
            g = g.resample("MS")[ [col_valor] ].sum(); idx = g.index
        else:
            g = g.resample("QS")[ [col_valor] ].sum(); idx = g.index
        faltan = len(idx) - len(g.dropna())
        g = g.reindex(idx).fillna(0.0) if freq == "D" else g.fillna(0.0)
        if faltan > 0:
            checks.append(("warn", f"Serie '{uid}': {faltan} periodos sin datos -> rellenados con 0."))
        gg = g.reset_index(); gg.columns = ["ds", "y"]; gg["unique_id"] = uid
        partes.append(gg)
    limpio = pd.concat(partes)[["unique_id", "ds", "y"]]

    # Largo minimo
    for uid, g in limpio.groupby("unique_id"):
        if len(g) < 2 * season + 10:
            checks.append(("warn", f"Serie '{uid}' tiene solo {len(g)} periodos; "
                                   f"se recomienda >= {2*season+10} para capturar estacionalidad."))
        else:
            checks.append(("ok", f"Serie '{uid}': {len(g)} periodos. Suficiente historia."))

    meta = {"freq": freq, "season": season, "freq_nombre": fnom}
    return (limpio, meta), checks


# ---------- 3. Motor de modelos ----------
def wape(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(np.abs(y - yhat)) / max(np.sum(np.abs(y)), 1e-9)

def bias_pct(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(yhat - y) / max(np.sum(np.abs(y)), 1e-9)

# ¿Esta disponible el stack Nixtla? Se decide una sola vez al importar.
try:
    import statsforecast  # noqa
    import mlforecast      # noqa
    NIXTLA_OK = True
except Exception:
    NIXTLA_OK = False

MOTOR_INFO = ("completo (Nixtla: MSTL+AutoARIMA, AutoETS, SeasonalNaive, LightGBM)"
              if NIXTLA_OK else
              "portable (LightGBM + Holt-Winters + SeasonalNaive, sin Nixtla)")


def _seleccionar(cv, modelos):
    """Logica comun de ranking + ensamble honesto. Devuelve (tabla, mejores)."""
    filas, mejores = [], {}
    for uid, g in cv.groupby("unique_id"):
        met = {m: wape(g["y"], g[m]) for m in modelos if m in g.columns}
        for m, w in met.items():
            filas.append({"serie": uid, "modelo": m, "WAPE_%": round(w, 2),
                          "BIAS_%": round(bias_pct(g["y"], g[m]), 2)})
        top2 = sorted(met, key=met.get)[:2]
        ens = g[top2].mean(axis=1)
        w_ens, w_best = wape(g["y"], ens), met[top2[0]]
        if len(top2) == 2 and w_ens < w_best:
            mejores[uid] = top2
            filas.append({"serie": uid, "modelo": f"ENSAMBLE({'+'.join(top2)})",
                          "WAPE_%": round(w_ens, 2), "BIAS_%": round(bias_pct(g["y"], ens), 2)})
        else:
            mejores[uid] = [top2[0]]
    tabla = pd.DataFrame(filas).sort_values(["serie", "WAPE_%"]).reset_index(drop=True)
    return tabla, mejores


def entrenar_y_competir(limpio, meta, horizonte, n_windows=3):
    """Router: usa Nixtla si esta instalado, si no el motor portable.
    Ambos devuelven (tabla, mejores, forecast, cv) con el mismo esquema."""
    if NIXTLA_OK:
        return _motor_nixtla(limpio, meta, horizonte, n_windows)
    return _motor_portable(limpio, meta, horizonte, n_windows)


# --------- MOTOR A: Nixtla (preferido) ---------
def _motor_nixtla(limpio, meta, horizonte, n_windows):
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS, MSTL, AutoARIMA, SeasonalNaive
    from mlforecast import MLForecast
    from mlforecast.lag_transforms import RollingMean, ExpandingMean
    import lightgbm as lgb

    freq, season = meta["freq"], meta["season"]
    h = horizonte
    sf = StatsForecast(models=[
        MSTL(season_length=season, trend_forecaster=AutoARIMA()),
        AutoETS(season_length=season),
        SeasonalNaive(season_length=season),
    ], freq=freq, n_jobs=-1)

    lags_base = {7: [1, 2, 3, 7, 14, 28], 52: [1, 2, 4, 8, 26, 52],
                 12: [1, 2, 3, 6, 12], 4: [1, 2, 4]}[season]
    n_min = limpio.groupby("unique_id").size().min()
    lags = [l for l in lags_base if l < n_min - h - 5] or [1]
    mlf = MLForecast(
        models={"LightGBM": lgb.LGBMRegressor(
            n_estimators=500, learning_rate=0.05, num_leaves=31,
            min_child_samples=8, subsample=0.9, colsample_bytree=0.9,
            random_state=42, verbosity=-1)},
        freq=freq, lags=lags,
        lag_transforms={lags[0]: [RollingMean(window_size=min(4, max(2, season // 3))),
                                  ExpandingMean()]},
        date_features=["dayofweek", "week", "month"] if freq == "D" else ["week", "month"],
    )
    step = max(1, h // 2)
    cv_sf = sf.cross_validation(df=limpio, h=h, n_windows=n_windows, step_size=step)
    cv_ml = mlf.cross_validation(df=limpio, h=h, n_windows=n_windows, step_size=step,
                                 static_features=[])
    cv = cv_sf.merge(cv_ml.drop(columns=["y"]), on=["unique_id", "ds", "cutoff"])
    tabla, mejores = _seleccionar(cv, ["MSTL", "AutoETS", "SeasonalNaive", "LightGBM"])

    fc_sf = sf.forecast(df=limpio, h=h, level=[80])
    mlf.fit(limpio, static_features=[])
    fc = fc_sf.merge(mlf.predict(h=h), on=["unique_id", "ds"])
    out = []
    for uid, g in fc.groupby("unique_id"):
        g = g.copy()
        g["Forecast"] = g[mejores[uid]].mean(axis=1).clip(lower=0)
        stat = next((m for m in mejores[uid] if m != "LightGBM"), "MSTL")
        g["Lo_80"] = g.get(f"{stat}-lo-80", g["Forecast"] * 0.85).clip(lower=0)
        g["Hi_80"] = g.get(f"{stat}-hi-80", g["Forecast"] * 1.15)
        out.append(g[["unique_id", "ds", "Forecast", "Lo_80", "Hi_80"]])
    return tabla, mejores, pd.concat(out), cv


# --------- MOTOR B: portable (sin Nixtla) ---------
# Implementa SeasonalNaive, Holt-Winters (statsmodels) y LightGBM directos.
# Mismo esquema de salida; usa walk-forward manual.
def _features_ml(g, season, lags):
    """Construye matriz de features (lags + calendario) para una serie."""
    d = g.copy().reset_index(drop=True)
    for l in lags:
        d[f"lag_{l}"] = d["y"].shift(l)
    d["roll"] = d["y"].shift(1).rolling(min(4, max(2, season // 3))).mean()
    d["exp"] = d["y"].shift(1).expanding().mean()
    d["dow"] = d["ds"].dt.dayofweek
    d["week"] = d["ds"].dt.isocalendar().week.astype(int)
    d["month"] = d["ds"].dt.month
    return d

def _pred_recursiva_lgb(model, hist, season, lags, h, feat_cols):
    """Prediccion recursiva h pasos con LightGBM (reinyecta su propia prediccion)."""
    serie = hist.copy()
    preds = []
    last = serie["ds"].iloc[-1]
    paso = (serie["ds"].iloc[-1] - serie["ds"].iloc[-2])
    for _ in range(h):
        nxt = last + paso
        fila = {"ds": nxt}
        ext = pd.concat([serie, pd.DataFrame([{"ds": nxt, "y": np.nan}])], ignore_index=True)
        fext = _features_ml(ext, season, lags).iloc[-1]
        X = fext[feat_cols].values.reshape(1, -1).astype(float)
        yhat = max(0.0, float(model.predict(X)[0]))
        preds.append((nxt, yhat))
        serie = pd.concat([serie, pd.DataFrame([{"ds": nxt, "y": yhat}])], ignore_index=True)
        last = nxt
    return preds

def _motor_portable(limpio, meta, horizonte, n_windows):
    import lightgbm as lgb
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    freq, season = meta["freq"], meta["season"]
    h = horizonte
    lags_base = {7: [1, 2, 3, 7, 14, 28], 52: [1, 2, 4, 8, 26, 52],
                 12: [1, 2, 3, 6, 12], 4: [1, 2, 4]}[season]
    n_min = limpio.groupby("unique_id").size().min()
    lags = [l for l in lags_base if l < n_min - h - 5] or [1]
    step = max(1, h // 2)

    def fit_pred_lgb(train, future_index):
        d = _features_ml(train, season, lags).dropna()
        feat_cols = [c for c in d.columns if c not in ("ds", "y", "unique_id")]
        if len(d) < 10:
            base = train["y"].tail(season).mean()
            return [base] * len(future_index), feat_cols, None
        model = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31,
                                  min_child_samples=8, subsample=0.9, colsample_bytree=0.9,
                                  random_state=42, verbosity=-1)
        model.fit(d[feat_cols], d["y"])
        preds = [p for _, p in _pred_recursiva_lgb(model, train[["ds", "y"]], season, lags,
                                                   len(future_index), feat_cols)]
        return preds, feat_cols, model

    def fit_pred_hw(train, n):
        y = train["y"].values
        try:
            usa_season = len(y) >= 2 * season
            m = ExponentialSmoothing(y, trend="add",
                                     seasonal="add" if usa_season else None,
                                     seasonal_periods=season if usa_season else None,
                                     initialization_method="estimated").fit()
            return np.clip(m.forecast(n), 0, None)
        except Exception:
            return np.repeat(train["y"].tail(season).mean(), n)

    def snaive(train, n):
        last = train["y"].values[-season:] if len(train) >= season else train["y"].values
        return np.array([last[i % len(last)] for i in range(n)])

    # ---- Walk-forward manual ----
    cv_filas = []
    for uid, g in limpio.groupby("unique_id"):
        g = g.sort_values("ds").reset_index(drop=True)
        n = len(g)
        for w in range(n_windows):
            corte = n - (n_windows - w) * step
            if corte < season + h:
                continue
            train, test = g.iloc[:corte], g.iloc[corte:corte + h]
            if len(test) == 0:
                continue
            p_lgb, _, _ = fit_pred_lgb(train, test["ds"])
            p_hw = fit_pred_hw(train, len(test))
            p_sn = snaive(train, len(test))
            for i, (_, row) in enumerate(test.iterrows()):
                cv_filas.append({"unique_id": uid, "ds": row["ds"], "cutoff": train["ds"].iloc[-1],
                                 "y": row["y"], "LightGBM": p_lgb[i],
                                 "HoltWinters": p_hw[i], "SeasonalNaive": p_sn[i]})
    cv = pd.DataFrame(cv_filas)
    if cv.empty:  # series muy cortas: degradar a holdout simple
        for uid, g in limpio.groupby("unique_id"):
            g = g.sort_values("ds").reset_index(drop=True)
            tr, te = g.iloc[:-h], g.iloc[-h:]
            p_hw = fit_pred_hw(tr, len(te)); p_sn = snaive(tr, len(te))
            p_lgb, _, _ = fit_pred_lgb(tr, te["ds"])
            for i, (_, row) in enumerate(te.iterrows()):
                cv_filas.append({"unique_id": uid, "ds": row["ds"], "cutoff": tr["ds"].iloc[-1],
                                 "y": row["y"], "LightGBM": p_lgb[i],
                                 "HoltWinters": p_hw[i], "SeasonalNaive": p_sn[i]})
        cv = pd.DataFrame(cv_filas)

    tabla, mejores = _seleccionar(cv, ["HoltWinters", "SeasonalNaive", "LightGBM"])

    # ---- Forecast final sobre toda la historia ----
    out = []
    for uid, g in limpio.groupby("unique_id"):
        g = g.sort_values("ds").reset_index(drop=True)
        paso = g["ds"].iloc[-1] - g["ds"].iloc[-2]
        fechas = [g["ds"].iloc[-1] + paso * (i + 1) for i in range(h)]
        preds = {}
        preds["LightGBM"], _, _ = fit_pred_lgb(g, fechas)
        preds["HoltWinters"] = fit_pred_hw(g, h)
        preds["SeasonalNaive"] = snaive(g, h)
        mat = pd.DataFrame({m: preds[m] for m in mejores[uid]})
        fc = mat.mean(axis=1).clip(lower=0).values
        # IC empirico: residuos de la mejor combinacion en CV
        gcv = cv[cv.unique_id == uid]
        resid = (gcv["y"] - gcv[mejores[uid]].mean(axis=1)).std() if len(gcv) else fc.std()
        resid = resid if np.isfinite(resid) and resid > 0 else max(1.0, np.mean(fc) * 0.15)
        out.append(pd.DataFrame({"unique_id": uid, "ds": fechas, "Forecast": fc,
                                 "Lo_80": np.clip(fc - 1.28 * resid, 0, None),
                                 "Hi_80": fc + 1.28 * resid}))
    return tabla, mejores, pd.concat(out), cv


# ---------- 4. Generador de insights (max 10) ----------
def generar_insights(limpio, meta, tabla, mejores, forecast, cv, rol):
    """Devuelve lista de dicts {titulo, texto, fig(plotly) o None}, max 10,
    con lenguaje adaptado al rol."""
    import plotly.express as px
    import plotly.graph_objects as go

    gerencial = rol.startswith("Gerente")
    season, fnom = meta["season"], meta["freq_nombre"]
    ins = []

    def add(titulo, texto, fig=None):
        if len(ins) < 10:
            ins.append({"titulo": titulo, "texto": texto, "fig": fig})

    # 1. Mejor modelo global
    mejor_global = (tabla.loc[tabla.groupby("serie")["WAPE_%"].idxmin()])
    detalle = "; ".join(f"{r.serie}: {r.modelo} (WAPE {r['WAPE_%']:.1f}%)"
                        for _, r in mejor_global.iterrows())
    wape_prom = mejor_global["WAPE_%"].mean()
    veredicto = ("alta confiabilidad" if wape_prom < 15 else
                 "confiabilidad aceptable" if wape_prom < 25 else
                 "precision limitada: usar como referencia, no como compromiso")
    add("Mejor modelo por serie",
        f"Ganadores en validacion walk-forward -> {detalle}. "
        f"Error promedio (WAPE) {wape_prom:.1f}%: {veredicto}.")

    # 2. Proyeccion total
    tot_fc = forecast.groupby("unique_id")["Forecast"].sum()
    ult = limpio.groupby("unique_id").apply(lambda g: g.tail(len(forecast[forecast.unique_id==g.name]))["y"].sum())
    var = 100 * (tot_fc.sum() - ult.sum()) / max(ult.sum(), 1e-9)
    fig = go.Figure()
    for uid, g in limpio.groupby("unique_id"):
        fig.add_scatter(x=g["ds"].tail(season*3), y=g["y"].tail(season*3), name=f"{uid} (hist)", mode="lines")
    for uid, g in forecast.groupby("unique_id"):
        fig.add_scatter(x=g["ds"], y=g["Forecast"], name=f"{uid} (forecast)",
                        mode="lines", line=dict(dash="dash"))
    fig.update_layout(height=380, margin=dict(t=30, b=10))
    add("Proyeccion vs historia reciente",
        f"Total proyectado proximo horizonte: {tot_fc.sum():,.0f} "
        f"({var:+.1f}% vs el mismo numero de periodos previos). "
        + ("Util para planificar capacidad y compromisos comerciales." if gerencial
           else "Comparar contra plan/presupuesto y ajustar staffing o compra."),
        fig)

    # 3. Estacionalidad dominante
    d = limpio.copy()
    if meta["freq"] == "D":
        d["periodo"] = d["ds"].dt.day_name()
        orden = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        etiqueta = "dia de la semana"
    else:
        d["periodo"] = d["ds"].dt.month
        orden = list(range(1, 13)); etiqueta = "mes"
    perfil = d.groupby("periodo")["y"].mean().reindex(orden).dropna()
    pico, valle = perfil.idxmax(), perfil.idxmin()
    amp = 100 * (perfil.max() - perfil.min()) / max(perfil.mean(), 1e-9)
    fig = px.bar(perfil.reset_index(), x="periodo", y="y", height=340)
    fig.update_layout(margin=dict(t=30, b=10), yaxis_title="promedio")
    add(f"Estacionalidad por {etiqueta}",
        f"Pico en {pico}, valle en {valle}; amplitud {amp:.0f}% sobre el promedio. "
        + ("Concentrar recursos y negociacion logistica en el pico." if gerencial
           else "Incorporada como feature en LightGBM y via MSTL en los estadisticos."),
        fig)

    # 4. Tendencia (regresion sobre media movil)
    from scipy import stats as scs
    t_ins = []
    for uid, g in limpio.groupby("unique_id"):
        mm = g["y"].rolling(season, min_periods=max(2, season//2)).mean().dropna()
        if len(mm) > 10:
            pend, _, r, p, _ = scs.linregress(np.arange(len(mm)), mm.values)
            cambio = 100 * pend * len(mm) / max(mm.iloc[0], 1e-9)
            dir_ = "crecio" if cambio > 5 else "cayo" if cambio < -5 else "se mantuvo estable"
            t_ins.append(f"{uid} {dir_} ({cambio:+.0f}% en el periodo, p={p:.3f})")
    add("Tendencia de fondo", "Sobre media movil desestacionalizada: " + "; ".join(t_ins) + ".")

    # 5. Outliers / anomalias
    anom = []
    for uid, g in limpio.groupby("unique_id"):
        z = np.abs(scs.zscore(g["y"])) if g["y"].std() > 0 else np.zeros(len(g))
        n_out = int((z > 3).sum())
        if n_out:
            peor = g.loc[g.index[np.argmax(z)]]
            anom.append(f"{uid}: {n_out} anomalias (mayor: {peor['ds'].date()} = {peor['y']:,.0f})")
    add("Anomalias detectadas",
        ("; ".join(anom) + ". Validar si fueron eventos reales (feriados, paros, promos) "
         "para etiquetarlos como exogenas en la siguiente iteracion.")
        if anom else "Sin anomalias severas (|z|>3). Series limpias.")

    # 6. Volatilidad por serie (CV)
    vol = limpio.groupby("unique_id")["y"].agg(lambda s: 100*s.std()/max(s.mean(),1e-9)).sort_values()
    add("Volatilidad por serie",
        f"Serie mas estable: {vol.index[0]} (CV {vol.iloc[0]:.0f}%); "
        f"mas volatil: {vol.index[-1]} (CV {vol.iloc[-1]:.0f}%). "
        + ("La volatil necesita mas colchon de capacidad/inventario." if gerencial
           else "En la volatil conviene ampliar intervalos y revisar exogenas."))

    # 7. Concentracion (Pareto)
    tot = limpio.groupby("unique_id")["y"].sum().sort_values(ascending=False)
    if len(tot) > 1:
        acum = tot.cumsum() / tot.sum()
        n80 = int((acum <= 0.8).sum()) + 1
        add("Concentracion del negocio",
            f"{n80} de {len(tot)} series concentran ~80% del volumen "
            f"(lider: {tot.index[0]} con {100*tot.iloc[0]/tot.sum():.0f}%). "
            + ("Riesgo de dependencia: priorizar retencion del lider." if gerencial
               else "Priorizar precision del forecast en las series top."))

    # 8. Sesgo del modelo elegido
    sesgos = []
    for uid, g in cv.groupby("unique_id"):
        pred = g[mejores[uid]].mean(axis=1)
        b = bias_pct(g["y"], pred)
        if abs(b) > 5:
            sesgos.append(f"{uid}: {'sobre' if b>0 else 'sub'}estima {abs(b):.1f}%")
    add("Sesgo del modelo",
        ("Atencion -> " + "; ".join(sesgos) + ". Corregir con ajuste de nivel o mas historia.")
        if sesgos else "Sesgo < 5% en todas las series: el modelo no sobre ni subestima sistematicamente.")

    # 9. Calidad vs baseline ingenuo
    mejora = []
    for uid, g in cv.groupby("unique_id"):
        w_base = wape(g["y"], g["SeasonalNaive"])
        w_mod = wape(g["y"], g[mejores[uid]].mean(axis=1))
        mejora.append(f"{uid}: {100*(w_base-w_mod)/max(w_base,1e-9):+.0f}% vs naive")
    add("Valor agregado del modelo",
        "Mejora frente a repetir la ultima estacion (SeasonalNaive): " + "; ".join(mejora) +
        ". Si la mejora es <=0%, el patron es tan estable que el naive basta (tambien es un hallazgo).")

    # 10. Rango de planificacion (intervalos)
    rng_ = forecast.groupby("unique_id").apply(
        lambda g: f"{g['Lo_80'].sum():,.0f} - {g['Hi_80'].sum():,.0f}")
    add("Rango de planificacion (IC 80%)",
        "; ".join(f"{u}: {r}" for u, r in rng_.items()) +
        ". " + ("Planificar capacidad con el techo y compromisos con el piso." if gerencial
                else "Usar Lo_80 para compromisos firmes y Hi_80 para dimensionar capacidad."))

    return ins[:10]


# =====================================================================
# INTERFAZ STREAMLIT — identidad visual ForecastMYPE / automatizaesto
# =====================================================================
BRAND = {
    "navy": "#0C1A2E", "navy2": "#1A2B45", "gold": "#C8901C", "gold_l": "#E8B440",
    "teal": "#28B088", "blue": "#2B6CB0", "bg": "#F7F9FC", "bg2": "#EEF3FA",
    "border": "#DDE6F0", "muted": "#5A7391", "white": "#FFFFFF",
}

def _setup_plotly_brand():
    """Plantilla Plotly de marca: tipografía, colores y ejes limpios."""
    import plotly.io as pio
    import plotly.graph_objects as go
    pio.templates["automatizaesto"] = go.layout.Template(layout=dict(
        font=dict(family="Inter Tight, Inter, sans-serif", color=BRAND["navy2"], size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[BRAND["navy2"], BRAND["gold"], BRAND["teal"], BRAND["blue"],
                  BRAND["gold_l"], "#8B5CF6", "#E05252"],
        xaxis=dict(gridcolor=BRAND["border"], zerolinecolor=BRAND["border"], linecolor=BRAND["border"]),
        yaxis=dict(gridcolor=BRAND["border"], zerolinecolor=BRAND["border"], linecolor=BRAND["border"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(size=11)),
        margin=dict(t=40, b=20, l=10, r=10),
        hoverlabel=dict(font_family="JetBrains Mono, monospace", font_size=12),
    ))
    pio.templates.default = "plotly_white+automatizaesto"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* base */
html, body, [data-testid="stAppViewContainer"] * { font-family: 'Inter Tight', sans-serif; }
[data-testid="stAppViewContainer"] { background: linear-gradient(165deg,#F0F5FF 0%,#FFFFFF 38%,#FFFFFF 100%); }
.block-container { max-width: 1080px; padding-top: 1.6rem; padding-bottom: 4rem; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], header[data-testid="stHeader"] { display: none; }

/* topbar de marca */
.ae-topbar { display:flex; align-items:center; gap:13px; padding:14px 0 26px; border-bottom:1px solid #DDE6F0; margin-bottom:30px; }
.ae-logo { width:40px; height:40px; border-radius:11px; background:linear-gradient(135deg,#C8901C,#E8B440);
  display:flex; align-items:center; justify-content:center; font-family:'Fraunces',serif; font-weight:700;
  font-size:21px; color:#fff; box-shadow:0 4px 14px rgba(200,144,28,.35); }
.ae-name { font-family:'Fraunces',serif; font-weight:600; font-size:1.25rem; color:#0C1A2E; line-height:1.1; }
.ae-name small { display:block; font-family:'Inter Tight'; font-weight:500; font-size:.72rem; color:#5A7391; letter-spacing:.02em; }
.ae-beta { margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:.62rem; font-weight:500;
  text-transform:uppercase; letter-spacing:.1em; padding:4px 12px; border-radius:20px;
  background:rgba(40,176,136,.12); color:#28B088; }

/* cabecera de paso */
.ae-paso { display:flex; align-items:baseline; gap:14px; margin:34px 0 6px; }
.ae-paso .n { font-family:'JetBrains Mono',monospace; font-size:.72rem; font-weight:700; color:#C8901C;
  background:rgba(200,144,28,.10); border:1px solid rgba(200,144,28,.30); border-radius:8px; padding:3px 9px; }
.ae-paso h3 { font-family:'Fraunces',serif; font-weight:600; font-size:1.35rem; color:#0C1A2E; margin:0; letter-spacing:-.01em; }
.ae-sub { color:#5A7391; font-size:.92rem; line-height:1.6; margin:0 0 14px; }

/* chips de validación */
.ae-chk { display:flex; align-items:flex-start; gap:9px; font-size:.86rem; line-height:1.5; color:#1A2B45;
  background:#fff; border:1px solid #DDE6F0; border-left-width:3px; border-radius:10px; padding:8px 13px; margin-bottom:7px; }
.ae-chk.ok   { border-left-color:#28B088; }
.ae-chk.warn { border-left-color:#C8901C; background:#FDFAF3; }
.ae-chk.error{ border-left-color:#E05252; background:#FDF4F4; }
.ae-chk .ic { font-family:'JetBrains Mono',monospace; font-weight:700; font-size:.8rem; }
.ae-chk.ok .ic { color:#28B088; } .ae-chk.warn .ic { color:#C8901C; } .ae-chk.error .ic { color:#E05252; }

/* tarjetas KPI */
.ae-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin:18px 0 6px; }
@media (max-width:760px){ .ae-kpis{ grid-template-columns:1fr 1fr; } }
.ae-kpi { background:#fff; border:1px solid #DDE6F0; border-radius:14px; padding:16px 18px; box-shadow:0 4px 24px rgba(12,26,46,.06); }
.ae-kpi .v { font-family:'JetBrains Mono',monospace; font-size:1.35rem; font-weight:500; color:#0C1A2E; }
.ae-kpi .v.gold { color:#C8901C; } .ae-kpi .v.teal { color:#28B088; }
.ae-kpi .l { font-size:.64rem; color:#5A7391; text-transform:uppercase; letter-spacing:.09em; margin-top:3px; }

/* widgets streamlit */
.stButton>button, .stDownloadButton>button { border-radius:11px; font-weight:600; padding:.55rem 1.5rem; border:1px solid #DDE6F0; }
.stButton>button[kind="primary"] { background:#0C1A2E; border-color:#0C1A2E; color:#fff; box-shadow:0 6px 20px rgba(12,26,46,.25); }
.stButton>button[kind="primary"]:hover { background:#1A2B45; border-color:#1A2B45; }
.stDownloadButton>button { background:linear-gradient(135deg,#C8901C,#E8B440); border:none; color:#fff; box-shadow:0 6px 20px rgba(200,144,28,.30); }
[data-testid="stFileUploader"] section { border:1.5px dashed #C9D6E6; border-radius:14px; background:#FBFCFE; }
[data-testid="stExpander"] { border:1px solid #DDE6F0; border-radius:14px; background:#fff; box-shadow:0 4px 24px rgba(12,26,46,.05); margin-bottom:10px; }
[data-testid="stExpander"] summary { font-weight:600; color:#0C1A2E; }
[data-testid="stDataFrame"] { border:1px solid #DDE6F0; border-radius:12px; overflow:hidden; }
div[role="radiogroup"] label { background:#fff; border:1px solid #DDE6F0; border-radius:100px; padding:6px 16px; margin-right:6px; }
.stSlider [data-baseweb="slider"] div[role="slider"] { background:#C8901C; }
</style>
"""

def _paso(st, n, titulo, sub=None):
    st.markdown(f'<div class="ae-paso"><span class="n">PASO {n}</span><h3>{titulo}</h3></div>',
                unsafe_allow_html=True)
    if sub:
        st.markdown(f'<p class="ae-sub">{sub}</p>', unsafe_allow_html=True)

def _checks_html(checks):
    ic = {"ok": "✓", "warn": "!", "error": "✕"}
    return "".join(f'<div class="ae-chk {n}"><span class="ic">{ic[n]}</span><span>{m}</span></div>'
                   for n, m in checks)

def _kpis_html(items):
    """items: lista de (valor, etiqueta, clase_color)"""
    cards = "".join(f'<div class="ae-kpi"><div class="v {c}">{v}</div><div class="l">{l}</div></div>'
                    for v, l, c in items)
    return f'<div class="ae-kpis">{cards}</div>'


def main_app():
    import streamlit as st

    st.set_page_config(page_title="Forecast | automatizaesto", page_icon="📈",
                       layout="wide", initial_sidebar_state="collapsed")
    _setup_plotly_brand()
    st.markdown(_CSS, unsafe_allow_html=True)

    # ---- Topbar de marca ----
    st.markdown(
        '<div class="ae-topbar">'
        '<div class="ae-logo">F</div>'
        '<div class="ae-name">Forecast<small>by automatizaesto · cualquier negocio, cualquier formato de datos</small></div>'
        '<span class="ae-beta">● Beta</span>'
        '</div>', unsafe_allow_html=True)

    # ---- Paso 1: Rol ----
    _paso(st, 1, "¿Cuál es tu rol?",
          "Los hallazgos se redactan en tu lenguaje: decisiones para gerencia, detalle técnico para análisis.")
    rol = st.radio("Rol", ["Gerente / Dueño de negocio", "Analista / Planner", "Operaciones / Logística"],
                   horizontal=True, key="rol", label_visibility="collapsed")

    # ---- Paso 2: Carga ----
    _paso(st, 2, "Carga tus datos",
          "Excel o CSV con al menos una columna de fecha y una numérica a proyectar. "
          "Opcional: columna de serie (cliente, producto, mercado, campaña…).")
    archivo = st.file_uploader("Archivo", type=["xlsx", "xls", "csv"], key="archivo",
                               label_visibility="collapsed")
    if not archivo:
        st.markdown('<p class="ae-sub">Sube un archivo para continuar — tus datos no salen de esta sesión.</p>',
                    unsafe_allow_html=True)
        st.stop()

    df = (pd.read_csv(archivo) if archivo.name.endswith(".csv")
          else pd.read_excel(archivo))
    with st.expander(f"Vista previa — {archivo.name} ({len(df):,} filas)", expanded=False):
        st.dataframe(df.head(8), use_container_width=True)

    # ---- Paso 3: Mapeo asistido ----
    _paso(st, 3, "Mapeo de columnas",
          "Detectamos automáticamente qué columna es qué. Confirma o corrige antes de seguir.")
    sug = detectar_columnas(df)
    cols = list(df.columns)
    c1, c2, c3 = st.columns(3)
    col_fecha = c1.selectbox("Fecha", cols,
                             index=cols.index(sug["fecha"]) if sug["fecha"] in cols else 0, key="col_fecha")
    col_valor = c2.selectbox("Valor a proyectar", cols,
                             index=cols.index(sug["valor"]) if sug["valor"] in cols else 0, key="col_valor")
    op_serie = ["(sin serie - una sola)"] + cols
    col_serie = c3.selectbox("Serie (opcional)", op_serie,
                             index=op_serie.index(sug["serie"]) if sug["serie"] in op_serie else 0, key="col_serie")

    # ---- Paso 4: Prevalidacion ----
    _paso(st, 4, "Validación de datos",
          "Antes de modelar, revisamos fechas, nulos, duplicados, vacíos y frecuencia.")
    res, checks = prevalidar(df, col_fecha, col_valor,
                             None if col_serie == "(sin serie - una sola)" else col_serie)
    st.markdown(_checks_html(checks), unsafe_allow_html=True)
    if res is None:
        st.stop()
    limpio, meta = res

    # ---- Paso 5: Ejecutar ----
    _paso(st, 5, "Horizonte y ejecución",
          f"Frecuencia detectada: <b>{meta['freq_nombre']}</b> · Motor activo: <b>{MOTOR_INFO}</b>")
    horizonte = st.slider("Horizonte a proyectar (periodos)",
                          4, meta["season"], min(16, meta["season"]), key="horizonte")
    firma = (archivo.name, col_fecha, col_valor, col_serie, horizonte)
    if st.button("Generar forecast →", type="primary", key="btn_run"):
        with st.spinner("Compitiendo modelos con validación walk-forward sobre tu historia real…"):
            st.session_state["resultados"] = entrenar_y_competir(limpio, meta, horizonte)
            st.session_state["firma"] = firma
    if "resultados" not in st.session_state:
        st.stop()
    if st.session_state.get("firma") != firma:
        st.warning("Cambiaste datos o parámetros: vuelve a ejecutar el forecast.")
        st.stop()
    tabla, mejores, forecast, cv = st.session_state["resultados"]

    # ---- Resumen ejecutivo (KPIs) ----
    mejor_global = tabla.loc[tabla.groupby("serie")["WAPE_%"].idxmin()]
    wape_prom = mejor_global["WAPE_%"].mean()
    tot_fc = forecast["Forecast"].sum()
    n_series = forecast["unique_id"].nunique()
    st.markdown(_kpis_html([
        (f"{tot_fc:,.0f}", f"Total proyectado · {horizonte} per. {meta['freq_nombre']}s", "gold"),
        (f"{wape_prom:.1f}%", "Error de validación (WAPE)", "teal" if wape_prom < 15 else ""),
        (f"{n_series}", "Series modeladas", ""),
        (f"{len(cv):,}", "Predicciones validadas vs real", ""),
    ]), unsafe_allow_html=True)

    ganadores = "; ".join(f"**{u}** → {' + '.join(m)}" for u, m in mejores.items())
    st.success(f"Modelo ganador por serie (validado contra tu propia historia): {ganadores}")
    with st.expander("Ranking completo de modelos (WAPE %, menor = mejor)"):
        st.dataframe(tabla, use_container_width=True)

    # ---- Paso 6: Insights ----
    _paso(st, 6, "Hallazgos",
          "Máximo 10, ordenados por relevancia y redactados para tu rol. Cada gráfica es interactiva.")
    insights = generar_insights(limpio, meta, tabla, mejores, forecast, cv, rol)
    for i, item in enumerate(insights, 1):
        with st.expander(f"{i} · {item['titulo']}", expanded=(i <= 3)):
            st.write(item["texto"])
            if item["fig"] is not None:
                st.plotly_chart(item["fig"], use_container_width=True)

    # ---- Descarga ----
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        forecast.rename(columns={"unique_id": "serie", "ds": "periodo"}).to_excel(
            xw, sheet_name="forecast", index=False)
        tabla.to_excel(xw, sheet_name="metricas", index=False)
        pd.DataFrame([{"insight": f"{i+1}. {x['titulo']}", "detalle": x["texto"]}
                      for i, x in enumerate(insights)]).to_excel(
            xw, sheet_name="insights", index=False)
    st.download_button("Descargar resultados en Excel ↓", buf.getvalue(),
                       "resultados_forecast.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    main_app()
