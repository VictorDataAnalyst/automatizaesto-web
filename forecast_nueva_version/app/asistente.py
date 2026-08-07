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

    # --- Decisión 1: compromiso de volumen (siempre) ---
    decisiones.append({
        "tono": "ok", "prioridad": "alta",
        "titulo": f"Puedes comprometer {piso} {u}",
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
        decisiones.append({
            "tono": "alerta", "prioridad": "alta",
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
            "tono": "ok", "prioridad": "media",
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
        decisiones.append({
            "tono": "accion", "prioridad": "media",
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
        decisiones.append({
            "tono": "info", "prioridad": "media",
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
            "tono": "info" if gana == "manual" else "ok", "prioridad": "alta",
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
        "tono": "ok" if conf == "alta" else "info", "prioridad": "baja",
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

    return {"decisiones": decisiones, "evidencia": evidencia, "confianza": confianza,
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
