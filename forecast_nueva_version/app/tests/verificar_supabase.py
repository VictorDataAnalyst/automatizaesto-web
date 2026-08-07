# =====================================================================
# Verifica que Supabase esté listo para el modo SaaS.
# Uso:  python app/tests/verificar_supabase.py
# Dice exactamente qué falta y cómo arreglarlo. NUNCA imprime las claves.
# =====================================================================
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP.parent / "files"))

import config  # noqa: E402

OK, MAL, AVISO = "  [OK]   ", "  [FALTA]", "  [AVISO]"
problemas = []


def falta(msg, arreglo):
    problemas.append((msg, arreglo))
    print(f"{MAL} {msg}")


print("=" * 66)
print("VERIFICACION DE SUPABASE PARA MODO SaaS")
print("=" * 66)

# ---------- 1. Archivo .env ----------
print("\n1. Archivo .env")
env = APP / ".env"
if not env.exists():
    falta("No existe app/.env",
          "Copia app/.env.example como app/.env y llena las claves.")
else:
    print(f"{OK} app/.env encontrado")

# ---------- 2. Variables ----------
print("\n2. Credenciales (no se imprimen los valores)")
if not config.SUPABASE_URL:
    falta("SUPABASE_URL vacio", "Dashboard -> Settings -> API -> Project URL")
else:
    print(f"{OK} SUPABASE_URL -> {config.SUPABASE_URL}")

for nombre, valor, donde in [
    ("SUPABASE_SERVICE_KEY", config.SUPABASE_SERVICE_KEY,
     "Settings -> API Keys -> service_role (o 'secret'). Es SECRETA."),
    ("SUPABASE_ANON_KEY", config.SUPABASE_ANON_KEY,
     "Settings -> API Keys -> anon (o 'publishable'). Es publica."),
]:
    if valor:
        print(f"{OK} {nombre} presente ({len(valor)} caracteres)")
    else:
        falta(f"{nombre} vacio", donde)

print(f"\n  Modo que arrancaria la app: {config.MODO.upper()}")
if config.MODO != "saas":
    falta("La app arrancaria en DEMO, no en SaaS",
          "Faltan SUPABASE_URL y/o SUPABASE_SERVICE_KEY.")
    print("\n" + "=" * 66)
    print("Corrige lo anterior y vuelve a correr esta verificacion.")
    for i, (m, a) in enumerate(problemas, 1):
        print(f"  {i}. {m}\n     -> {a}")
    sys.exit(1)

# ---------- 3. Conexión ----------
import httpx  # noqa: E402

H = {"apikey": config.SUPABASE_SERVICE_KEY,
     "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}"}


def consultar(recurso, params=None):
    url = f"{config.SUPABASE_URL}/rest/v1/{recurso}"
    with httpx.Client(timeout=20) as c:
        return c.get(url, headers=H, params=params or {"limit": "1"})


print("\n3. Conexion")
try:
    r = consultar("orgs")
    if r.status_code == 401:
        falta("Supabase rechaza la clave (401)",
              "La SUPABASE_SERVICE_KEY no es valida o es de otro proyecto.")
        raise SystemExit(1)
    print(f"{OK} Conecta con {config.SUPABASE_URL}")
except httpx.HTTPError as e:
    falta(f"No se puede conectar: {e}",
          "Revisa SUPABASE_URL y tu conexion a internet.")
    raise SystemExit(1)

# ---------- 4. Tablas ----------
print("\n4. Tablas (migraciones 001 y 003)")
for tabla in ["orgs", "miembros", "datasets", "corridas",
              "perfil_org", "insights_guardados"]:
    r = consultar(tabla)
    if r.status_code == 200:
        print(f"{OK} {tabla}")
    else:
        falta(f"Tabla '{tabla}' no existe o no es accesible ({r.status_code})",
              "Aplica 001_saas_schema.sql y 003_aprendizaje_forecast.sql "
              "en Dashboard -> SQL Editor.")

# ---------- 5. Migración 004 ----------
print("\n5. Eventos de uso (migracion 004)")
r = consultar("eventos")
if r.status_code == 200:
    print(f"{OK} eventos")
else:
    falta(f"Tabla 'eventos' no existe ({r.status_code})",
          "Aplica app/supabase/migrations/004_eventos_uso.sql en SQL Editor.")

# ---------- 6. Migración 005 ----------
print("\n6. Lista de contactos (migracion 005)")
r = consultar("contactos_marketing")
if r.status_code == 200:
    print(f"{OK} contactos_marketing")
else:
    falta(f"Vista 'contactos_marketing' no existe ({r.status_code})",
          "Aplica app/supabase/migrations/005_contactos_marketing.sql en SQL Editor.")

# ---------- 7. Storage ----------
print(f"\n7. Bucket de Storage ('{config.STORAGE_BUCKET}')")
try:
    with httpx.Client(timeout=20) as c:
        rb = c.get(f"{config.SUPABASE_URL}/storage/v1/bucket", headers=H)
    if rb.status_code == 200:
        buckets = {b["name"]: b for b in rb.json()}
        b = buckets.get(config.STORAGE_BUCKET)
        if not b:
            falta(f"No existe el bucket '{config.STORAGE_BUCKET}'",
                  f"Dashboard -> Storage -> New bucket -> nombre "
                  f"'{config.STORAGE_BUCKET}', SIN marcar 'Public'.")
            if buckets:
                print(f"         (buckets que si existen: {', '.join(buckets)})")
        elif b.get("public"):
            falta(f"El bucket '{config.STORAGE_BUCKET}' es PUBLICO",
                  "Los archivos de tus clientes quedarian expuestos. "
                  "Dashboard -> Storage -> bucket -> desmarcar 'Public'.")
        else:
            print(f"{OK} '{config.STORAGE_BUCKET}' existe y es privado")
    else:
        print(f"{AVISO} No se pudo listar Storage ({rb.status_code})")
except httpx.HTTPError as e:
    print(f"{AVISO} No se pudo consultar Storage: {e}")

# ---------- 8. Auth ----------
print("\n8. Autenticacion")
if config.SUPABASE_JWT_SECRET:
    print(f"{OK} JWT_SECRET presente (proyecto con firma HS256)")
else:
    print(f"{OK} Sin JWT_SECRET: se validara por JWKS (proyecto moderno)")

# ---------- Resumen ----------
print("\n" + "=" * 66)
if problemas:
    print(f"FALTAN {len(problemas)} COSAS:\n")
    for i, (m, a) in enumerate(problemas, 1):
        print(f"  {i}. {m}")
        print(f"     -> {a}\n")
    print("Esta verificacion NO aplica nada: solo revisa y reporta.")
    print("Las migraciones se corren a mano en Dashboard -> SQL Editor.")
    print("\n(Si lo ejecutas con el depurador veras 'SystemExit: 1'. No es un")
    print(" error: es el codigo de salida que indica 'faltan cosas'.")
    print(" Ejecutalo desde la terminal y no aparece.)")
    sys.exit(1)
print("TODO LISTO. Supabase esta configurado para modo SaaS.")
print("Avisa para correr la prueba completa contra el Supabase real.")
