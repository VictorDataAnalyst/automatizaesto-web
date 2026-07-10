# Marca automatizaesto — assets "Ae"

## Archivos

| Archivo | Uso |
|---|---|
| `logo-ae.svg` | Maestro vectorial, fondo transparente |
| `logo-ae-tile.svg` | Maestro en tile oscuro (avatares, favicon) |
| `logo-ae-1024.png` / `logo-ae-512.png` | Avatar para redes (Instagram, LinkedIn, WhatsApp Business) |
| `logo-ae-transparente-1024.png` | Para poner sobre fotos o fondos propios |
| `social/banner-01-presentacion.png` | Post de presentación de marca (1080×1080) |
| `social/banner-02-caso-boletas.png` | Post caso boletas 4 h → 5 min (1080×1080) |
| `social/banner-03-caso-reporteria.png` | Post caso reportería 4 h → 30 min (1080×1080) |
| `render.html` | Generador: los textos de los banners se editan aquí (bloque `DATOS`) |

## Cómo crear o editar banners

1. Abre `render.html` y edita el bloque `DATOS` (textos, métricas, pies).
   Para un banner nuevo, agrega un objeto más al arreglo `banners`.
2. Regenera los PNG con Chrome (una línea por banner):

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=12000 --window-size=1080,1080 --screenshot="RUTA\social\banner-01-presentacion.png" "file:///RUTA/render.html?v=banner&n=1"
```

Reemplaza `RUTA` por esta carpeta y `n=1|2|3…` por el banner que quieras.
Para los logos: `?v=logo-tile` (1024 o 512 en `--window-size`) y `?v=logo-trans`
con `--default-background-color=00000000`.

## Colores de marca

Fondo `#0B1220` · azul `#3B82F6` · cian `#38BDF8` · texto `#E8EDF6` · plomo `#9DA9BF`.
Tipografía: Plus Jakarta Sans (títulos 700/800) + monoespaciada del sistema (números y etiquetas).
