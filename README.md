# Sistema de captación inmobiliaria

Scraper + scoring + informe HTML para Idealista y Fotocasa.

## Instalación (una sola vez)

```bash
# 1. Crea una carpeta para el proyecto
mkdir captacion && cd captacion

# 2. Copia aquí los 5 ficheros: config.py, scraper.py, scorer.py, reporter.py, main.py

# 3. Instala dependencias
pip3 install requests beautifulsoup4

# 4. Listo
```

## Uso diario

```bash
# Ciclo completo: scrapea → puntúa → abre informe en el navegador
python3 main.py

# Solo regenerar el informe (sin scrapear)
python3 main.py --solo-informe

# Recalcular scores cambiando pesos (sin scrapear)
python3 main.py --solo-score
```

## Añadir una zona nueva

Edita `config.py` y añade un bloque en la lista `ZONAS`:

```python
{
    "nombre": "Monte Alina - Pozuelo",
    "idealista_url": "https://www.idealista.com/venta-viviendas/pozuelo-de-alarcon/urbanizaciones/monte-alina/",
    "fotocasa_url": "https://www.fotocasa.es/es/comprar/viviendas/pozuelo-de-alarcon/monte-alina/l",
    "precio_medio_m2": 5500,
},
```

## Ajustar el scoring

En `config.py`, sección `SCORING`:
- `peso_precio / urgencia / vendedor`: redistribuye importancia (deben sumar 100)
- `descuento_max`: qué % de descuento te parece excelente oportunidad
- `dias_urgencia`: a partir de cuántos días activo consideras señal
- `score_minimo`: umbral para aparecer en el informe

## Automatizar con cron (opcional)

Para que se ejecute solo cada mañana a las 8:00:

```bash
crontab -e
# Añade esta línea (ajusta la ruta a tu carpeta):
0 8 * * * cd /ruta/a/captacion && python3 main.py >> data/log.txt 2>&1
```

## Ficheros generados

```
data/
  anuncios_raw.csv      → todos los anuncios scrapeados (histórico)
  anuncios_scored.csv   → todos los anuncios con su score
  vistos.json           → IDs ya procesados (deduplicador)
  dias_mercado.json     → fecha primera vez visto cada anuncio
  informe_YYYY-MM-DD.html → informe del día (se abre automáticamente)
```

## Nota sobre bloqueos

Idealista y Fotocasa tienen medidas anti-bot. Si ves errores 403:
- Aumenta `delay_min` y `delay_max` en `config.py` (p.ej. 8–15 segundos)
- Reduce `max_paginas` a 1–2
- Ejecuta en horarios de baja carga (madrugada, primera mañana)
- Si el problema persiste, considera usar la API oficial de Idealista
