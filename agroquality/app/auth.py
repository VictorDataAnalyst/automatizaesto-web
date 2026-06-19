# =====================================================================
# AgroQuality — autenticación. Valida el JWT que emite Supabase Auth.
# En MODO_DEMO no hay login: usuario_actual() devuelve un usuario ficticio.
# Mismo patrón que forecast_nueva_version/app/auth.py.
# =====================================================================
import jwt
from jwt import PyJWKClient
from fastapi import Header, HTTPException

import config

DEMO_USER = {"user_id": "00000000-0000-0000-0000-000000000000",
             "email": "demo@local", "modo": "demo"}

# Supabase moderno firma los JWT con claves asimétricas (ES256/RS256) y publica
# las públicas en un JWKS. Proyectos legacy usan HS256 con el JWT secret.
# Soportamos ambos: detectamos el `alg` del header y validamos según corresponda.
_JWKS_URL = f"{config.SUPABASE_URL}/auth/v1/.well-known/jwks.json" if config.SUPABASE_URL else ""
_jwks_client = PyJWKClient(_JWKS_URL) if _JWKS_URL else None
_ASIMETRICOS = ("ES256", "RS256", "EdDSA")


def _token_de_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Falta el token de sesión (Authorization: Bearer …).")
    return authorization.split(" ", 1)[1].strip()


def verificar_jwt(token: str) -> dict:
    try:
        alg = jwt.get_unverified_header(token).get("alg", "HS256")
        if alg in _ASIMETRICOS:
            if not _jwks_client:
                raise HTTPException(500, "Falta SUPABASE_URL para validar el token (JWKS).")
            clave = _jwks_client.get_signing_key_from_jwt(token).key
            payload = jwt.decode(token, clave, algorithms=list(_ASIMETRICOS),
                                 audience="authenticated", leeway=60)
        else:
            payload = jwt.decode(token, config.SUPABASE_JWT_SECRET,
                                 algorithms=["HS256"], audience="authenticated", leeway=60)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Tu sesión expiró. Vuelve a iniciar sesión.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, f"Token inválido: {e}")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(401, "Token sin identidad de usuario.")
    return {"user_id": sub, "email": payload.get("email"), "modo": "saas"}


def usuario_actual(authorization: str | None = Header(default=None)) -> dict:
    """Dependencia FastAPI. En demo no exige login; en SaaS valida el JWT."""
    if not config.MODO_SAAS:
        return DEMO_USER
    return verificar_jwt(_token_de_header(authorization))
