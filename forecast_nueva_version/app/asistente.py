# =====================================================================
# Asistente ejecutivo de planificación (determinista).
# Convierte el informe YA calculado en:
#   - decisiones (qué hacer) con evidencia trazable ("¿por qué?")
#   - evidencia (las cifras exactas que sostienen todo)
#   - confianza (entendible, sin jerga)
#   - riesgos detectados
#   - plan de acción cronológico
# Todo nace de hechos calculados. NADA inventado. NADA de LLM.
# =====================================================================
from collections import Counter


def _fmt(x) -> str:
    """Miles con espacio fino — mismo formato que el resto del informe.
    Sin esto convivían '2 592' y '5889' en la misma grilla."""
    try:
        return f"{round(float(x)):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(x)


def _rankear(decisiones: list) -> list:
    """Ordena por impacto real y deriva la prioridad del score, no al revés.
    Antes la prioridad venía escrita a mano en cada decisión y el orden era
    el del código: primero lo que programé, no lo que más urge.
    Escala 0-100. Como máximo 2 decisiones dominantes: si todo es urgente,
    nada lo es."""
    for d in decisiones:
        d.setdefault("score", 30)
    decisiones.sort(key=lambda d: -d["score"])
    altas = 0
    for d in decisiones:
        if d["score"] >= 55 and altas < 2:
            d["prioridad"] = "alta"; altas += 1
        elif d["score"] >= 30:
            d["prioridad"] = "media"
        else:
            d["prioridad"] = "baja"
    return decisiones


def _veredicto(k, var, conf, wape, u, h, fplu, cd, decisiones) -> dict:
    """Una o dos frases que responden '¿qué está pasando?'. Se compone de los
    datos reales: tendencia + riesgo principal + confianza. Nunca es fijo."""
    if var > 5:
        tend, tono_t = f"crece {var:.0f}%", "ok"
    elif var < -5:
        tend, tono_t = f"cae {abs(var):.0f}%", "alerta"
    else:
        tend, tono_t = "se mantiene estable", "info"

    frase = (f"Para los próximos {h} {fplu} tu operación {tend} "
             f"frente al periodo anterior, con {k.get('total_fmt','')} {u} proyectados.")

    # El riesgo principal es la decisión de mayor score que sea una alerta,
    # EXCLUYENDO la de volumen: la tendencia ya se dijo en la primera frase y
    # repetirla ("cae 15%... hay algo que atender: cae 15%") suena a error.
    riesgo = next((d for d in decisiones
                   if d["tono"] == "alerta" and d.get("id") != "volumen"), None)
    if riesgo:
        pero = riesgo.get("titular_corto") or riesgo["titulo"]
        frase += f" Pero hay algo que atender: {pero[0].lower()}{pero[1:]}."
        tono = "alerta"
    elif var <= -12:
        # La caída ya se dijo arriba; decir "no hay riesgos" la contradiría.
        frase += " Ese es el punto a atender: ajusta el plan antes de comprometerte."
        tono = "alerta"
    elif var >= 12:
        frase += " Asegúrate de tener capacidad para sostener ese crecimiento."
        tono = "info"
    else:
        frase += " No detecto riesgos que requieran acción inmediata."
        tono = tono_t

    if conf == "limitada":
        frase += (f" Ojo: la proyección tiene un margen de error amplio ({wape:.0f}%), "
                  f"tómala como referencia.")
    return {"frase": frase, "tono": tono, "tendencia": tend,
            "confianza": conf, "variacion_pct": round(var, 1)}


def _insight(inf, id_):
    for x in inf.get("insights", []):
        if x.get("id") == id_:
            return x
    return None


def _modelo_ganador(inf):
    gan = (inf.get("anexo") or {}).get("ganadores") or {}
    modelos = [m for ms in gan.values() for m in ms]
    return Counter(modelos).most_common(1)[0][0] if modelos else "—"


def construir(inf: dict, rubro: str = "", perfil: dict | None = None,
              prec: dict | None = None, comp: dict | None = None) -> dict:
    k = inf.get("kpis", {})
    u = k.get("unidad", "unidades")
    h, fplu = k.get("horizonte", ""), k.get("frecuencia_plural", "periodos")
    var = float(k.get("variacion_pct", 0) or 0)
    wape = float(k.get("wape_pct", 0) or 0)
    conf = k.get("confianza", "media")
    total, piso, techo = k.get("total_fmt", ""), k.get("piso_fmt", ""), k.get("techo_fmt", "")
    cap = _insight(inf, "capacidad")
    cd = (cap or {}).get("datos") or {}

    decisiones, riesgos, plan = [], [], []

    # --- Decisión 1: volumen del periodo (siempre) ---
    # Un vaivén fuerte de demanda ES el asunto principal, aunque no haya otro
    # riesgo: a partir de ±20% escala a dominante y el titular lo dice.
    _cae = var <= -12
    _sube = var >= 12
    decisiones.append({
        "id": "volumen",
        # El +8 hace que cualquier vaivén de ±12% o más cruce a dominante:
        # tanto una caída como un crecimiento fuerte obligan a replanificar.
        "score": 34 + min(26, abs(var) * 1.1) + (8 if (_cae or _sube) else 0),
        "tono": "alerta" if _cae else "ok",
        "titular_corto": (f"tu demanda cae {abs(var):.0f}% frente al periodo anterior" if _cae
                          else f"tu demanda sube {var:.0f}%" if _sube
                          else f"puedes comprometer {piso} {u}"),
        "importa": ((f"Una caída de {abs(var):.0f}% cambia el plan completo: si mantienes "
                     f"la estructura de costos del periodo anterior, el margen se come "
                     f"la diferencia.") if _cae else
                    (f"Crecer {var:.0f}% solo es buena noticia si la operación aguanta. "
                     f"Revisa que tengas capacidad para ese volumen.") if _sube else
                    (f"Este es el número con el que negocias: comprometer de más cuesta "
                     f"incumplimientos, y de menos deja capacidad ociosa que ya pagaste.")),
        "titulo": (f"Tu demanda cae {abs(var):.0f}%: compromete {piso} {u}" if _cae
                   else f"Tu demanda sube {var:.0f}%: compromete {piso} {u}" if _sube
                   else f"Puedes comprometer {piso} {u}"),
        "resumen": f"Con 80% de confianza el total del periodo cae entre {piso} y {techo}. "
                   f"Comprometer el piso y preparar el techo evita sobrecostos.",
        "accion": f"Fija metas y compromisos en {piso} {u}; ten capacidad para {techo}.",
        "porque": (f"Sumé lo que proyecto para los {h} {fplu} que vienen: {total} {u}. "
                   f"Como ningún pronóstico es exacto, calculo un rango: de cada 10 veces, "
                   f"8 caerán entre {piso} y {techo}. Por eso te digo que comprometas el "
                   f"número bajo ({piso}) — así cumples aunque venga flojo — y que tengas "
                   f"capacidad para el alto ({techo}), para no quedarte corto si viene fuerte."),
        "evidencia": [
            {"label": f"Total proyectado ({h} {fplu})", "valor": f"{total} {u}",
             "ayuda": "La suma de todos los periodos que estoy proyectando."},
            {"label": "Piso (escenario bajo)", "valor": piso,
             "ayuda": "Difícilmente vendas menos que esto. Es tu número seguro para comprometer."},
            {"label": "Techo (escenario alto)", "valor": techo,
             "ayuda": "Difícilmente superes esto. Para esta cifra debes tener capacidad lista."},
            {"label": "vs periodo anterior", "valor": f"{var:+.1f}%",
             "ayuda": "Cuánto sube o baja frente al periodo comparable anterior."},
        ]})

    # --- Decisión 2: capacidad (si el cliente subió stock) ---
    if cap and cd.get("n_excede", 0) > 0:
        fp = cd.get("fecha_pico")
        # El déficit de capacidad es el fallo más caro: si no se cubre, el
        # pedido no sale. Score alto, y escala con el tamaño del hueco.
        _pct_def = 100 * cd["deficit_total"] / max(cd.get("demanda_total", 1), 1)
        decisiones.append({
            "score": 62 + min(35, _pct_def * 3),
            "tono": "alerta",
            "titular_corto": f"te falta capacidad en {cd['n_excede']} de {cd['n_total']} periodos",
            "importa": (f"Si no amplías capacidad, esos {_fmt(cd['deficit_total'])} {u} "
                        f"no se producen a tiempo: se traducen en entregas tarde o "
                        f"pedidos que hay que rechazar."),
            "titulo": f"Tendrás déficit de capacidad en {cd['n_excede']} de {cd['n_total']} periodos",
            "resumen": cap.get("resumen", ""),
            "accion": f"Adelanta producción, suma turno o reprograma entregas antes del {fp}.",
            "porque": (f"Comparé, periodo por periodo, cuánto vas a necesitar contra cuánto "
                       f"puedes producir (lo saqué de tu columna «{cd.get('col','stock')}», "
                       f"tomando tu ritmo habitual). En {cd['n_excede']} de {cd['n_total']} "
                       f"periodos la demanda pasa por encima de tu capacidad: en total te "
                       f"faltarían {_fmt(cd['deficit_total'])} {u}. El momento más apretado es "
                       f"el {fp}. Si no haces nada, ese pedido no sale a tiempo."),
            "evidencia": [
                {"label": "Vas a necesitar", "valor": f"{_fmt(cd['demanda_total'])} {u}",
                 "ayuda": "Demanda total que proyecto para el periodo."},
                {"label": "Puedes producir", "valor": f"{_fmt(cd['capacidad_total'])} {u}",
                 "ayuda": f"Tu capacidad, calculada desde la columna «{cd.get('col','stock')}»."},
                {"label": "Te faltaría", "valor": f"{_fmt(cd['deficit_total'])} {u}",
                 "ayuda": "La diferencia: lo que no alcanzarías a cubrir."},
                {"label": "Fecha más crítica", "valor": fp or "—",
                 "ayuda": "El periodo donde la brecha es mayor. Actúa antes de esta fecha."},
            ]})
        riesgos.append({
            "tono": "alerta", "titulo": "Capacidad insuficiente",
            "impacto": f"{_fmt(cd['deficit_total'])} {u}", "probabilidad": "Alta",
            "accion": "Abrir turno adicional o adelantar producción"})
        if fp:
            plan.append({"cuando": fp, "orden": fp,
                         "accion": f"Cubrir el déficit de capacidad ({_fmt(cd['deficit_total'])} {u}): abrir turno o adelantar producción."})
    elif cap:
        decisiones.append({
            "score": 22,   # buena noticia: informativa, no compite por atención
            "tono": "ok",
            "titular_corto": "tu capacidad cubre la demanda",
            "importa": "Tienes margen: puedes tomar más pedidos o liberar recursos "
                       "que hoy están reservados por si acaso.",
            "titulo": "Tu capacidad cubre la demanda proyectada",
            "resumen": cap.get("resumen", ""),
            "accion": "Puedes subir la meta o liberar recursos.",
            "evidencia": [
                {"label": "Demanda proyectada", "valor": f"{_fmt(cd.get('demanda_total',0))} {u}"},
                {"label": "Capacidad disponible", "valor": f"{_fmt(cd.get('capacidad_total',0))} {u}"},
            ]})

    # --- Decisión 3: estacionalidad (periodo más exigente) ---
    ie = _insight(inf, "estacionalidad")
    if ie:
        # Cuanto más marcada la estacionalidad, más planificación exige.
        _amp = 0.0
        import re as _re
        _m = _re.search(r"(\d+)%\s*de amplitud", ie.get("resumen", ""))
        if _m:
            _amp = float(_m.group(1))
        decisiones.append({
            "score": 26 + min(22, _amp * 0.25),
            "tono": "accion",
            "titular_corto": "hay un periodo mucho más exigente que el resto",
            "importa": ("Los picos no se improvisan: contratar y capacitar toma "
                        "semanas. Si reaccionas cuando llega, ya es tarde."),
            "titulo": "Hay un periodo más exigente que el resto",
            "resumen": ie["resumen"],
            "accion": "Refuerza capacidad antes del pico; usa el valle para mantenimiento.",
            "evidencia": [{"label": "Patrón estacional", "valor": ie.get("cifra") or "—"},
                          {"label": "Detalle", "valor": ie["resumen"]}]})
        plan.append({"cuando": "Antes del pico estacional", "orden": "0",
                     "accion": f"Reforzar capacidad para el pico. {ie['resumen']}"})

    # --- Decisión 4: concentración (dependencia) ---
    icn = _insight(inf, "concentracion")
    if icn:
        # Riesgo estructural: escala con cuánto pesa la serie líder.
        import re as _re2
        _m2 = _re2.search(r"pesa (\d+)%", icn.get("resumen", ""))
        _lider = float(_m2.group(1)) if _m2 else 50.0
        decisiones.append({
            "score": 20 + min(30, _lider * 0.45),
            "tono": "info",
            "titular_corto": "tu volumen depende de muy pocas series",
            "importa": (f"Si esa línea falla —un cliente que se va, una plaga, un "
                        f"contrato que no se renueva— te llevas el golpe completo, "
                        f"no una parte."),
            "titulo": "Tu volumen depende de pocas series",
            "resumen": f"{icn['resumen']} Es lo que no puede fallar.",
            "accion": "Asigna ahí tus mejores recursos y ten un plan B.",
            "evidencia": [{"label": "Concentración", "valor": icn.get("cifra") or "—"},
                          {"label": "Detalle", "valor": icn["resumen"]}]})
        riesgos.append({
            "tono": "info", "titulo": "Concentración del negocio",
            "impacto": icn.get("cifra") or "—", "probabilidad": "Media",
            "accion": "Diversificar o blindar la serie líder"})

    # --- Decisión: tu equipo vs el modelo (FVA) ---
    if comp:
        gana = comp["gana"]
        decisiones.append({
            # Que el equipo gane al modelo es una señal fuerte: significa que
            # hay información fuera de los datos. Que gane el modelo, informativa.
            "score": (58 if gana == "manual" else 24),
            "tono": "alerta" if gana == "manual" else "ok",
            "titular_corto": ("tu equipo está pronosticando mejor que el modelo"
                              if gana == "manual" else "el modelo mejora la proyección del equipo"),
            "importa": (("Tu gente maneja información que los datos no capturan. "
                         "Si no la incorporamos, el modelo seguirá por debajo de "
                         "ellos y no te aportará nada.")
                        if gana == "manual" else
                        (f"Cada punto de error de más se paga en inventario o en "
                         f"incumplimientos: son {comp['fva_vs_manual']} puntos que "
                         f"puedes ahorrarte.")),
            "titulo": comp["titulo"],
            "resumen": comp["mensaje"],
            "accion": comp["accion"],
            "porque": (f"Tomé la proyección que tu equipo cargó en la columna "
                       f"«{comp['col_manual']}» y la puse a competir contra la mía sobre "
                       f"periodos que YA pasaron, así los dos se miden contra la realidad. "
                       f"Tu equipo se desvió {comp['wape_manual']}% en promedio; yo "
                       f"{comp['wape_modelo']}%. Repetir la temporada anterior sin pensar "
                       f"(lo más simple posible) se desvía {comp['wape_naive']}%. "
                       + ("Como tu equipo gana, lo honesto es decírtelo: síguelos a ellos."
                          if gana == "manual" else
                          "Por eso te propongo partir de mi proyección.")),
            "evidencia": [
                {"label": "Se equivoca tu equipo", "valor": f"{comp['wape_manual']}%",
                 "ayuda": "Qué tanto se desvió el plan manual en periodos ya ocurridos."},
                {"label": "Me equivoco yo", "valor": f"{comp['wape_modelo']}%",
                 "ayuda": "Qué tanto se desvió el modelo en esos mismos periodos."},
                {"label": "Diferencia", "valor": f"{comp['fva_vs_manual']:+.1f} pts",
                 "ayuda": "Positivo = el modelo aporta. Negativo = tu equipo lo hace mejor."},
                {"label": "Si no pensaras nada", "valor": f"{comp['wape_naive']}%",
                 "ayuda": "Error de repetir la temporada pasada. Es el mínimo a superar."},
            ]})
        if gana == "manual":
            riesgos.append({
                "tono": "info", "titulo": "Tu equipo sabe algo que los datos no",
                "impacto": f"{abs(comp['fva_vs_manual'])} pts de error",
                "probabilidad": "Confirmada",
                "accion": "Agregar esa información como columna para que el modelo la aprenda"})

    # --- Decisión 5: confianza (siempre, entendible) ---
    decisiones.append({
        # Solo escala a primer plano cuando el margen de error es preocupante.
        "score": (12 if conf == "alta" else 28 if conf == "media" else 58),
        "tono": "alerta" if conf == "limitada" else "ok" if conf == "alta" else "info",
        "titular_corto": (f"la proyección tiene un margen de error amplio ({wape:.0f}%)"
                          if conf == "limitada" else f"la proyección es de confianza {conf}"),
        "importa": (("Con este margen, planificar al detalle es arriesgado: usa el "
                     "rango y deja holgura hasta tener más historia.")
                    if conf != "alta" else
                    "Puedes usar estos números para comprometerte con clientes."),
        "titulo": f"La proyección es de confianza {conf}",
        "resumen": k.get("veredicto", ""),
        "accion": ("Puedes comprometerte con ella." if conf == "alta"
                   else "Trátalo como referencia y deja holgura."),
        "porque": (f"No te pido que me creas: probé el modelo contra tu propia historia. "
                   f"Le tapé los últimos periodos, le pedí que los adivinara y comparé con "
                   f"lo que de verdad pasó. En promedio se desvió {wape:.0f}%. "
                   f"O sea: si proyecto 100, la realidad suele caer entre "
                   f"{100-wape:.0f} y {100+wape:.0f}."),
        "evidencia": [
            {"label": "Margen de error", "valor": f"{wape:.0f}%",
             "ayuda": "Cuánto se desvía en promedio al probarlo contra tu historia real."},
            {"label": "Series analizadas", "valor": k.get("n_series", "—"),
             "ayuda": "Cuántos productos/clientes/líneas se modelaron por separado."},
            {"label": "Método elegido", "valor": _modelo_ganador(inf),
             "ayuda": "De varios métodos probados, el que mejor acertó con tus datos."}]})

    # --- Riesgo extra: confianza limitada ---
    if conf == "limitada":
        riesgos.append({
            "tono": "alerta", "titulo": "Proyección con margen amplio",
            "impacto": f"{wape:.0f}% de error", "probabilidad": "Media",
            "accion": "Usar como referencia direccional, no como compromiso"})

    # --- Feriados en el plan de acción ---
    if_ = _insight(inf, "feriados")
    if if_ and not str(if_.get("cifra", "")).strip().startswith("0"):
        plan.append({"cuando": "Feriados del periodo", "orden": "1",
                     "accion": f"Ajustar entregas y turnos. {if_['resumen']}"})

    # --- Evidencia (S2): las cifras que sostienen todo ---
    # `sufijo` va aparte del número para que la unidad se pinte pequeña y la
    # cifra no se parta en dos líneas (descuadraba la grilla).
    evidencia = [
        {"label": "Vas a vender", "valor": total, "sufijo": u,
         "ayuda": f"Total esperado en los próximos {h} {fplu}."},
        {"label": "Rango probable", "valor": f"{piso} – {techo}", "sufijo": u,
         "ayuda": "8 de cada 10 veces el resultado cae entre estas dos cifras."},
        {"label": "Margen de error", "valor": f"{wape:.0f}", "sufijo": "%",
         "ayuda": "Cuánto se desvía al probarlo contra tu historia real."},
        {"label": "Series analizadas", "valor": k.get("n_series", "—"),
         "ayuda": "Productos, clientes o líneas modelados por separado."},
        {"label": "Método elegido", "valor": _modelo_ganador(inf),
         "ayuda": "El que mejor acertó con tus datos, entre varios probados."},
    ]
    if cap:
        evidencia.insert(1, {"label": "Puedes producir", "valor": f"{_fmt(cd.get('capacidad_total',0))}",
                             "sufijo": u, "ayuda": "Tu capacidad disponible en el periodo."})
        if cd.get("deficit_total", 0) > 0:
            evidencia.insert(2, {"label": "Te faltaría", "valor": f"{_fmt(cd['deficit_total'])}",
                                 "sufijo": u, "ayuda": "Lo que no alcanzarías a cubrir."})
    if prec:
        evidencia.append({"label": "Acierto ya verificado", "valor": f"{prec['wape_ultima']:.1f}",
                          "sufijo": "% de error",
                          "ayuda": "Qué tan cerca estuvo mi último pronóstico de la realidad."})

    # --- Confianza (S3): estrellas + motivos, sin jerga ---
    estrellas = 5 if (conf == "alta" and wape < 8) else 4 if conf == "alta" else 3 if conf == "media" else 2
    motivos = []
    # La precisión ya verificada contra la realidad es el argumento más fuerte: va primero.
    if prec:
        motivos.append(f"Track record real: {prec['frase']}")
        if prec.get("tendencia") == "mejorando":
            motivos.append("Mis pronósticos vienen mejorando corrida a corrida")
        # Track record demostrado: sube la confianza; track record malo: la baja.
        if prec["wape_ultima"] <= 10:
            estrellas = min(5, estrellas + 1)
        elif prec["wape_ultima"] > 30:
            estrellas = max(1, estrellas - 1)
    motivos += [f"Error histórico {wape:.0f}%",
                f"{k.get('n_series','—')} series analizadas",
                "Validado contra tu propia historia (walk-forward)"]
    iv = _insight(inf, "volatilidad")
    if iv:
        motivos.append(iv["resumen"])
    confianza = {"estrellas": estrellas,
                 "nivel": {"alta": "Alta", "media": "Media", "limitada": "Limitada"}.get(conf, conf.title()),
                 "motivos": motivos,
                 "track_record": prec}

    # --- Plan de acción: ordenar (fechas ISO primero) ---
    plan.sort(key=lambda x: (x["orden"][0] not in "012", x["orden"]))
    plan_accion = [{"cuando": p["cuando"], "accion": p["accion"]} for p in plan]

    # --- Continuidad (memoria del negocio) ---
    continuidad = None
    if perfil and perfil.get("n_corridas", 0) >= 3 and perfil.get("wape_tipico") is not None:
        continuidad = (f"Van {perfil['n_corridas']} análisis tuyos; tu error típico ronda "
                       f"{perfil['wape_tipico']:.0f}%. Uso esa historia para calibrar la confianza.")

    # --- Prioridad por impacto real, no por orden de programación ---
    decisiones = _rankear(decisiones)
    veredicto = _veredicto(k, var, conf, wape, u, h, fplu, cd, decisiones)

    return {"veredicto": veredicto,
            "decisiones": decisiones, "evidencia": evidencia, "confianza": confianza,
            "riesgos": riesgos, "plan_accion": plan_accion, "continuidad": continuidad,
            "comparacion": comp}


if __name__ == "__main__":  # ponytail: check de la lógica no trivial
    inf = {"kpis": {"unidad": "contenedores", "horizonte": 8, "frecuencia_plural": "semanales",
                    "total_fmt": "1 716", "variacion_pct": -14.6, "confianza": "alta",
                    "wape_pct": 5.0, "piso_fmt": "1 657", "techo_fmt": "1 776", "n_series": 2,
                    "veredicto": "Confianza alta."},
           "anexo": {"ganadores": {"A": ["ETS"], "B": ["ETS", "AutoARIMA"]}},
           "insights": [
               {"id": "capacidad", "resumen": "Superas capacidad en 6 periodos.", "cifra": "6 en riesgo",
                "datos": {"demanda_total": 1716, "capacidad_total": 1676, "deficit_total": 40,
                          "n_excede": 6, "n_total": 16, "fecha_pico": "2026-05-31", "unidad": "contenedores"}},
               {"id": "estacionalidad", "resumen": "Pico en abril.", "cifra": "pico: abril"},
               {"id": "concentracion", "resumen": "Producto A pesa 66%.", "cifra": "1 de 2 series"}]}
    a = construir(inf, "Agroexportación", {"n_corridas": 7, "wape_tipico": 11.0})
    assert len(a["decisiones"]) >= 4
    assert any(d["tono"] == "alerta" and "déficit" in d["titulo"].lower() for d in a["decisiones"])

    # --- Jerarquía: el déficit de capacidad manda sobre todo lo demás ---
    assert "déficit" in a["decisiones"][0]["titulo"].lower(), \
        f"lo más urgente debe ir primero, no {a['decisiones'][0]['titulo']}"
    assert a["decisiones"][0]["prioridad"] == "alta"
    altas = [d for d in a["decisiones"] if d["prioridad"] == "alta"]
    assert len(altas) <= 2, f"si todo es urgente nada lo es: {len(altas)} altas"
    # El orden debe ser descendente por score
    scores = [d["score"] for d in a["decisiones"]]
    assert scores == sorted(scores, reverse=True), scores
    # Cada decisión explica su consecuencia de negocio
    assert all(d.get("importa") for d in a["decisiones"])

    # --- Veredicto: se compone de datos reales, no es texto fijo ---
    v = a["veredicto"]
    assert "cae 15%" in v["frase"], v["frase"]          # var = -14.6 -> "cae 15%"
    assert "atender" in v["frase"] and v["tono"] == "alerta"
    assert "contenedores" in v["frase"]
    # Sin riesgo de capacidad, la caída del 15% pasa a ser ELLA el asunto.
    # No debe decir "no detecto riesgos" justo después de anunciar la caída.
    sin_riesgo = {**inf, "insights": [x for x in inf["insights"] if x["id"] != "capacidad"]}
    v2 = construir(sin_riesgo)["veredicto"]
    assert "No detecto riesgos" not in v2["frase"], "se contradice con la caída"
    assert "punto a atender" in v2["frase"] and v2["tono"] == "alerta", v2["frase"]
    # Creciendo fuerte: no es alarma, pero sí aviso de capacidad.
    creciendo = {**sin_riesgo, "kpis": {**inf["kpis"], "variacion_pct": 18.0}}
    v3 = construir(creciendo)["veredicto"]
    assert "crece 18%" in v3["frase"] and "capacidad" in v3["frase"], v3["frase"]
    # Estable y sin riesgos: ahí sí corresponde decir que no hay nada urgente.
    calmo = {**sin_riesgo, "kpis": {**inf["kpis"], "variacion_pct": 2.0}}
    v4 = construir(calmo)["veredicto"]
    assert "No detecto riesgos" in v4["frase"] and "estable" in v4["frase"], v4["frase"]
    assert all(d.get("evidencia") for d in a["decisiones"])        # todas trazables
    assert a["confianza"]["estrellas"] == 5 and a["confianza"]["nivel"] == "Alta"
    assert any(r["titulo"] == "Capacidad insuficiente" for r in a["riesgos"])
    assert a["plan_accion"] and a["continuidad"]
    assert a["evidencia"][0]["label"] == "Vas a vender"
    # La unidad va en `sufijo`, no pegada al número (si no, la grilla se descuadra).
    assert a["evidencia"][0]["sufijo"] == "contenedores"
    assert " contenedores" not in str(a["evidencia"][0]["valor"])
    assert all(e.get("ayuda") for e in a["evidencia"])   # toda cifra se explica
    print("asistente OK:", len(a["decisiones"]), "decisiones,", len(a["riesgos"]), "riesgos,",
          len(a["plan_accion"]), "pasos de plan")
