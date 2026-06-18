# AgroQuality — imagen de producción (backend FastAPI + frontend estático).
# El runtime NO usa conexión directa a Postgres (solo REST/Storage/JWKS de
# Supabase), por eso las Network Restrictions del proyecto no lo afectan.
FROM python:3.12-slim

WORKDIR /app

# Dependencias primero (mejor caché de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código de la app
COPY . .

# La plataforma de hosting suele inyectar $PORT; por defecto 8603.
ENV PORT=8603
EXPOSE 8603

# Las credenciales Supabase se pasan como variables de entorno del host
# (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET,
#  AGROQUALITY_BUCKET). NO se hornea el .env en la imagen (ver .dockerignore).
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8603}"]
