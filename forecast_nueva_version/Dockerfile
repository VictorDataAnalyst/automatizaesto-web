# Forecast — imagen de producción.
# Contexto de build: forecast_nueva_version/ (necesita app/ y files/).
FROM python:3.12-slim

# libgomp1: lightgbm lo carga en runtime. Sin esto el build pasa y la app
# revienta al primer forecast con "libgomp.so.1: cannot open shared object file".
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv
COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY files/ ./files/

WORKDIR /srv/app
ENV PORT=8602
EXPOSE 8602

# Railway/Render/Fly asignan el puerto por la variable PORT. Con el puerto fijo
# la plataforma no recibe trafico y el error que muestra no explica por que.
# Se usa `sh -c` para que ${PORT} se expanda en tiempo de ejecucion.
#
# ponytail: UN SOLO worker a propósito. El estado del flujo (limpio/meta/
# resultados) vive en el dict WORKING en RAM; con 2+ workers el usuario valida
# en un proceso y genera en otro -> 409/404 intermitentes. Para escalar de
# verdad hay que mover ese estado a caché compartida (Redis) o recomputarlo.
# Mientras tanto: escala vertical, y varias réplicas SOLO con sesión pegajosa.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8602} --workers 1"]
