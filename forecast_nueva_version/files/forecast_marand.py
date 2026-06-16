# =====================================================================
# SISTEMA DE FORECAST DE EXPORTACIÓN - MARAND COMPANY (PALTA HASS)
# Stack: Nixtla StatsForecast + MLForecast (LightGBM) + Ensamble
# Autor: Victor Cardeña Denegri | automatizaesto.com
# ---------------------------------------------------------------------
# Por qué este stack y no Prophet/ARIMA solos:
#  - LightGBM con features de calendario/campaña ganó M5 (Walmart) y es
#    el estándar actual en retail/agro-export.
#  - StatsForecast (AutoARIMA, AutoETS, MSTL) da baselines estadísticos
#    sólidos, 100x más rápidos que statsmodels.
#  - El ensamble (promedio de los 2 mejores en validación) reduce el
#    riesgo de que un solo modelo falle en cambio de régimen.
#  - Métrica principal: WAPE (no MAPE). La palta es hiperestacional:
#    semanas con ~0 TM fuera de campaña hacen que el MAPE explote y
#    el modelo "parezca" malo aunque acierte en volumen total.
# =====================================================================

import warnings, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS, MSTL, SeasonalNaive
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, ExpandingMean
import lightgbm as lgb

warnings.filterwarnings("ignore")

# ---------------- CONFIG ----------------
class Config:
    INPUT_XLSX   = "plantilla_datos_marand.xlsx"   # <- reemplazar con datos reales
    SHEET        = "exportaciones"
    FREQ         = "W-SUN"      # semanal (cierre domingo). Cambiar a "MS" si es mensual
    SEASON       = 52           # 52 si semanal, 12 si mensual
    HORIZON      = 16           # semanas a proyectar (≈ 4 meses)
    N_WINDOWS    = 4            # ventanas walk-forward de validación
    LEVEL        = [80, 95]     # intervalos de confianza
    OUT_XLSX     = "resultados_forecast_marand.xlsx"
    OUT_PLOT     = "forecast_marand.png"

# ---------------- MÉTRICAS ----------------
def wape(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(np.abs(y - yhat)) / max(np.sum(np.abs(y)), 1e-9)

def bias_pct(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    return 100 * np.sum(yhat - y) / max(np.sum(np.abs(y)), 1e-9)

def rmse(y, yhat):
    return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(yhat, float)) ** 2)))

# ---------------- CARGA DE DATOS ----------------
def cargar_datos(path):
    """Espera columnas: fecha | serie | toneladas  (+ exógenas opcionales:
    precio_fob_usd_kg, semana_campana). 'serie' puede ser mercado destino
    (EEUU, Europa, Asia) o producto. El sistema es multi-serie nativo."""
    df = pd.read_excel(path, sheet_name=Config.SHEET)
    df = df.rename(columns={"fecha": "ds", "serie": "unique_id", "toneladas": "y"})
    df["ds"] = pd.to_datetime(df["ds"])
    df = df.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    return df

# ---------------- FEATURES DE CAMPAÑA (dominio agro-export) ----------------
def agregar_features(df):
    out = df.copy()
    out["semana"] = out["ds"].dt.isocalendar().week.astype(int)
    out["mes"] = out["ds"].dt.month
    # Ventana de campaña Hass Perú: abr-ago (pico jun-jul)
    out["en_campana"] = out["mes"].between(4, 8).astype(int)
    out["pico_campana"] = out["mes"].isin([6, 7]).astype(int)
    # Codificación cíclica de la semana (mejor que dummies para GBM)
    out["sin_w"] = np.sin(2 * np.pi * out["semana"] / 52)
    out["cos_w"] = np.cos(2 * np.pi * out["semana"] / 52)
    return out

FEATURES_EXOGENAS = ["semana", "mes", "en_campana", "pico_campana", "sin_w", "cos_w"]

# ---------------- MODELOS ----------------
def construir_modelos():
    sf = StatsForecast(
        models=[
            # MSTL descompone la estacionalidad y proyecta la tendencia con
            # ARIMA no estacional: misma precision, 50x mas rapido que
            # AutoARIMA(season_length=52)
            MSTL(season_length=Config.SEASON, trend_forecaster=AutoARIMA()),
            AutoETS(season_length=Config.SEASON),
            SeasonalNaive(season_length=Config.SEASON),  # baseline honesto
        ],
        freq=Config.FREQ,
        n_jobs=-1,
    )
    mlf = MLForecast(
        models={
            "LightGBM": lgb.LGBMRegressor(
                n_estimators=600, learning_rate=0.05, num_leaves=31,
                min_child_samples=10, subsample=0.9, colsample_bytree=0.9,
                random_state=42, verbosity=-1,
            )
        },
        freq=Config.FREQ,
        lags=[1, 2, 3, 4, 8, 12, 26, 52],
        lag_transforms={
            1: [RollingMean(window_size=4), RollingMean(window_size=12), ExpandingMean()],
            52: [RollingMean(window_size=4)],
        },
        date_features=["week", "month"],
    )
    return sf, mlf

# ---------------- VALIDACIÓN WALK-FORWARD ----------------
def validar(df_feat, sf, mlf):
    h, n_w = Config.HORIZON, Config.N_WINDOWS
    cv_sf = sf.cross_validation(df=df_feat[["unique_id", "ds", "y"]],
                                h=h, n_windows=n_w, step_size=h // 2)
    cv_ml = mlf.cross_validation(df=df_feat[["unique_id", "ds", "y"] + FEATURES_EXOGENAS],
                                 h=h, n_windows=n_w, step_size=h // 2,
                                 static_features=[])
    cv = cv_sf.merge(cv_ml.drop(columns=["y"]), on=["unique_id", "ds", "cutoff"])

    modelos = ["MSTL", "AutoETS", "SeasonalNaive", "LightGBM"]
    filas = []
    for uid, g in cv.groupby("unique_id"):
        for m in modelos:
            filas.append({
                "serie": uid, "modelo": m,
                "WAPE_%": round(wape(g["y"], g[m]), 2),
                "BIAS_%": round(bias_pct(g["y"], g[m]), 2),
                "RMSE_TM": round(rmse(g["y"], g[m]), 1),
            })
    tabla = pd.DataFrame(filas).sort_values(["serie", "WAPE_%"])

    # Seleccion honesta por serie: se prueba el ensamble de los 2 mejores
    # (incluido el baseline) y se usa SOLO si supera al mejor individual en CV
    mejores, filas_ens = {}, []
    for uid, g_cv in cv.groupby("unique_id"):
        rank = tabla[tabla.serie == uid].nsmallest(2, "WAPE_%")
        top2 = rank["modelo"].tolist()
        wape_best = rank["WAPE_%"].iloc[0]
        ens = g_cv[top2].mean(axis=1)
        wape_ens = wape(g_cv["y"], ens)
        if wape_ens < wape_best:
            mejores[uid] = top2
            etiqueta = f"ENSAMBLE({'+'.join(top2)}) [ELEGIDO]"
        else:
            mejores[uid] = [top2[0]]
            etiqueta = f"ENSAMBLE({'+'.join(top2)}) [descartado, gana {top2[0]}]"
        filas_ens.append({
            "serie": uid, "modelo": etiqueta,
            "WAPE_%": round(wape_ens, 2),
            "BIAS_%": round(bias_pct(g_cv["y"], ens), 2),
            "RMSE_TM": round(rmse(g_cv["y"], ens), 1),
        })
    tabla = pd.concat([tabla, pd.DataFrame(filas_ens)]).sort_values(["serie", "WAPE_%"])
    return tabla.reset_index(drop=True), mejores, cv

# ---------------- FORECAST FINAL ----------------
def proyectar(df_feat, sf, mlf, mejores):
    h = Config.HORIZON
    fc_sf = sf.forecast(df=df_feat[["unique_id", "ds", "y"]], h=h, level=Config.LEVEL)

    mlf.fit(df_feat[["unique_id", "ds", "y"] + FEATURES_EXOGENAS], static_features=[])
    futuro = mlf.make_future_dataframe(h=h)
    futuro = agregar_features(futuro)
    fc_ml = mlf.predict(h=h, X_df=futuro[["unique_id", "ds"] + FEATURES_EXOGENAS])

    fc = fc_sf.merge(fc_ml, on=["unique_id", "ds"])
    partes = []
    for uid, g in fc.groupby("unique_id"):
        g = g.copy()
        g["Forecast_TM"] = g[mejores[uid]].mean(axis=1).clip(lower=0)
        # Intervalos: tomamos los del mejor modelo estadístico disponible
        stat = next((m for m in mejores[uid] if m != "LightGBM"), "MSTL")
        for lvl in Config.LEVEL:
            lo, hi = f"{stat}-lo-{lvl}", f"{stat}-hi-{lvl}"
            if lo in g.columns:
                g[f"Lo_{lvl}"] = g[lo].clip(lower=0)
                g[f"Hi_{lvl}"] = g[hi]
        partes.append(g[["unique_id", "ds", "Forecast_TM"]
                        + [c for c in g.columns if c.startswith(("Lo_", "Hi_"))]])
    return pd.concat(partes).rename(columns={"unique_id": "serie", "ds": "semana"})

# ---------------- VISUALIZACIÓN ----------------
def graficar(df, forecast, path):
    series = df["unique_id"].unique()
    fig, axes = plt.subplots(len(series), 1, figsize=(13, 4 * len(series)), squeeze=False)
    for ax, uid in zip(axes.ravel(), series):
        h = df[df.unique_id == uid].tail(120)
        f = forecast[forecast.serie == uid]
        ax.plot(h["ds"], h["y"], color="#2c3e50", lw=1.4, label="Histórico (TM)")
        ax.plot(f["semana"], f["Forecast_TM"], color="#e74c3c", lw=2, label="Forecast ensamble")
        if "Lo_80" in f.columns:
            ax.fill_between(f["semana"], f["Lo_80"], f["Hi_80"], color="#e74c3c", alpha=0.18, label="IC 80%")
        ax.set_title(f"Marand Company - Exportación palta Hass | {uid}", fontsize=12, fontweight="bold")
        ax.set_ylabel("Toneladas/semana"); ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(path, dpi=130); plt.close()

# ---------------- MAIN ----------------
def main():
    df = cargar_datos(Config.INPUT_XLSX)
    df_feat = agregar_features(df)
    sf, mlf = construir_modelos()

    print(">> Validación walk-forward...")
    tabla, mejores, _ = validar(df_feat, sf, mlf)
    print(tabla.to_string(index=False))

    print("\n>> Forecast final (próximas %d semanas)..." % Config.HORIZON)
    forecast = proyectar(df_feat, sf, mlf, mejores)

    graficar(df, forecast, Config.OUT_PLOT)

    with pd.ExcelWriter(Config.OUT_XLSX, engine="openpyxl") as xw:
        forecast.to_excel(xw, sheet_name="forecast", index=False)
        tabla.to_excel(xw, sheet_name="metricas_validacion", index=False)
        resumen = forecast.groupby("serie")["Forecast_TM"].sum().round(0).reset_index()
        resumen.columns = ["serie", f"Total_TM_proximas_{Config.HORIZON}_semanas"]
        resumen.to_excel(xw, sheet_name="resumen_ejecutivo", index=False)
    print(f"\nOK -> {Config.OUT_XLSX} | {Config.OUT_PLOT}")

if __name__ == "__main__":
    main()
