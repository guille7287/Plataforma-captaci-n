"""
scorer.py — Calcula el score de captación (0–100) para cada anuncio.

Criterios y pesos (configurables en config.py):
  - Precio vs. mercado (50%): cuánto por debajo del precio medio €/m² de la zona
  - Señales de urgencia (30%): bajada de precio, días en mercado
  - Tipo de vendedor (20%): particular > desconocido > agencia

Score final: 0–100. Por encima del umbral configurado → candidato a captar.
"""

import csv
import json
from datetime import datetime, date
from pathlib import Path

from config import ZONAS, SCORING

DATA_DIR = Path("data")
ARCHIVO_RAW    = DATA_DIR / "anuncios_raw.csv"
ARCHIVO_SCORED = DATA_DIR / "anuncios_scored.csv"
ARCHIVO_DIAS   = DATA_DIR / "dias_mercado.json"   # {id: fecha_primera_vez_visto}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cargar_csv(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cargar_dias_mercado():
    if ARCHIVO_DIAS.exists():
        return json.loads(ARCHIVO_DIAS.read_text())
    return {}


def guardar_dias_mercado(d):
    ARCHIVO_DIAS.write_text(json.dumps(d))


def precio_medio_zona(zona_nombre):
    for z in ZONAS:
        if z["nombre"] == zona_nombre:
            return z["precio_medio_m2"]
    return None


def dias_en_mercado(anuncio_id, fecha_scrape, registro):
    """Días desde que vimos el anuncio por primera vez."""
    if anuncio_id not in registro:
        registro[anuncio_id] = fecha_scrape
    primera = datetime.strptime(registro[anuncio_id], "%Y-%m-%d").date()
    hoy = datetime.strptime(fecha_scrape, "%Y-%m-%d").date()
    return (hoy - primera).days


# ---------------------------------------------------------------------------
# Cálculo de score por criterio
# ---------------------------------------------------------------------------

def score_precio(precio_m2_anuncio, precio_medio):
    """
    Devuelve 0–100 según qué tan por debajo del precio medio está el anuncio.
    - Al precio medio o más caro → 0
    - descuento_max% o más barato → 100
    - Entre medias → interpolación lineal
    """
    if precio_m2_anuncio is None or precio_medio is None:
        return 50  # sin datos → puntuación neutral

    descuento_pct = (precio_medio - precio_m2_anuncio) / precio_medio * 100
    desc_max = SCORING["descuento_max"]
    desc_min = SCORING["descuento_min"]

    if descuento_pct <= desc_min:
        return 0
    if descuento_pct >= desc_max:
        return 100
    return round((descuento_pct - desc_min) / (desc_max - desc_min) * 100)


def score_urgencia(bajada_precio, dias):
    """
    0–100 combinando señal de bajada de precio y días en mercado.
    - bajada de precio confirmada → +50 puntos base
    - días en mercado: 0 días → 0 pts, dias_urgencia+ → 50 pts
    """
    puntos = 0

    # Bajada de precio explícita en el portal
    if str(bajada_precio).lower() in ("true", "1", "sí", "si"):
        puntos += 50

    # Días en mercado
    umbral = SCORING["dias_urgencia"]
    if dias >= umbral:
        puntos += 50
    else:
        puntos += round(dias / umbral * 50)

    return min(puntos, 100)


def score_vendedor(tipo_vendedor):
    """Particular es más fácil de captar que agencia."""
    mapa = {
        "particular":   100,
        "desconocido":   50,
        "agencia":       20,
    }
    return mapa.get(tipo_vendedor.lower() if tipo_vendedor else "desconocido", 50)


# ---------------------------------------------------------------------------
# Score total
# ---------------------------------------------------------------------------

def calcular_score(anuncio, dias):
    precio_medio = precio_medio_zona(anuncio["zona"])

    precio_m2 = None
    if anuncio.get("precio_m2"):
        try:
            precio_m2 = float(anuncio["precio_m2"])
        except (ValueError, TypeError):
            pass

    s_precio    = score_precio(precio_m2, precio_medio)
    s_urgencia  = score_urgencia(anuncio.get("bajada_precio"), dias)
    s_vendedor  = score_vendedor(anuncio.get("tipo_vendedor", "desconocido"))

    score_total = round(
        s_precio   * SCORING["peso_precio"] / 100 +
        s_urgencia * SCORING["peso_urgencia"] / 100 +
        s_vendedor * SCORING["peso_vendedor"] / 100
    )

    return {
        **anuncio,
        "score_precio":   s_precio,
        "score_urgencia": s_urgencia,
        "score_vendedor": s_vendedor,
        "score_total":    score_total,
        "dias_mercado":   dias,
        "precio_medio_zona": precio_medio,
    }


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def run(anuncios_nuevos=None):
    """
    Recalcula scores para todos los anuncios (o solo los nuevos si se pasan).
    Devuelve lista de anuncios con score >= score_minimo, ordenados por score.
    """
    print(f"\n{'='*60}")
    print(f"  SCORING DE OPORTUNIDADES")
    print(f"{'='*60}")

    # Si no se pasan anuncios nuevos, carga todos del CSV
    if anuncios_nuevos is None:
        anuncios_nuevos = cargar_csv(ARCHIVO_RAW)

    if not anuncios_nuevos:
        print("  Sin anuncios para puntuar.")
        return []

    registro_dias = cargar_dias_mercado()
    resultados = []

    for a in anuncios_nuevos:
        dias = dias_en_mercado(a["id"], a.get("fecha_scrape", str(date.today())), registro_dias)
        scored = calcular_score(a, dias)
        resultados.append(scored)

    guardar_dias_mercado(registro_dias)

    # Ordenar por score descendente
    resultados.sort(key=lambda x: x["score_total"], reverse=True)

    # Guardar todos con score
    campos = list(resultados[0].keys()) if resultados else []
    with open(ARCHIVO_SCORED, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)

    # Filtrar por score mínimo
    oportunidades = [r for r in resultados if r["score_total"] >= SCORING["score_minimo"]]

    print(f"  Anuncios procesados: {len(resultados)}")
    print(f"  Oportunidades (score ≥ {SCORING['score_minimo']}): {len(oportunidades)}")

    return oportunidades


if __name__ == "__main__":
    oportunidades = run()
    print(f"\nTop 5 oportunidades:")
    for i, o in enumerate(oportunidades[:5], 1):
        print(f"  {i}. [{o['score_total']}] {o['titulo'][:60]} — {o['precio']:,}€ — {o['url']}")
