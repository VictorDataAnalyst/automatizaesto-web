# Forecast — app con frontend propio

Aplicación web completa de Forecast con frontend propio (sin Streamlit):
backend FastAPI + página única con la identidad visual de ForecastMYPE.
El motor de modelos se reutiliza desde `../files/app_forecast_universal.py`
(no se duplica: cualquier mejora al motor beneficia a ambas apps).

## Ejecución
```
pip install -r requirements.txt
python server.py
```
Abre http://localhost:8602

## Flujo (3 pantallas)
1. **Tus datos** — dropzone (drag & drop), plantillas Excel descargables
   (básica y extendida con stock, ambas con datos de ejemplo listos para probar).
2. **Configura** — la app muestra lo que entendió: rubro detectado, mapeo de
   columnas (corregible), validaciones, y **qué análisis puede ofrecer con esas
   columnas** (los bloqueados dicen qué falta). Tres preguntas: rol, país
   (feriados) y horizonte.
3. **Informe ejecutivo** — cifra héroe con variación y veredicto de confianza,
   gráfica principal con banda de confianza 80%, hallazgos como tarjetas
   expandibles con mini-gráficas, anexo técnico y descarga en Excel.

## El rol cambia el informe de verdad
- **Gerente**: orden decisión-primero, lenguaje de negocio, sin jerga.
- **Analista**: + insights exclusivos (valor vs naive, sesgo, anomalías),
  detalle de modelos y validación.
- **Operaciones**: orden capacidad-primero (estacionalidad, rangos, fechas a blindar).
Se puede cambiar de rol desde el propio informe (pestañas) sin re-entrenar.

## Feriados
Vía librería `holidays` (Perú, Colombia, México, Chile, Ecuador, Bolivia,
Argentina, España): lista los feriados dentro del horizonte proyectado y,
en series diarias, calcula el efecto histórico feriado vs día normal.

## Todo en español
Días, meses, narrativa y columnas del Excel exportado
(`serie, periodo, proyeccion, piso_80, techo_80`).

## API
- `POST /api/analizar` — sube archivo → detección de columnas, rubro y propuestas.
- `POST /api/validar` — checks de calidad + frecuencia + horizonte recomendado.
- `POST /api/forecast` — entrena (con caché por horizonte) y devuelve el informe JSON.
- `GET /api/descargar/{token}` — Excel con proyección, métricas y hallazgos.
- `GET /api/plantilla?extendida=true|false` — plantilla Excel con ejemplo.
