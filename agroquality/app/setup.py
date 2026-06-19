# =====================================================================
# AgroQuality — setup de Supabase (uso único, no es parte del runtime).
#   1) Aplica la migración 001_calidad_schema.sql (DDL) vía psycopg2.
#   2) Crea el bucket privado de fotos vía la API de Storage.
#   3) Verifica que las tablas aq_* existan y reporta.
# Lee las credenciales de agroquality/app/.env (NO se commitea).
# Ejecutar:  python setup.py
# =====================================================================
import os
import sys
from pathlib import Path

import httpx

# La consola de Windows (cp1252) no imprime →/✓/…; forzamos UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
MIGRACION = BASE.parent / "supabase" / "migrations" / "001_calidad_schema.sql"


def cargar_env():
    env = BASE / ".env"
    if not env.exists():
        sys.exit("✖ No existe agroquality/app/.env — copia .env.example y rellénalo.")
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def aplicar_migracion(db_url: str):
    import psycopg2
    sql = MIGRACION.read_text(encoding="utf-8")
    print(f"→ Aplicando migración ({MIGRACION.name}, {len(sql)} chars)…")
    with psycopg2.connect(db_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql)
            # Verificación: ¿existen las tablas aq_*?
            cur.execute("""select table_name from information_schema.tables
                           where table_schema='public' and table_name like 'aq_%'
                           order by table_name""")
            tablas = [r[0] for r in cur.fetchall()]
            cur.execute("select count(*) from information_schema.views "
                        "where table_schema='public' and table_name='aq_resumen_inspeccion'")
            vista = cur.fetchone()[0]
    print(f"  ✓ Tablas creadas: {', '.join(tablas) or '(ninguna)'}")
    print(f"  ✓ Vista aq_resumen_inspeccion: {'sí' if vista else 'no'}")
    return tablas


def crear_bucket(url: str, service_key: str, bucket: str):
    h = {"apikey": service_key, "Authorization": f"Bearer {service_key}",
         "Content-Type": "application/json"}
    print(f"→ Creando bucket privado '{bucket}'…")
    with httpx.Client(timeout=20) as c:
        r = c.post(f"{url}/storage/v1/bucket", headers=h,
                   json={"id": bucket, "name": bucket, "public": False})
        if r.status_code in (200, 201):
            print("  ✓ Bucket creado.")
        elif r.status_code == 409 or "already exists" in r.text.lower():
            print("  ✓ El bucket ya existía (ok).")
        else:
            print(f"  ✖ No se pudo crear el bucket: {r.status_code} {r.text}")


def main():
    cargar_env()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service = os.environ.get("SUPABASE_SERVICE_KEY", "")
    db_url = os.environ.get("SUPABASE_DB_URL", "")
    bucket = os.environ.get("AGROQUALITY_BUCKET", "agroquality-fotos")

    faltan = [k for k, v in {"SUPABASE_URL": url, "SUPABASE_SERVICE_KEY": service,
                             "SUPABASE_DB_URL": db_url}.items() if not v]
    if faltan:
        sys.exit(f"✖ Faltan variables en .env: {', '.join(faltan)}")

    print("AgroQuality · setup Supabase")
    print("=" * 40)
    aplicar_migracion(db_url)
    crear_bucket(url, service, bucket)
    print("=" * 40)
    print("✓ Listo. Arranca la app:  python server.py  (ya en modo SaaS)")


if __name__ == "__main__":
    main()
