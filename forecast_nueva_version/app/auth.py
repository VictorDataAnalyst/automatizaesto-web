# =====================================================================
# Autenticación — valida el JWT que emite Supabase Auth.
# En MODO_DEMO no hay login: usuario_actual() devuelve un usuario ficticio
# para que la app siga corriendo en local sin Supabase.
# =====================================================================
import jwt
from fastapi import Header, HTTPException

import config

# Usuario de demo (sin login). org_id estable para que el flujo demo persista.
DEMO_USER = {"user_id": "00000000-0000-0000-0000-000000000000",
             "email": "demo@local", "modo": "demo"}


def _token_de_header(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Falta el token de sesión (Authorization: Bearer …).")
    return authorization.split(" ", 1)[1].strip()


def verificar_jwt(token: str) -> dict:
    """Valida firma + expiración del JWT de Supabase (HS256 con el JWT secret).
    Devuelve {user_id, email}. Lanza 401 si es inválido o expiró."""
    try:
        payload = jwt.decode(
            token, config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"], audience="authenticated",
        )
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
