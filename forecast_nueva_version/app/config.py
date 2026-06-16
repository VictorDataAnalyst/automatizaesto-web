# =====================================================================
# Configuración por variables de entorno.
# Sin credenciales Supabase -> MODO_DEMO (estado en RAM, sin login).
# Con credenciales        -> MODO_SAAS (Auth + persistencia).
# =====================================================================
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
# Secreto JWT del proyecto (Dashboard → Settings → API → JWT Secret).
# Necesario para validar tokens HS256 emitidos por Supabase Auth.
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Bucket privado para los archivos subidos por los clientes.
STORAGE_BUCKET = os.environ.get("FORECAST_BUCKET", "forecast-datasets")

# Modo SaaS solo si está todo lo mínimo para auth + persistencia.
MODO_SAAS = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY and SUPABASE_JWT_SECRET)
MODO = "saas" if MODO_SAAS else "demo"
