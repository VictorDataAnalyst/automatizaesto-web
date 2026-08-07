# =====================================================================
# Erlang C (Fase 4 · vertical BPO/colas).
# Agentes necesarios para atender una tasa de llegadas en un intervalo,
# cumpliendo un nivel de servicio (% atendido dentro de T segundos).
# Determinista y auditable. Inerte hasta que un cliente de servicio suba
# AHT + nivel de servicio; con esos datos, exacto.
# =====================================================================
import math


def agentes(llegadas: float, aht_seg: float, intervalo_seg: float = 1800,
            nivel_servicio: float = 0.8, tiempo_objetivo_seg: float = 20,
            ocupacion_max: float = 0.85, shrinkage: float = 0.0) -> dict:
    """`llegadas` en `intervalo_seg`, atención media `aht_seg`. Devuelve agentes
    requeridos (con shrinkage) + métricas de la cola en ese punto."""
    if llegadas <= 0 or aht_seg <= 0:
        return {"agentes": 0, "agentes_base": 0, "sl": 1.0, "ocupacion": 0.0,
                "trafico_erlangs": 0.0, "prob_espera": 0.0}
    A = llegadas * aht_seg / intervalo_seg           # tráfico en Erlangs
    N = max(1, math.floor(A) + 1)                     # N > A siempre

    def prob_espera(N, A):
        # Iterativo (sin factoriales que desborden): term_k = A^k / k!
        term, s = 1.0, 1.0                            # k = 0
        for k in range(1, N):
            term *= A / k
            s += term
        term *= A / N                                 # term_N = A^N/N!
        C = term * (N / (N - A))                      # Erlang C numerador
        return C / (s + C)

    sl = pw = 0.0
    while N <= 100000:
        pw = prob_espera(N, A)
        sl = 1 - pw * math.exp(-(N - A) * (tiempo_objetivo_seg / aht_seg))
        if sl >= nivel_servicio and A / N <= ocupacion_max:
            break
        N += 1
    req = math.ceil(N / (1 - shrinkage)) if 0 <= shrinkage < 1 else N
    return {"agentes": req, "agentes_base": N, "sl": round(sl, 3),
            "ocupacion": round(A / N, 3), "trafico_erlangs": round(A, 2),
            "prob_espera": round(pw, 3)}


if __name__ == "__main__":  # ponytail: check contra caso conocido
    # 100 llegadas / 30 min, AHT 180s -> 10 Erlangs; 80% en 20s -> ~13-15 agentes
    r = agentes(100, 180, intervalo_seg=1800, nivel_servicio=0.8, tiempo_objetivo_seg=20)
    assert r["trafico_erlangs"] == 10.0, r
    assert 13 <= r["agentes"] <= 15, r
    assert r["sl"] >= 0.8 and r["ocupacion"] <= 0.85
    # shrinkage 30% infla la plantilla
    r2 = agentes(100, 180, shrinkage=0.30)
    assert r2["agentes"] > r["agentes"], (r["agentes"], r2["agentes"])
    # sin llegadas -> 0 agentes
    assert agentes(0, 180)["agentes"] == 0
    print("erlang OK:", r["agentes"], "agentes | SL", r["sl"], "| ocup", r["ocupacion"])
