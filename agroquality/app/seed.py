# =====================================================================
# AgroQuality — datos semilla (modo demo). Reflejan las capturas reales de
# Marand Company Asia (paltas Hass a China, 13/06/2026). Mismos nombres de
# columna que el esquema Supabase (aq_inspeccion / aq_pallet).
# =====================================================================


def score_de(pct_total: float) -> str:
    if pct_total < 12:
        return "good"
    if pct_total <= 25:
        return "fair"
    return "poor"


def _pallet(codigo, calibre, productor, temp, pcal, pcond, principal, muestra):
    ptot = round(pcal + pcond, 2)
    return {
        "codigo": codigo, "calibre": calibre, "productor": productor,
        "temp_prom": temp, "peso_neto_prom": 10, "brix_prom": None,
        "tamano_muestra": muestra, "cajas_muestra": 120,
        "pct_calidad": pcal, "pct_condicion": pcond, "pct_total": ptot,
        "pallet_score": score_de(ptot), "sample_score": score_de(ptot),
        "defecto_principal": principal, "clase": "1", "fotos": None,
    }


def inspecciones_semilla() -> list:
    insp1_pallets = [
        _pallet("R-MAR-10-EX08267", 28, "004-03006-03", 6.0, 1.5, 8.5, "Sum of Condition Defects", 69),
        _pallet("R-MAR-10-EX08142", 30, "016-42980-01", 6.5, 3.2, 11.0, "Black Spots, Sum of Condition Defects", 76),
        _pallet("R-MAR-10-EX08281", 22, "016-4726-01", 6.2, 6.1, 24.4, "Internal Breakdown, Lenticelosis", 54),
        _pallet("S-MAR-10-EX08284", 18, "010-62372-01", 6.1, 4.0, 18.0, "Sum of Total Defects", 44),
        _pallet("S-MAR-10-EX08178", 26, "009-33744-02", 6.3, 5.0, 19.0, "Lenticelosis, Sum of Condition Defects", 66),
        _pallet("C-MAR-10-EX08274", 22, "016-40726-01", 6.0, 6.0, 22.0, "Sum of Total Defects", 54),
        _pallet("C-MAR-10-EX08296", 20, "016-42980-01", 5.9, 2.0, 6.0, "Sum of Quality Defects", 48),
        _pallet("C-MAR-10-EX08283", 24, "016-40726-01", 6.2, 6.12, 24.49, "Sum of Total Defects", 51),
    ]
    insp1 = {
        "id": "INS-2606-0001", "codigo": "INS-2606-0001",
        "lote": "FBIU5628390", "container": "FBIU5628390", "num_factura": None,
        "compania": "Marand Company Asia", "exportador": "Marand Company",
        "consignatario": "Supafresh", "producto": "Avocados", "variedad": "Hass",
        "embalaje": "Plastic Box 10Kg", "tipo_producto": "CONV",
        "locacion": "China, Shanghai", "pais_origen": "Peru", "barco": "ORCA I 025W",
        "tipo_carrier": "Ocean", "frigorifico": "Supafresh DC", "fumigacion": "None",
        "tipo_inspeccion": "Normal Inspection", "inspector": "Titus Song",
        "cajas": 2400, "total_pallets": 8, "hora_frigorifico": "4:00 PM",
        "fecha_embalaje": "2026-04-30", "fecha_arribo": "2026-06-01",
        "fecha_frigorifico": "2026-06-13", "estado": "cerrada",
        "pallets": insp1_pallets,
    }

    insp2_pallets = [
        _pallet("R-MAR-08-EX07710", 24, "004-03006-03", 5.8, 1.0, 5.0, "Sum of Condition Defects", 60),
        _pallet("R-MAR-08-EX07711", 22, "009-33744-02", 5.9, 2.0, 7.5, "Lenticelosis", 58),
        _pallet("S-MAR-08-EX07712", 20, "010-62372-01", 6.0, 3.0, 9.5, "Black Spots", 62),
        _pallet("C-MAR-08-EX07713", 26, "016-4726-01", 6.1, 5.5, 21.0, "Internal Breakdown", 50),
    ]
    insp2 = {
        "id": "INS-2605-0007", "codigo": "INS-2605-0007",
        "lote": "MNBU7781002", "container": "MNBU7781002", "num_factura": None,
        "compania": "Marand Company Asia", "exportador": "Marand Company",
        "consignatario": "Wonokoyo", "producto": "Avocados", "variedad": "Hass",
        "embalaje": "Plastic Box 10Kg", "tipo_producto": "CONV",
        "locacion": "China, Ningbo", "pais_origen": "Peru", "barco": "SANTA CRUZ 042W",
        "tipo_carrier": "Ocean", "frigorifico": "Supafresh DC", "fumigacion": "None",
        "tipo_inspeccion": "Normal Inspection", "inspector": "Lia Chen",
        "cajas": 1200, "total_pallets": 4, "hora_frigorifico": "9:30 AM",
        "fecha_embalaje": "2026-04-18", "fecha_arribo": "2026-05-20",
        "fecha_frigorifico": "2026-05-22", "estado": "cerrada",
        "pallets": insp2_pallets,
    }
    return [insp1, insp2]
