# Ejercita el backend SaaS (_SaasDB + auth JWT) contra un PostgREST simulado.
# Objetivo: cazar bugs del camino SaaS —que NUNCA se ha ejecutado— sin
# necesitar credenciales reales de Supabase.
import json
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

PUERTO = 8799

# Config ANTES de importar config.py (lee env al importar).
os.environ["SUPABASE_URL"] = f"http://127.0.0.1:{PUERTO}"
os.environ["SUPABASE_SERVICE_KEY"] = "service-key-falsa"
os.environ["SUPABASE_JWT_SECRET"] = "secreto-de-prueba-para-hs256-1234567890"
os.environ["SUPABASE_ANON_KEY"] = "anon-falsa"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = r"C:\Users\USER\Desktop\Marand\Proyecto_Geolocalizacion\Automatizaesto_Deploy\forecast_nueva_version\app"
FILES = r"C:\Users\USER\Desktop\Marand\Proyecto_Geolocalizacion\Automatizaesto_Deploy\forecast_nueva_version\files"
sys.path.insert(0, FILES)
sys.path.insert(0, APP)

RECIBIDO = []          # registro de lo que llegó al "Supabase"


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _responder(self, code, body=b"", headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _leer(self):
        n = int(self.headers.get("Content-Length", 0))
        crudo = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(crudo or b"{}")
        except Exception:
            return crudo

    def do_GET(self):
        ruta = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(ruta.query)
        RECIBIDO.append(("GET", ruta.path, q, self.headers.get("Prefer")))
        tabla = ruta.path.rsplit("/", 1)[-1]

        if ruta.path.startswith("/storage/"):
            return self._responder(200, b"contenido-de-archivo")
        if tabla == "miembros":
            return self._responder(200, json.dumps([{"org_id": "org-1"}]).encode())
        if tabla == "datasets":
            return self._responder(200, json.dumps(
                [{"id": "ds-1", "org_id": "org-1", "nombre": "d.xlsx",
                  "storage_path": "org-1/ds-1/d.xlsx"}]).encode())
        if tabla == "corridas":
            # count=exact -> PostgREST devuelve el total en content-range
            if (self.headers.get("Prefer") or "").find("count=exact") >= 0:
                return self._responder(200, json.dumps([{"id": "c-1"}]).encode(),
                                       {"Content-Range": "0-0/7"})
            sel = q.get("select", [""])[0]
            if "informe" in sel:
                return self._responder(200, json.dumps(
                    [{"id": "c-1", "creado_en": "2026-08-01T00:00:00Z",
                      "informe": {"chart_principal": {"series": []}}},
                     {"id": "c-2", "creado_en": "2026-07-01T00:00:00Z",
                      "informe": None}]).encode())     # <- informe nulo: debe filtrarse
            return self._responder(200, json.dumps(
                [{"id": "c-1", "estado": "lista", "config": {},
                  "creado_en": "2026-08-01T00:00:00Z", "dataset_id": "ds-1"}]).encode())
        if tabla == "perfil_org":
            return self._responder(200, json.dumps([{"perfil": {"n_corridas": 3}}]).encode())
        if tabla == "insights_guardados":
            return self._responder(200, json.dumps(
                [{"id": "g-1", "corrida_id": "c-1", "insight": {}, "nota": None,
                  "creado_en": "2026-08-01T00:00:00Z"}]).encode())
        if tabla == "eventos":
            return self._responder(200, json.dumps(
                [{"tipo": "informe_generado", "meta": {}, "creado_en": "2026-08-01T00:00:00Z"}]).encode())
        return self._responder(404, b"[]")

    def do_POST(self):
        ruta = urllib.parse.urlparse(self.path)
        cuerpo = self._leer()
        RECIBIDO.append(("POST", ruta.path, cuerpo, self.headers.get("Prefer")))
        if ruta.path.startswith("/storage/"):
            return self._responder(200, b'{"Key":"ok"}')
        tabla = ruta.path.rsplit("/", 1)[-1]
        if tabla == "datasets":
            return self._responder(201, json.dumps([{**cuerpo, "id": "ds-1"}]).encode())
        if tabla == "corridas":
            return self._responder(201, json.dumps([{**cuerpo, "id": "c-1"}]).encode())
        if tabla == "insights_guardados":
            return self._responder(201, json.dumps([{**cuerpo, "id": "g-1"}]).encode())
        return self._responder(201, json.dumps([cuerpo]).encode())

    def do_PATCH(self):
        ruta = urllib.parse.urlparse(self.path)
        # El filtro org_id viaja en la QUERY, no en el cuerpo: hay que guardarla.
        RECIBIDO.append(("PATCH", ruta.path, urllib.parse.parse_qs(ruta.query), None))
        return self._responder(204)

    def do_DELETE(self):
        ruta = urllib.parse.urlparse(self.path)
        RECIBIDO.append(("DELETE", ruta.path, urllib.parse.parse_qs(ruta.query), None))
        return self._responder(204)


srv = HTTPServer(("127.0.0.1", PUERTO), Mock)
threading.Thread(target=srv.serve_forever, daemon=True).start()

import config                                                    # noqa: E402
assert config.MODO == "saas", f"deberia arrancar en SaaS, esta en {config.MODO}"
print("modo:", config.MODO)

from db import DB                                                # noqa: E402
print("backend:", type(DB).__name__)
assert type(DB).__name__ == "_SaasDB"

fallos = []


def probar(nombre, fn):
    try:
        r = fn()
        print(f"  OK   {nombre} -> {str(r)[:70]}")
        return r
    except Exception as e:                                        # noqa: BLE001
        fallos.append((nombre, f"{type(e).__name__}: {e}"))
        print(f"  FALLA {nombre} -> {type(e).__name__}: {e}")
        return None


print("\n--- _SaasDB ---")
probar("org_de_usuario", lambda: DB.org_de_usuario("user-1"))
probar("crear_dataset", lambda: DB.crear_dataset("org-1", {
    "nombre": "d.xlsx", "storage_path": "", "filas": 10,
    "columnas": {"fecha": "f"}, "rubro": "General", "creado_por": None}))
probar("get_dataset", lambda: DB.get_dataset("org-1", "ds-1"))
probar("crear_corrida", lambda: DB.crear_corrida("org-1", "ds-1", {"rol": "gerente"}))
probar("guardar_informe", lambda: DB.guardar_informe("org-1", "c-1", {"kpis": {}}))
probar("historial", lambda: DB.historial("org-1"))
probar("get_perfil", lambda: DB.get_perfil("org-1"))
probar("guardar_perfil", lambda: DB.guardar_perfil("org-1", {"n_corridas": 4}))
probar("guardar_insight", lambda: DB.guardar_insight("org-1", "c-1", {"t": 1}, None, None))
probar("listar_guardados", lambda: DB.listar_guardados("org-1"))
probar("borrar_guardado", lambda: DB.borrar_guardado("org-1", "g-1"))
probar("subir_archivo", lambda: DB.subir_archivo("org-1", "ds-1", b"x", "d.xlsx"))
probar("bajar_archivo", lambda: DB.bajar_archivo("org-1/ds-1/d.xlsx"))

print("\n--- métodos NUEVOS (nunca ejecutados en SaaS) ---")
prev = probar("informes_previos", lambda: DB.informes_previos("org-1"))
if prev is not None:
    if len(prev) != 1:
        fallos.append(("informes_previos", f"deberia filtrar informe nulo, devolvio {len(prev)}"))
    else:
        print("       filtra corridas sin informe: OK")
probar("registrar_evento", lambda: DB.registrar_evento("org-1", "informe_generado", {"rol": "gerente"}))
probar("eventos", lambda: DB.eventos("org-1"))
n = probar("corridas_desde", lambda: DB.corridas_desde("org-1", "2026-08-01T00:00:00+00:00"))
if n != 7:
    fallos.append(("corridas_desde", f"content-range mal parseado: esperaba 7, dio {n}"))
else:
    print("       parsea content-range '0-0/7' -> 7: OK")

print("\n--- registrar_evento no debe romper el flujo si Supabase cae ---")
srv.shutdown()
try:
    DB.registrar_evento("org-1", "informe_generado", {})
    print("  OK   registrar_evento con backend caido: no lanza")
except Exception as e:                                            # noqa: BLE001
    fallos.append(("registrar_evento sin backend", f"{type(e).__name__}: {e}"))
    print(f"  FALLA registrar_evento con backend caido -> {e}")

print("\n--- auth: validación de JWT ---")
import jwt as pyjwt                                               # noqa: E402
from auth import verificar_jwt, usuario_actual                    # noqa: E402
from fastapi import HTTPException                                 # noqa: E402
import time                                                       # noqa: E402

SEC = os.environ["SUPABASE_JWT_SECRET"]
bueno = pyjwt.encode({"sub": "u-1", "email": "a@b.com", "aud": "authenticated",
                      "exp": int(time.time()) + 600}, SEC, algorithm="HS256")
probar("token valido", lambda: verificar_jwt(bueno))

for nombre, tok in [
    ("token con firma mala", pyjwt.encode(
        {"sub": "u-1", "aud": "authenticated", "exp": int(time.time()) + 600},
        "OTRO-SECRETO", algorithm="HS256")),
    # Vencido MUCHO mas alla del leeway=60 (que existe a proposito, para
    # tolerar desfase de reloj entre servidores).
    ("token expirado hace 1h", pyjwt.encode(
        {"sub": "u-1", "aud": "authenticated", "exp": int(time.time()) - 3600},
        SEC, algorithm="HS256")),
    ("token sin sub", pyjwt.encode(
        {"aud": "authenticated", "exp": int(time.time()) + 600}, SEC, algorithm="HS256")),
    ("audiencia incorrecta", pyjwt.encode(
        {"sub": "u-1", "aud": "otra", "exp": int(time.time()) + 600}, SEC, algorithm="HS256")),
]:
    try:
        verificar_jwt(tok)
        fallos.append((nombre, "ACEPTO un token que debia rechazar"))
        print(f"  FALLA {nombre}: fue ACEPTADO (agujero de seguridad)")
    except HTTPException as e:
        print(f"  OK   {nombre} rechazado ({e.status_code})")

# El leeway de 60s es intencional: un token recién vencido SÍ debe pasar
# (desfase de reloj), pero no uno vencido hace rato (comprobado arriba).
tok_recien = pyjwt.encode({"sub": "u-1", "aud": "authenticated",
                           "exp": int(time.time()) - 10}, SEC, algorithm="HS256")
try:
    verificar_jwt(tok_recien)
    print("  OK   token vencido hace 10s aceptado (leeway=60 intencional)")
except HTTPException:
    print("  NOTA token vencido hace 10s rechazado (leeway mas estricto de lo esperado)")

# alg=none: intento clásico de bypass
try:
    tok_none = pyjwt.encode({"sub": "u-1", "aud": "authenticated"}, None, algorithm="none")
    verificar_jwt(tok_none)
    fallos.append(("alg=none", "ACEPTADO — bypass de firma"))
    print("  FALLA alg=none fue ACEPTADO (bypass de firma)")
except Exception as e:                                            # noqa: BLE001
    print(f"  OK   alg=none rechazado ({type(e).__name__})")

# En SaaS, sin cabecera Authorization debe exigir login
try:
    usuario_actual(None)
    fallos.append(("sin Authorization", "dejo pasar sin token"))
    print("  FALLA sin cabecera Authorization: dejo pasar")
except HTTPException as e:
    print(f"  OK   sin cabecera Authorization rechazado ({e.status_code})")

print("\n" + "=" * 60)
if fallos:
    print(f"FALLOS: {len(fallos)}")
    for n, d in fallos:
        print(f"  - {n}: {d}")
    sys.exit(1)
print("TODO OK — el camino SaaS se ejecuta correctamente")

print("\n--- aislamiento entre organizaciones ---")
# Toda consulta/escritura que toque datos de negocio debe llevar org_id.
SIN_ORG_OK = {"/rest/v1/miembros"}   # resuelve la org a partir del user_id
malas = []
for metodo, ruta, datos, _pref in RECIBIDO:
    if ruta.startswith("/storage/") or ruta in SIN_ORG_OK:
        continue
    # GET/PATCH/DELETE -> querystring parseada; POST -> cuerpo JSON.
    tiene = isinstance(datos, dict) and "org_id" in datos
    if not tiene:
        malas.append((metodo, ruta, str(datos)[:70]))

if malas:
    print(f"  SIN filtro org_id: {len(malas)}")
    for m in malas:
        print(f"    - {m}")
else:
    print(f"  OK  las {len(RECIBIDO)} operaciones sobre datos de negocio filtran por org_id")
