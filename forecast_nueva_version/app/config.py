# =====================================================================
# Configuración por variables de entorno.
# Sin credenciales Supabase -> MODO_DEMO (estado en RAM, sin login).
# Con credenciales        -> MODO_SAAS (Auth + persistencia).
# =====================================================================
import os
from pathlib import Path

# .env.example dice "cópialo como .env", pero nadie lo leía: crear el archivo
# no hacía nada y la app arrancaba en demo creyendo estar en SaaS.
# ponytail: 6 líneas con stdlib en vez de sumar python-dotenv.
# setdefault -> las variables de entorno reales mandan sobre el archivo.
_ENV = Path(__file__).resolve().parent / ".env"
if _ENV.exists():
    for _linea in _ENV.read_text(encoding="utf-8").splitlines():
        _linea = _linea.split("#", 1)[0].strip()
        if "=" in _linea:
            _k, _, _v = _linea.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
# Secreto JWT — SOLO para proyectos Supabase antiguos que firman con HS256.
# Los proyectos modernos firman con claves asimétricas (ES256/RS256) y publican
# las públicas vía JWKS: ahí NO existe secreto que copiar, y auth.py lo resuelve
# solo con SUPABASE_URL. Por eso es opcional (exigirlo dejaba a los proyectos
# nuevos atrapados en modo demo pese a tener todo bien configurado).
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Bucket privado para los archivos subidos por los clientes.
STORAGE_BUCKET = os.environ.get("FORECAST_BUCKET", "forecast-datasets")

# Lo mínimo imprescindible: a dónde apuntar y con qué escribir.
MODO_SAAS = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)
MODO = "saas" if MODO_SAAS else "demo"
