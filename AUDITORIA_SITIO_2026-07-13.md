# Auditoría de automatizaesto.com — 13 jul 2026

Revisión de contenido (home, nosotros, servicios, blog) + auditoría técnica sobre el código fuente de esta carpeta. Ordenado por prioridad.

---

## P0 — Urgente: archivos internos expuestos públicamente

El sitio se publica en Netlify desde la raíz de esta carpeta, así que **todo lo que está aquí es descargable por cualquiera** que conozca (o adivine) la URL:

| Archivo | Riesgo |
|---|---|
| `Propuesta_Economica_AgroQuality_Marand.pdf` | Propuesta comercial con precios de un cliente, pública en `/Propuesta_Economica_AgroQuality_Marand.pdf` |
| `Presupuesto_Estimacion_AgroQuality.xlsx` | Presupuesto interno, público |
| `agroquality/OPERACIONES.md` | **Verificado accesible en producción.** Runbook con arquitectura, correo de cliente real (`mariela@marand.com.pe`), modelo de permisos, nota de que OAuth se ocultó porque bypasea la whitelist — un mapa para atacantes |
| `agroquality/app/` (código backend, `__pycache__`) | Código del servidor público (no hay secretos hardcodeados — verificado — pero no debería estar) |
| `agroquality/supabase/` (migraciones SQL, README) | Esquema completo de la BD público |
| `gen_propuesta_agroquality.py` | Script interno |
| `home-v2.html`, `redesign-preview.html`, `design-system/` | Borradores accesibles; pueden indexarse |

**Acción recomendada:** separar el sitio público del resto (repo o subcarpeta `public/` como publish dir en Netlify), o como mínimo borrar del deploy los archivos de cliente y el runbook hoy mismo. Los borradores, protegerlos o eliminarlos.

---

## P1 — Conversión

1. **`/casos/` y `/portafolio/` son páginas huérfanas.** Existen, tienen buen contenido (AgroField, forecast, flujos documentales) y están en el sitemap, pero **ninguna página del sitio las enlaza**. La home promete "ver resultados" y solo muestra dos tarjetas anónimas. Enlazar "Casos" en la navegación principal es probablemente la mejora de conversión más barata disponible.
2. **Números duros en resultados.** "De media jornada a minutos" → "de 4 h a 8 min". La sección se llama "números que lo prueban"; que los pruebe.
3. **Prueba social con nombre.** Testimonio con nombre/cargo o logos (tienes los logos de Concentrix y ubycall en `/Logos` — si hay permiso de uso, úsalos).
4. **CTA de agenda directa** (Calendly o similar) además del formulario y WhatsApp.
5. **Rango de precios orientativo** ("automatizaciones puntuales desde $X") en la sección de precios.

## P2 — SEO

1. **`og:locale` es `es_ES` en todas las páginas** → cambiar a `es_PE`.
2. **Schema.org:** hay `Organization`; agregar `ProfessionalService`/`LocalBusiness` con dirección, teléfono y zona de servicio (Perú) para SEO local. Crear perfil de Google Business.
3. **Servicios antiguos vivos y sin rumbo:** `servicios/automatizacion-leads.html`, `base-de-conocimiento.html`, `flujos-documentales.html` siguen publicados con el posicionamiento anterior (IA/PyMEs), no están en el sitemap y nada los enlaza. Decidir: actualizarlos y enlazarlos, o redirigirlos 301 a `/servicios.html`.
4. **Inconsistencia de URLs:** se mezclan `/servicios.html` y `/servicios` (ambas resuelven; el canonical apunta a `.html`). Elegir una forma y usarla en todos los enlaces internos.
5. **Blog:** dos artículos publicados y dos "próximamente" desde hace un mes. Publicar los pendientes o quitar las tarjetas — "próximamente" estancado resta credibilidad.
6. **Sitemap:** actualizar `lastmod` (todo dice junio) e incluir/excluir según lo que decidas en el punto 3.

## P3 — UX / técnico

1. **Cookie wall bloqueante** (`consent.js`): modal centrado que bloquea la navegación solo para GA4. Para cookies de analítica basta un banner discreto no bloqueante; el muro actual cuesta rebotes, sobre todo en móvil.
2. **Honeypot del formulario:** está bien implementado (`display:none` + Netlify honeypot) — descarto la observación de la revisión anterior.
3. **Cabeceras de seguridad** (`_headers`): bien configuradas (HSTS, nosniff, X-Frame-Options). Falta `Content-Security-Policy` — deseable, no urgente.
4. **PageSpeed:** la API no respondió durante la auditoría. El sitio es estático y liviano (index 56 KB, assets 624 KB), así que no anticipo problemas, pero vale correr https://pagespeed.web.dev/ manualmente sobre la home en móvil.

## Lo que está bien (no tocar)

Copy claro y diferenciado, meta tags y Open Graph completos, sitio estático rápido, fuentes self-hosted, GA4 solo tras consentimiento (RGPD), robots/sitemap presentes, sin secretos en el código, formulario Netlify con antispam.
