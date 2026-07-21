# Migración de marca · Familia Ae

**Decisión (21 jul 2026):** los productos pasan de nombres descriptivos a marca de casa
con descriptor, estilo IBM.

| Antes | Ahora |
|---|---|
| AgroQuality | **Ae Quality** |
| AgroField | **Ae Field** |
| Forecast | **Ae Forecast** |

Regla de escritura: siempre `Ae` + espacio + descriptor en mayúscula inicial.
El monograma **Ae** acompaña a cada producto con el color de acento que le corresponde
(esmeralda en Ae Quality, Ion en el resto).

---

## ✅ Hecho (ya en el código)

- Nombre de marca actualizado en **todas** las páginas públicas: home, Compañía,
  Productos, AI, Casos, Portafolio, Blog, landings de producto, legal y libro de
  reclamaciones (118 sustituciones).
- Títulos, meta descriptions, Open Graph y datos estructurados (JSON-LD) al día.
- Monograma: la λ de las landings de producto y del login se reemplazó por el
  sello **Ae** con la tipografía de marca.
- Verificado: sin rastros de los nombres antiguos, enlaces internos intactos,
  JSON-LD válido.

## ⚠️ Deliberadamente NO tocado (y por qué)

| Elemento | Estado | Razón |
|---|---|---|
| Carpetas `/agroquality/`, `/agrofield/`, `/forecast/` | Sin cambios | Las URLs ya están indexadas en Google. Renombrarlas cuesta posicionamiento sin ganar nada: **la URL no es la marca**. Si algún día se renombran, debe hacerse con 301 desde las antiguas. |
| Subdominio `agroquality.automatizaesto.com` | Sin cambios | Requiere DNS + certificado + configuración en Render. Ver abajo. |
| Prefijos de base de datos `aq_*` | Sin cambios | Son plomería interna, invisible para el cliente. Renombrar tablas en producción es riesgo puro sin beneficio de marca. |
| Bucket `agroquality-fotos` | Sin cambios | Mismo criterio: interno, con URLs firmadas ya en uso. |

## 📋 Pendiente — requiere acción tuya

1. **INDECOPI:** verificar disponibilidad y registrar la marca `AutomatizaEsto` y,
   si procede, los nombres de producto. Es el paso que convierte el nombre en activo.
2. **Subdominio (opcional):** si quieres `quality.automatizaesto.com`,
   el orden seguro es — crear el nuevo registro DNS → añadir el dominio en Render →
   verificar certificado → dejar el antiguo redirigiendo 301 durante al menos 6 meses.
   Hasta entonces, el subdominio actual sigue funcionando sin problema.
3. **Aviso a Marand:** un correo corto explicando que la plataforma ahora se llama
   Ae Quality, que no cambia nada en su acceso ni en sus datos, y que el enlace de
   siempre sigue funcionando.
4. **Perfiles públicos:** actualizar el nombre en LinkedIn de la empresa y en
   cualquier material comercial (propuestas, presentaciones).

## Nota de arquitectura de marca

El sistema elegido hace que cada producto dependa de la marca madre — esa es su
fortaleza (todo refuerza a AutomatizaEsto) y su límite (ningún producto camina solo).
Si en el futuro un producto crece lo suficiente para venderse o escindirse, ese será
el momento de darle nombre propio; la arquitectura actual lo permite sin rehacer el sitio.
