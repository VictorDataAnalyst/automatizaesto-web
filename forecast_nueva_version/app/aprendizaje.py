# =====================================================================
# APRENDIZAJE — memoria determinista por organización.
# No es un LLM: es un "perfil del negocio" que se acumula corrida a
# corrida y se reinyecta en los próximos informes para que la app se
# adapte (defaults sugeridos + bloque "lo que sé de tu negocio").
# Todo es JSON-serializable: el perfil vive en la tabla perfil_org.
# =====================================================================
from collections import Counter


# ---------------------------------------------------------------------
# Estructura del perfil
# ---------------------------------------------------------------------
def perfil_vacio() -> dict:
    return {
        "identidad": {"nombre": None, "negocio": None},
        "n_corridas": 0,
        # contadores de frecuencia -> de aquí salen los defaults sugeridos
        "rol_freq": {}, "pais_freq": {}, "unidad_freq": {}, "rubro_freq": {},
        "horizonte_ultimo": None,
        "series": {},                       # {nombre_serie: veces vista}
        "calidad": {"wape_prom": None, "n": 0, "sesgo_dir": None},
        "hallazgos": {},                    # {id_insight: {"n": k, "titulo": str}}
        "ultima_corrida": None,             # snapshot para comparar
        "actualizado_en": None,
    }


def _inc(d: dict, clave) -> None:
    if clave is None:
        return
    d[str(clave)] = int(d.get(str(clave), 0)) + 1


def _top(freq: dict):
    """Valor más frecuente de un contador, o None si vacío."""
    if not freq:
        return None
    return max(freq.items(), key=lambda kv: kv[1])[0]


# ---------------------------------------------------------------------
# Fundir una corrida nueva en el perfil (se llama DESPUÉS de informar)
# ---------------------------------------------------------------------
def fundir_corrida(perfil: dict, cfg: dict, inf: dict,
                   rubro: str | None, fecha_iso: str) -> dict:
    p = {**perfil_vacio(), **(perfil or {})}
    p["n_corridas"] = int(p.get("n_corridas", 0)) + 1

    _inc(p["rol_freq"], cfg.get("rol"))
    _inc(p["pais_freq"], cfg.get("pais"))
    _inc(p["unidad_freq"], cfg.get("unidad"))
    _inc(p["rubro_freq"], rubro)
    p["horizonte_ultimo"] = cfg.get("horizonte") or p.get("horizonte_ultimo")

    # Series vistas (las claves de ganadores son los nombres de serie)
    for serie in (inf.get("anexo", {}).get("ganadores") or {}):
        _inc(p["series"], serie)

    # Calidad: WAPE promedio incremental + dirección de sesgo
    kpis = inf.get("kpis", {})
    wape = kpis.get("wape_pct")
    cal = p["calidad"]
    if isinstance(wape, (int, float)):
        n = int(cal.get("n", 0))
        prev = cal.get("wape_prom")
        cal["wape_prom"] = round((wape if prev is None
                                  else (prev * n + wape) / (n + 1)), 1)
        cal["n"] = n + 1
    sesgo = _sesgo_medio(inf)
    if sesgo is not None:
        cal["sesgo_dir"] = ("sobreestima" if sesgo > 2 else
                            "subestima" if sesgo < -2 else "equilibrado")

    # Hallazgos recurrentes (qué tipos de insight aparecen seguido)
    for ins in inf.get("insights", []):
        clave = ins.get("id") or ins.get("titulo")
        if not clave:
            continue
        h = p["hallazgos"].setdefault(str(clave),
                                      {"n": 0, "titulo": ins.get("titulo", "")})
        h["n"] += 1

    p["ultima_corrida"] = {
        "fecha": fecha_iso,
        "total_fmt": kpis.get("total_fmt"),
        "total": kpis.get("total"),
        "variacion_pct": kpis.get("variacion_pct"),
        "wape_pct": kpis.get("wape_pct"),
        "rol": cfg.get("rol"), "pais": cfg.get("pais"),
    }
    p["actualizado_en"] = fecha_iso
    return p


def _sesgo_medio(inf: dict):
    """Sesgo % promedio de los modelos ganadores (anexo)."""
    anexo = inf.get("anexo", {})
    ranking = anexo.get("ranking") or []
    ganadores = anexo.get("ganadores") or {}
    ganan = {(s, m) for s, ms in ganadores.items() for m in ms}
    vals = [r.get("sesgo_pct") for r in ranking
            if (r.get("serie"), r.get("modelo")) in ganan
            and isinstance(r.get("sesgo_pct"), (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else None


# ---------------------------------------------------------------------
# Lo que la app YA sabe -> defaults para precargar el próximo análisis
# ---------------------------------------------------------------------
def defaults_sugeridos(perfil: dict) -> dict:
    p = perfil or {}
    return {
        "rol": _top(p.get("rol_freq", {})),
        "pais": _top(p.get("pais_freq", {})),
        "unidad": _top(p.get("unidad_freq", {})),
        "horizonte": p.get("horizonte_ultimo"),
    }


# ---------------------------------------------------------------------
# Bloque "memoria" — se calcula ANTES de fundir, para comparar con la
# historia previa. Va dentro del informe y se pinta en el frontend.
# ---------------------------------------------------------------------
def bloque_memoria(perfil: dict, inf: dict) -> dict:
    p = perfil or perfil_vacio()
    previas = int(p.get("n_corridas", 0))
    n_corrida = previas + 1
    nombre = (p.get("identidad") or {}).get("nombre")
    kpis = inf.get("kpis", {})

    lineas = []
    if previas == 0:
        lineas.append("Primera proyección guardada para tu negocio. "
                      "A partir de ahora la app recuerda tus análisis y se adapta.")
    else:
        cal = p.get("calidad", {})
        if isinstance(cal.get("wape_prom"), (int, float)):
            lineas.append(f"Tu error típico ronda {cal['wape_prom']:.0f}% (WAPE) "
                          f"en {cal.get('n', 0)} corrida(s) previas.")
        if cal.get("sesgo_dir") and cal["sesgo_dir"] != "equilibrado":
            lineas.append(f"Históricamente tu modelo {cal['sesgo_dir']} la demanda; "
                          "tenlo presente al comprometer cifras.")
        rol_pref = _top(p.get("rol_freq", {}))
        pais_pref = _top(p.get("pais_freq", {}))
        if rol_pref:
            donde = f", en {pais_pref}" if pais_pref else ""
            lineas.append(f"Sueles leer el informe como «{rol_pref}»{donde}.")
        ult = p.get("ultima_corrida") or {}
        if ult.get("total") is not None and kpis.get("total") is not None:
            delta = _delta_pct(ult["total"], kpis["total"])
            if delta is not None:
                signo = "▲" if delta >= 0 else "▼"
                lineas.append(
                    f"Tu última proyección sumaba {ult.get('total_fmt')}; "
                    f"esta suma {kpis.get('total_fmt')} ({signo} {abs(delta):.1f}%).")
        recurrentes = sorted(p.get("hallazgos", {}).values(),
                             key=lambda h: h.get("n", 0), reverse=True)
        recurrentes = [h["titulo"] for h in recurrentes if h.get("n", 0) >= 2]
        if recurrentes:
            lineas.append("Patrón que se repite en tus datos: "
                          + ", ".join(recurrentes[:2]).lower() + ".")

    return {
        "es_primera": previas == 0,
        "n_corrida": n_corrida,
        "saludo": (f"Hola de nuevo, {nombre}." if nombre and previas else
                   (f"Bienvenido, {nombre}." if nombre else None)),
        "lineas": lineas,
        "aprendido": resumen_perfil(p),
    }


def _delta_pct(viejo, nuevo):
    try:
        viejo = float(viejo)
        if abs(viejo) < 1e-9:
            return None
        return 100 * (float(nuevo) - viejo) / abs(viejo)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------
# Resumen del perfil para el panel "lo que sé de tu negocio"
# ---------------------------------------------------------------------
def resumen_perfil(perfil: dict) -> dict:
    p = perfil or perfil_vacio()
    series_top = [s for s, _ in Counter(p.get("series", {})).most_common(5)]
    return {
        "identidad": p.get("identidad") or {"nombre": None, "negocio": None},
        "n_corridas": int(p.get("n_corridas", 0)),
        "rubro": _top(p.get("rubro_freq", {})),
        "rol_preferido": _top(p.get("rol_freq", {})),
        "pais_preferido": _top(p.get("pais_freq", {})),
        "wape_tipico": (p.get("calidad") or {}).get("wape_prom"),
        "sesgo_dir": (p.get("calidad") or {}).get("sesgo_dir"),
        "series_top": series_top,
        "ultima_corrida": p.get("ultima_corrida"),
        "actualizado_en": p.get("actualizado_en"),
    }
