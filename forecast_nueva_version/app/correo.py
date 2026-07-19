# =====================================================================
# Correo del informe + plan operativo.
# "Generar ahora, enviar luego": construye el HTML del correo siempre.
# El envío real se activa solo si hay un proveedor configurado por env:
#   - RESEND_API_KEY (+ EMAIL_FROM)            -> Resend (API simple)
#   - SMTP_HOST / SMTP_USER / SMTP_PASS (...)  -> SMTP propio
# Sin credenciales, devuelve enviado=False con el motivo; el frontend
# igual muestra la vista previa y permite descargar el .html.
# =====================================================================
import json
import os
import smtplib
import urllib.request
from email.mime.text import MIMEText

ORO = "#C8901C"
NAVY = "#0C1A2E"
MUTED = "#5A7391"


def proveedor() -> str | None:
    if os.environ.get("RESEND_API_KEY"):
        return "resend"
    if os.environ.get("SMTP_HOST"):
        return "smtp"
    return None


def construir_html(inf: dict, plan: dict | None, destino_nombre: str | None = None) -> str:
    k = inf.get("kpis", {})
    saludo = f"Hola{(' ' + destino_nombre) if destino_nombre else ''},"
    insights = inf.get("insights", [])[:5]

    filas_insight = "".join(
        f"""<tr><td style="padding:10px 0;border-bottom:1px solid #EEF3FA;">
              <div style="font-weight:600;color:{NAVY};font-size:15px;">{x.get('icono','')} {x.get('titulo','')}
                {f'<span style="float:right;color:{ORO};font-family:monospace;">{x["cifra"]}</span>' if x.get('cifra') else ''}</div>
              <div style="color:{MUTED};font-size:13px;margin-top:4px;">{x.get('resumen','')}</div>
            </td></tr>"""
        for x in insights)

    bloque_plan = ""
    if plan and plan.get("filas"):
        pac = plan.get("pacing", {})
        filas_plan = "".join(
            f"""<tr>
                  <td style="padding:7px 10px;border-bottom:1px solid #EEF3FA;font-family:monospace;font-size:12px;">{f['fecha']}</td>
                  <td style="padding:7px 10px;border-bottom:1px solid #EEF3FA;font-family:monospace;font-size:12px;text-align:right;">{f['volumen_objetivo']:,.0f}</td>
                  <td style="padding:7px 10px;border-bottom:1px solid #EEF3FA;font-family:monospace;font-size:12px;text-align:right;color:{MUTED};">{f['proyeccion']:,.0f}</td>
                  <td style="padding:7px 10px;border-bottom:1px solid #EEF3FA;font-family:monospace;font-size:12px;text-align:right;font-weight:700;color:{NAVY};">{f['personas_turno']}</td>
                </tr>"""
            for f in plan["filas"])
        bloque_plan = f"""
        <h2 style="font-size:17px;color:{NAVY};margin:28px 0 4px;">Plan operativo por fecha</h2>
        <div style="background:#F7F9FC;border-left:3px solid {ORO};border-radius:8px;padding:12px 14px;font-size:13px;color:{NAVY};margin-bottom:12px;">
          {pac.get('mensaje','')}
        </div>
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <th style="text-align:left;font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;padding:6px 10px;">Fecha</th>
            <th style="text-align:right;font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;padding:6px 10px;">Objetivo</th>
            <th style="text-align:right;font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;padding:6px 10px;">Proyección</th>
            <th style="text-align:right;font-size:11px;color:{MUTED};text-transform:uppercase;letter-spacing:.05em;padding:6px 10px;">Pers./turno</th>
          </tr>
          {filas_plan}
        </table>
        <p style="font-size:12px;color:{MUTED};margin-top:8px;">
          Personas/turno = volumen objetivo de la fecha ÷ ({plan['productividad']:.0f} {plan['unidad']} por persona·turno × {plan['turnos']} turnos), redondeado hacia arriba.
          Pico: <b>{plan['personas_pico']}</b> personas/turno el {plan['fecha_pico']}.
        </p>"""

    return f"""<!DOCTYPE html><html><body style="margin:0;background:#EEF3FA;padding:24px 0;font-family:'Helvetica Neue',Arial,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid #DDE6F0;">
    <div style="background:{NAVY};padding:22px 28px;color:#fff;">
      <div style="font-size:18px;font-weight:700;">Forecast <span style="opacity:.6;font-weight:400;">· automatizaesto</span></div>
    </div>
    <div style="padding:24px 28px;">
      <p style="font-size:14px;color:{NAVY};">{saludo}</p>
      <p style="font-size:14px;color:{MUTED};margin-top:4px;">Este es el resumen de tu última proyección y, si lo generaste, tu plan operativo por fecha.</p>

      <div style="text-align:center;padding:16px 0 6px;">
        <div style="font-size:12px;color:{MUTED};text-transform:uppercase;letter-spacing:.1em;">Proyección · {k.get('horizonte','')} periodos {k.get('frecuencia_plural','')}</div>
        <div style="font-size:40px;font-weight:700;color:{NAVY};margin:6px 0;">{k.get('total_fmt','')} <span style="font-size:16px;color:{MUTED};">{k.get('unidad','')}</span></div>
        <div style="font-size:13px;color:{MUTED};">{k.get('veredicto','')}</div>
      </div>

      <h2 style="font-size:17px;color:{NAVY};margin:24px 0 4px;">Hallazgos principales</h2>
      <table style="width:100%;border-collapse:collapse;">{filas_insight}</table>
      {bloque_plan}

      <p style="font-size:12px;color:{MUTED};margin-top:28px;border-top:1px solid #EEF3FA;padding-top:14px;">
        Generado por Forecast · automatizaesto.com — los modelos se validan contra tu propia historia antes de proyectar.
      </p>
    </div>
  </div>
</body></html>"""


def enviar(destino: str, asunto: str, html: str) -> dict:
    """Envía si hay proveedor configurado; si no, informa el motivo."""
    prov = proveedor()
    if prov == "resend":
        remitente = os.environ.get("EMAIL_FROM", "Forecast <onboarding@resend.dev>")
        payload = json.dumps({"from": remitente, "to": [destino],
                              "subject": asunto, "html": html}).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails", data=payload, method="POST",
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return {"enviado": True, "id": json.loads(r.read() or b"{}").get("id")}
        except Exception as e:  # noqa: BLE001
            return {"enviado": False, "motivo": f"Resend rechazó el envío: {e}"}
    if prov == "smtp":
        try:
            msg = MIMEText(html, "html", "utf-8")
            msg["Subject"] = asunto
            msg["From"] = os.environ.get("EMAIL_FROM", os.environ["SMTP_USER"])
            msg["To"] = destino
            with smtplib.SMTP(os.environ["SMTP_HOST"],
                              int(os.environ.get("SMTP_PORT", "587"))) as s:
                s.starttls()
                s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
                s.send_message(msg)
            return {"enviado": True}
        except Exception as e:  # noqa: BLE001
            return {"enviado": False, "motivo": f"SMTP falló: {e}"}
    return {"enviado": False,
            "motivo": "Aún no hay proveedor de correo configurado. "
                      "Define RESEND_API_KEY o las variables SMTP_* para enviar de verdad."}
