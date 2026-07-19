# -*- coding: utf-8 -*-
"""Genera la propuesta economica de AgroQuality para Marand (PDF)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, ListFlowable, ListItem,
)

OUT = "Propuesta_Economica_AgroQuality_Marand.pdf"

# Paleta automatizaesto (verde)
VERDE = colors.HexColor("#15803D")
VERDE_OSC = colors.HexColor("#0F5C2E")
VERDE_CLARO = colors.HexColor("#E7F5EC")
GRIS = colors.HexColor("#4B5563")
GRIS_CLARO = colors.HexColor("#F3F4F6")
TINTA = colors.HexColor("#1F2937")

styles = getSampleStyleSheet()

def S(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)

st_title = S("t", fontName="Helvetica-Bold", fontSize=22, leading=26,
             textColor=colors.white)
st_sub = S("s", fontName="Helvetica", fontSize=10.5, leading=14,
           textColor=colors.HexColor("#D1FADF"))
st_h = S("h", fontName="Helvetica-Bold", fontSize=13, leading=16,
         textColor=VERDE_OSC, spaceBefore=14, spaceAfter=6)
st_body = S("b", fontName="Helvetica", fontSize=10, leading=15, textColor=TINTA)
st_small = S("sm", fontName="Helvetica", fontSize=8.5, leading=12, textColor=GRIS)
st_li = S("li", fontName="Helvetica", fontSize=10, leading=15, textColor=TINTA)
st_kpi = S("kpi", fontName="Helvetica-Bold", fontSize=10, leading=13,
           textColor=colors.white)
st_cellb = S("cb", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=TINTA)
st_cell = S("c", fontName="Helvetica", fontSize=9.5, leading=13, textColor=TINTA)
st_price = S("p", fontName="Helvetica-Bold", fontSize=15, leading=17, textColor=VERDE_OSC,
             alignment=TA_RIGHT)

story = []

# --- Encabezado de marca ---
head = Table([[
    Paragraph("AUTOMATIZA<font color='#A7F3D0'>ESTO</font>", S("logo",
              fontName="Helvetica-Bold", fontSize=15, textColor=colors.white)),
    Paragraph("Propuesta economica", S("hr", fontName="Helvetica", fontSize=9,
              textColor=colors.HexColor("#D1FADF"), alignment=TA_RIGHT)),
]], colWidths=[100*mm, 70*mm])
head.setStyle(TableStyle([
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 0),
    ("RIGHTPADDING", (0,0), (-1,-1), 0),
]))

banner = Table([
    [head],
    [Paragraph("AgroQuality", st_title)],
    [Paragraph("Plataforma de auditoria y control de calidad post-cosecha", st_sub)],
], colWidths=[170*mm])
banner.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), VERDE),
    ("LEFTPADDING", (0,0), (-1,-1), 16),
    ("RIGHTPADDING", (0,0), (-1,-1), 16),
    ("TOPPADDING", (0,0), (0,0), 14),
    ("BOTTOMPADDING", (0,0), (0,0), 8),
    ("TOPPADDING", (0,1), (0,1), 6),
    ("BOTTOMPADDING", (0,2), (0,2), 16),
    ("LINEBELOW", (0,0), (0,0), 0.6, colors.HexColor("#34A85A")),
]))
story.append(banner)
story.append(Spacer(1, 14))

# --- Datos del documento ---
meta = Table([
    [Paragraph("Preparado para", st_small), Paragraph("Preparado por", st_small)],
    [Paragraph("<b>Marand Company</b><br/>Sra. Mariela Camones<br/>mariela@marand.com.pe", st_cell),
     Paragraph("<b>AUTOMATIZAESTO.COM E.I.R.L.</b><br/>Victor Cardena &mdash; Founder &amp; CTO<br/>hola@automatizaesto.com", st_cell)],
], colWidths=[85*mm, 85*mm])
meta.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), GRIS_CLARO),
    ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
    ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ("TOPPADDING", (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
]))
story.append(meta)
story.append(Spacer(1, 4))
story.append(Paragraph("Ica, 25 de junio de 2026 &nbsp;&middot;&nbsp; Validez de la oferta: 30 dias", st_small))
story.append(Spacer(1, 10))

# --- 1. Resumen ---
story.append(Paragraph("1. Resumen", st_h))
story.append(Paragraph(
    "Tras la revision del prototipo, presentamos la propuesta para implementar "
    "<b>AgroQuality</b> en Marand Company: una solucion compuesta por una <b>app movil "
    "de captura</b> que el inspector usa en campo &mdash;incluso sin conexion&mdash; y una "
    "<b>plataforma web en la nube</b> donde la gerencia centraliza la informacion de las "
    "inspecciones de calidad post-cosecha, mantiene la trazabilidad de cada lote y controla "
    "el acceso mediante perfiles y permisos. La propuesta combina un <b>desarrollo a medida "
    "inicial</b> (la app movil de captura, construida para el flujo de Marand) con un "
    "<b>servicio SaaS (suscripcion mensual)</b> de operacion: nosotros alojamos, operamos "
    "y damos mantenimiento a la plataforma, sin que Marand compre licencias ni infraestructura propia.", st_body))

# --- 2. Que incluye ---
story.append(Paragraph("2. Que incluye el servicio", st_h))
incluye = [
    "<b>App movil del inspector (offline)</b>: captura de la inspeccion en campo &mdash;cabecera del lote, pallets, defectos, fotos y termografia&mdash; sin necesidad de senal; sincroniza automaticamente al recuperar conexion.",
    "<b>Gestion de inspecciones</b>: registro de cabecera del lote, pallets y defectos, con scoring automatico Good / Fair / Poor.",
    "<b>Panel del gerente</b>: KPIs, distribucion de scores, Pareto de defectos y filtro por periodo de ingreso.",
    "<b>Reporte profesional</b> tipo internacional: galerias de fotos por pallet y contenedor, ficha tecnica (firmeza, brix, PLU), termografia y trazabilidad.",
    "<b>Control de acceso por roles</b> y aislamiento de datos por empresa: solo personal autorizado de Marand ve la informacion.",
    "<b>Exportacion de datos</b> (CSV) y almacenamiento seguro de fotos en la nube.",
    "<b>Alojamiento, mantenimiento, respaldos y actualizaciones</b> incluidos durante toda la suscripcion.",
]
story.append(ListFlowable(
    [ListItem(Paragraph(t, st_li), leftIndent=6, value="•") for t in incluye],
    bulletType="bullet", start="•", leftIndent=10,
))

# --- 3. Inversion ---
story.append(Paragraph("3. Inversion", st_h))

def price_row(concepto, detalle, precio):
    return [
        Paragraph(concepto, st_cellb),
        Paragraph(detalle, st_cell),
        Paragraph(precio, st_price),
    ]

tbl = Table([
    [Paragraph("Concepto", st_kpi), Paragraph("Detalle", st_kpi), Paragraph("Inversion", S("kpir", parent=st_kpi, alignment=TA_RIGHT))],
    price_row("Desarrollo e implementacion (pago unico)",
              "App movil de captura a medida, configuracion de la empresa, carga inicial, "
              "capacitacion y soporte de arranque.",
              "S/ 3,500"),
    price_row("Plan piloto (meses 1 y 2)",
              "Tarifa promocional 50% para validar la plataforma con datos reales de Marand.",
              "S/ 600 / mes"),
    price_row("Plan AgroQuality (desde el mes 3)",
              "Suscripcion mensual completa: usuarios e inspecciones ilimitados de la empresa.",
              "S/ 1,200 / mes"),
], colWidths=[52*mm, 78*mm, 40*mm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), VERDE),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, VERDE_CLARO]),
    ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5C0")),
    ("INNERGRID", (0,0), (-1,-1), 0.4, colors.HexColor("#E5E7EB")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ("TOPPADDING", (0,0), (-1,-1), 8),
    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
]))
story.append(tbl)
story.append(Spacer(1, 5))
story.append(Paragraph(
    "Los montos estan expresados en soles (PEN) y <b>no incluyen IGV (18%)</b>. "
    "El desarrollo e implementacion es un <b>pago unico</b> al inicio del proyecto; "
    "la suscripcion se factura de forma mensual. El plan piloto permite a Marand evaluar "
    "el servicio con un riesgo minimo antes de pasar a la tarifa plena.", st_small))

# --- 4. Condiciones ---
story.append(Paragraph("4. Condiciones comerciales", st_h))
cond = [
    "<b>Desarrollo (pago unico):</b> se factura al inicio del proyecto. Una vez entregada la app movil y puesta en marcha la plataforma, comienza la suscripcion.",
    "<b>Modalidad:</b> suscripcion mensual (SaaS). Sin permanencia forzada; se puede dar de baja con 30 dias de aviso.",
    "<b>Descuento anual:</b> al contratar 12 meses por adelantado, se aplican 2 meses de cortesia (equivalente a ~17% de ahorro).",
    "<b>Soporte:</b> atencion por correo en horario laboral incluida en la suscripcion.",
    "<b>Mejoras:</b> las nuevas funcionalidades del roadmap se liberan sin costo adicional para Marand.",
    "<b>Datos:</b> la informacion es propiedad de Marand; se entrega export completo ante una eventual baja.",
]
story.append(ListFlowable(
    [ListItem(Paragraph(t, st_li), leftIndent=6, value="•") for t in cond],
    bulletType="bullet", start="•", leftIndent=10,
))

# --- 5. Proximos pasos ---
story.append(Paragraph("5. Proximos pasos", st_h))
story.append(Paragraph(
    "Con su conformidad, activamos el plan piloto y agendamos la sesion de capacitacion "
    "para el equipo de Marand. Quedamos atentos a sus comentarios para ajustar la propuesta "
    "a sus necesidades.", st_body))
story.append(Spacer(1, 16))
story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#E5E7EB")))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "AUTOMATIZAESTO.COM E.I.R.L. &nbsp;&middot;&nbsp; RUC 20616090608 &nbsp;&middot;&nbsp; "
    "Calle 1 N.&deg; 147, Urb. Parques de Villasol &nbsp;&middot;&nbsp; "
    "hola@automatizaesto.com &nbsp;&middot;&nbsp; www.automatizaesto.com", st_small))

doc = SimpleDocTemplate(OUT, pagesize=A4,
                        leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=16*mm, bottomMargin=14*mm,
                        title="Propuesta Economica AgroQuality - Marand",
                        author="AUTOMATIZAESTO.COM E.I.R.L.")
doc.build(story)
print("OK:", OUT)
