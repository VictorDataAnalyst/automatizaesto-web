# Forecast Universal — automatizaesto.com

App de forecasting para cualquier negocio (agro-export, BPO, retail, servicios)
y cualquier formato de datos. Detecta columnas, valida, compite 4 modelos
(MSTL+AutoARIMA, AutoETS, SeasonalNaive, LightGBM) con validación walk-forward,
elige el mejor (o ensamble si gana en validación) y genera hasta 10 insights
con gráficas, adaptados al rol del usuario.

## Instalación
```
pip install -r requirements_forecast.txt
```

## Ejecución
```
streamlit run app_forecast_universal.py
```
Se abre en el navegador (http://localhost:8501).

## Identidad visual
La app usa la identidad de ForecastMYPE (paleta navy/gold/teal, tipografías
Fraunces + Inter Tight + JetBrains Mono, la misma que la landing de
automatizaesto.com/forecast): topbar de marca, pasos numerados, chips de
validación, tarjetas KPI y gráficas Plotly con plantilla propia. El tema base
se define en `.streamlit/config.toml` (mantener esa carpeta junto al .py).

## Flujo
1. **Rol** — Gerente, Analista u Operaciones (cambia el lenguaje de los insights).
2. **Carga** — Excel o CSV. Mínimo: una columna de fecha y una numérica.
3. **Mapeo asistido** — la app sugiere fecha/valor/serie; el usuario confirma o corrige.
4. **Prevalidación** — fechas, nulos, duplicados, negativos, gaps, frecuencia
   (diaria/semanal/mensual/trimestral detectada automáticamente), historia mínima.
5. **Modelos** — competencia con walk-forward; métrica WAPE (robusta con ceros);
   el ensamble top-2 solo se usa si supera al mejor individual.
6. **Insights** — máx. 10: mejor modelo, proyección total, estacionalidad,
   tendencia, anomalías, volatilidad, concentración Pareto, sesgo,
   valor vs baseline naive, rango de planificación IC 80%. Excel descargable.

## Motor con fallback automático (portabilidad)
La app detecta si están instaladas las librerías de Nixtla:
- **Si están** → motor completo (MSTL+AutoARIMA, AutoETS, SeasonalNaive, LightGBM).
- **Si NO están** → motor portable (LightGBM + Holt-Winters + SeasonalNaive),
  sin dependencias de compilación. La app **nunca se cae por un import**.
El motor activo se muestra en pantalla (paso 5). Resultados casi idénticos
entre ambos: en Ubycall, WAPE 7.6 % vs 6.7 % por campaña.

Para forzar el motor completo (recomendado en tu PC de desarrollo):
```
python -m pip install statsforecast mlforecast lightgbm statsmodels
```

## Validado con datos reales
- Ubycall (BPO, diario): WAPE 6.7–19% por campaña.
- Marand (palta, semanal): WAPE 15–18% por mercado.
