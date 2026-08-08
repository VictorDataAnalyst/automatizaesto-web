# Prueba de humo contra el Supabase REAL: escribe y borra sus propios datos.
# Verifica lo que el simulador no puede: red, credenciales, RLS, Storage.
import sys
import uuid
from pathlib import Path

APP = Path(r"C:\Users\USER\Desktop\Marand\Proyecto_Geolocalizacion\Automatizaesto_Deploy\forecast_nueva_version\app")
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP.parent / "files"))

import config                                                    # noqa: E402
import httpx                                                     # noqa: E402
from db import DB                                                # noqa: E402

assert config.MODO == "saas", config.MODO
print(f"modo: {config.MODO} | backend: {type(DB).__name__}\n")

H = {"apikey": config.SUPABASE_SERVICE_KEY,
     "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
     "Content-Type": "application/json"}
REST = f"{config.SUPABASE_URL}/rest/v1"
creados = {"orgs": [], "datasets": [], "corridas": []}
fallos = []


def ok(msg, extra=""):
    print(f"  [OK]    {msg}" + (f" -> {extra}" if extra else ""))


def mal(msg, e):
    fallos.append((msg, str(e)))
    print(f"  [FALLA] {msg} -> {e}")


def crear_org(nombre):
    r = httpx.post(f"{REST}/orgs", headers={**H, "Prefer": "return=representation"},
                   json={"nombre": nombre}, timeout=30)
    r.raise_for_status()
    o = r.json()[0]
    creados["orgs"].append(o["id"])
    return o["id"]


# ---------------------------------------------------------------
print("1. Crear dos organizaciones de prueba")
try:
    sufijo = uuid.uuid4().hex[:6]
    orgA = crear_org(f"ZZ-prueba-A-{sufijo}")
    orgB = crear_org(f"ZZ-prueba-B-{sufijo}")
    ok("orgs creadas", f"A={orgA[:8]}… B={orgB[:8]}…")
except Exception as e:                                            # noqa: BLE001
    mal("crear orgs", e)
    raise SystemExit(1)

# ---------------------------------------------------------------
print("\n2. Datasets + Storage (subir y bajar de verdad)")
try:
    ds = DB.crear_dataset(orgA, {"nombre": "prueba.csv", "storage_path": "",
                                 "filas": 3, "columnas": {"fecha": "fecha"},
                                 "rubro": "General", "creado_por": None})
    creados["datasets"].append(ds["id"])
    contenido = b"fecha,valor\n2026-01-01,10\n2026-01-02,12\n"
    path = DB.subir_archivo(orgA, ds["id"], contenido, "prueba.csv")
    ok("archivo subido a Storage", path)
    vuelta = DB.bajar_archivo(path)
    if vuelta == contenido:
        ok("archivo descargado idéntico", f"{len(vuelta)} bytes")
    else:
        mal("descarga", f"contenido distinto: {vuelta[:40]}")
except Exception as e:                                            # noqa: BLE001
    mal("datasets/storage", e)

# ---------------------------------------------------------------
print("\n3. AISLAMIENTO — la org B no debe ver nada de la A")
try:
    propio = DB.get_dataset(orgA, ds["id"])
    ajeno = DB.get_dataset(orgB, ds["id"])
    if propio and not ajeno:
        ok("get_dataset aísla correctamente", "A lo ve, B no")
    else:
        mal("AISLAMIENTO ROTO en get_dataset",
            f"A={'ve' if propio else 'no ve'} / B={'VE (mal)' if ajeno else 'no ve'}")
except Exception as e:                                            # noqa: BLE001
    mal("aislamiento datasets", e)

# ---------------------------------------------------------------
print("\n4. Corridas, informes y perfil")
try:
    c = DB.crear_corrida(orgA, ds["id"], {"rol": "gerente", "horizonte": 6})
    creados["corridas"].append(c["id"])
    DB.guardar_informe(orgA, c["id"], {"kpis": {"total_fmt": "1 000"},
                                       "chart_principal": {"series": []}})
    ok("corrida creada y informe guardado", c["id"][:8] + "…")

    hist_a = DB.historial(orgA)
    hist_b = DB.historial(orgB)
    if len(hist_a) >= 1 and not any(x["id"] == c["id"] for x in hist_b):
        ok("historial aislado", f"A={len(hist_a)} corrida(s), B no la ve")
    else:
        mal("AISLAMIENTO ROTO en historial", f"B ve {len(hist_b)}")

    prev = DB.informes_previos(orgA)
    ok("informes_previos", f"{len(prev)} con informe")

    DB.guardar_perfil(orgA, {"n_corridas": 1, "identidad": {"nombre": "Prueba"}})
    p = DB.get_perfil(orgA)
    if p.get("n_corridas") == 1 and DB.get_perfil(orgB) == {}:
        ok("perfil guardado y aislado")
    else:
        mal("perfil", f"A={p} B={DB.get_perfil(orgB)}")
except Exception as e:                                            # noqa: BLE001
    mal("corridas/perfil", e)

# ---------------------------------------------------------------
print("\n5. Eventos y cuota (migración 004)")
try:
    DB.registrar_evento(orgA, "informe_generado", {"rol": "gerente"})
    ev_a, ev_b = DB.eventos(orgA), DB.eventos(orgB)
    if ev_a and not ev_b:
        ok("evento registrado y aislado", f"A={len(ev_a)} B={len(ev_b)}")
    else:
        mal("eventos", f"A={len(ev_a)} B={len(ev_b)}")
    n = DB.corridas_desde(orgA, "1970-01-01T00:00:00+00:00")
    ok("conteo de cuota (content-range)", f"{n} corridas")
except Exception as e:                                            # noqa: BLE001
    mal("eventos", e)

# ---------------------------------------------------------------
print("\n6. Insights guardados")
try:
    g = DB.guardar_insight(orgA, c["id"], {"titulo": "Prueba"}, "nota", None)
    if DB.listar_guardados(orgA) and not DB.listar_guardados(orgB):
        ok("insight guardado y aislado")
    else:
        mal("insights", "aislamiento")
    DB.borrar_guardado(orgA, g["id"])
    ok("insight borrado")
except Exception as e:                                            # noqa: BLE001
    mal("insights", e)

# ---------------------------------------------------------------
print("\n7. Vista contactos_marketing: NO debe ser legible por clientes")
try:
    clave = config.SUPABASE_ANON_KEY
    # PRIMERO comprobar que la clave anon es VALIDA. Sin esto, un 401 por
    # clave invalida se confundia con "acceso correctamente denegado" y la
    # prueba de seguridad pasaba sin haber comprobado nada.
    val = httpx.get(f"{config.SUPABASE_URL}/auth/v1/settings",
                    headers={"apikey": clave}, timeout=30)
    if val.status_code != 200:
        mal("la clave anon no es valida: la prueba de fuga no significa nada",
            f"HTTP {val.status_code} — revisa SUPABASE_ANON_KEY")
    else:
        ok("clave anon valida (la prueba siguiente si tiene sentido)")
        cab = {"apikey": clave, "Authorization": f"Bearer {clave}"}
        # Control: con esa misma clave, una tabla normal responde 200.
        ctrl = httpx.get(f"{REST}/orgs", headers=cab, params={"limit": "1"}, timeout=30)
        r = httpx.get(f"{REST}/contactos_marketing", headers=cab,
                      params={"limit": "1"}, timeout=30)
        if r.status_code in (401, 403, 404) or r.json() == []:
            ok("'anon' NO puede leer la lista de contactos",
               f"HTTP {r.status_code} (control sobre orgs: {ctrl.status_code})")
        else:
            mal("FUGA: 'anon' lee contactos_marketing", r.text[:80])
    r = httpx.get(f"{REST}/contactos_marketing", headers=H, params={"limit": "1"}, timeout=30)
    ok("service key sí puede leerla", f"HTTP {r.status_code}")
except Exception as e:                                            # noqa: BLE001
    mal("contactos_marketing", e)

# ---------------------------------------------------------------
print("\n8. Limpieza (borrar todo lo de prueba)")
try:
    for oid in creados["orgs"]:
        httpx.delete(f"{REST}/orgs", headers=H, params={"id": f"eq.{oid}"}, timeout=30)

    # El archivo de Storage NO cae por cascada al borrar la org.
    # OJO: DELETE /object/{bucket}/{path} devuelve 400 aqui y deja el archivo.
    # El que funciona es el borrado por lotes con {"prefixes": [...]}.
    S = f"{config.SUPABASE_URL}/storage/v1"
    httpx.request("DELETE", f"{S}/object/{config.STORAGE_BUCKET}",
                  headers=H, json={"prefixes": [path]}, timeout=30)

    # Verificar de VERDAD que no quedo nada (antes se asumia y era falso).
    resto = httpx.get(f"{REST}/orgs", headers=H,
                      params={"select": "id,nombre", "nombre": "like.ZZ-prueba-%"},
                      timeout=30).json()
    aun = httpx.get(f"{S}/object/{config.STORAGE_BUCKET}/{path}", headers=H, timeout=30)
    if resto:
        mal("quedaron orgs de prueba", resto)
    elif aun.status_code == 200:
        mal("el archivo de prueba sigue en Storage", path)
    else:
        ok("todo lo de prueba fue eliminado", "orgs y archivo verificados")
except Exception as e:                                            # noqa: BLE001
    mal("limpieza", e)

print("\n" + "=" * 62)
if fallos:
    print(f"FALLOS: {len(fallos)}")
    for n, d in fallos:
        print(f"  - {n}: {d}")
    sys.exit(1)
print("TODO OK CONTRA SUPABASE REAL")
