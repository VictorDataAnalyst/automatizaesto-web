# =====================================================================
# AgroQuality — configuración por variables de entorno.
# Sin credenciales Supabase -> MODO_DEMO (estado en RAM, sin login).
# Con credenciales        -> MODO_SAAS (Auth + persistencia).
# Mismo patrón que forecast_nueva_version/app/config.py.
# =====================================================================
import os
from pathlib import Path

# Carga agroquality/app/.env si existe (sin dependencias externas).
_ENV = Path(__file__).resolve().parent / ".env"
if _ENV.exists():
    for _l in _ENV.read_text(encoding="utf-8").splitlines():
        _l = _l.strip()
        if _l and not _l.startswith("#") and "=" in _l:
            _k, _v = _l.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
# Secreto JWT del proyecto (Dashboard → Settings → API → JWT Secret).
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Bucket privado para las fotos de inspección (galería de pallet / muestra).
STORAGE_BUCKET = os.environ.get("AGROQUALITY_BUCKET", "agroquality-fotos")

# Modo SaaS solo si está todo lo mínimo para auth + persistencia.
MODO_SAAS = bool(SUPABASE_URL and SUPABASE_SERVICE_KEY and SUPABASE_JWT_SECRET)
MODO = "saas" if MODO_SAAS else "demo"
