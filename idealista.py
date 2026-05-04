"""
idealista.py — Scraper de Idealista usando Zenrows como proxy anti-DataDome.

Zenrows actúa como intermediario: recibe la petición, la ejecuta desde
una IP residencial real con un navegador real, y nos devuelve el HTML limpio.
DataDome ve un usuario normal, no un bot.

Uso de créditos (plan gratuito: 1.000/mes):
  - js_render=True gasta 5 créditos por petición
  - 1 página = 5 créditos → 200 páginas/mes con el plan gratuito
  - Para 1 búsqueda diaria × 1 página = 30 páginas/mes = 150 créditos → bien dentro del límite
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import ZONAS, SCRAPER, ZENROWS


# ---------------------------------------------------------------------------
# Cliente Zenrows
# ---------------------------------------------------------------------------

def fetch_con_zenrows(url):
    """
    Descarga una URL pasando por Zenrows con Premium Proxies.
    Idealista usa DataDome — Premium Proxies es obligatorio según el Playground de Zenrows.
    """
    if not ZENROWS["api_key"]:
        print("  [!] Zenrows no configurado — añade tu API key en config.py")
        return None

    try:
        from zenrows import ZenRowsClient
    except ImportError:
        print("  [!] Falta la librería zenrows — ejecuta: pip3 install zenrows")
        return None

    try:
        time.sleep(random.uniform(SCRAPER["delay_min"], SCRAPER["delay_max"]))
        client = ZenRowsClient(ZENROWS["api_key"])
        params = {
            "premium_proxy": "true",
            "antibot": "true",
        }
        if ZENROWS["js_render"]:
            params["js_render"] = "true"
        r = client.get(url, params=params)
        if r.status_code == 200:
            # Comprueba que no nos han redirigido a la home
            if "items-container" not in r.text and 'class="item"' not in r.text:
                print(f"  [!] Idealista devolvió la home en vez de resultados — posible bloqueo parcial")
                return None
            return r.text
        else:
            print(f"  [!] Zenrows HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"  [!] Error Zenrows: {e}")

    return None


# ---------------------------------------------------------------------------
# Parser Idealista
# Selectores confirmados por el artículo de thewebscraping.club:
#   - article.item  → cada anuncio
#   - a.item-link   → título y URL
#   - span.item-price → precio
#   - span.item-detail → detalles (m², habitaciones)
# ---------------------------------------------------------------------------

def parsear_pagina_idealista(html, zona_nombre):
    """Extrae anuncios de una página de resultados de Idealista."""
    soup = BeautifulSoup(html, "lxml")
    anuncios = []

    items = soup.find_all("article", class_="item")
    if not items:
        # Fallback por si cambian la estructura
        items = soup.select("article[class*='item']")

    for item in items:
        try:
            anuncio = _parsear_item(item, zona_nombre)
            if anuncio:
                anuncios.append(anuncio)
        except Exception as e:
            print(f"    [!] Error parseando item: {e}")

    return anuncios


def _parsear_item(item, zona_nombre):
    # --- ID y URL ---
    item_id = item.get("data-element-id") or item.get("data-adid") or ""
    link = item.find("a", class_="item-link")

    if not link:
        return None

    href = link.get("href", "")
    if not item_id:
        m = re.search(r"/inmueble/(\d+)/", href)
        item_id = f"idealista_{m.group(1)}" if m else ""

    if not item_id:
        return None

    url = f"https://www.idealista.com{href}" if href.startswith("/") else href
    titulo = (link.get("title") or link.get_text(strip=True))[:120]

    # --- Precio ---
    precio = None
    precio_tag = item.find("span", class_="item-price")
    if precio_tag:
        digits = re.sub(r"[^\d]", "", precio_tag.get_text())
        precio = int(digits) if digits else None

    if not precio:
        return None

    # --- Detalles: m² y habitaciones ---
    m2 = None
    habitaciones = None
    detalles = item.find_all("span", class_="item-detail")
    for d in detalles:
        txt = d.get_text(strip=True)
        if "m²" in txt and m2 is None:
            m = re.search(r"(\d+)", txt)
            if m:
                m2 = int(m.group(1))
        elif re.search(r"hab", txt, re.IGNORECASE) and habitaciones is None:
            m = re.search(r"(\d+)", txt)
            if m:
                habitaciones = int(m.group(1))

    # --- Bajada de precio ---
    bajada = bool(item.find(class_=re.compile(r"price.down|bajada", re.I)))

    # --- Tipo vendedor ---
    tipo_vendedor = "desconocido"
    if item.find(class_=re.compile(r"agency|inmobiliaria|logo", re.I)):
        tipo_vendedor = "agencia"
    texto_completo = item.get_text()
    if re.search(r"particular", texto_completo, re.IGNORECASE):
        tipo_vendedor = "particular"

    return {
        "id":            item_id,
        "fuente":        "idealista",
        "zona":          zona_nombre,
        "titulo":        titulo,
        "precio":        precio,
        "m2":            m2,
        "habitaciones":  habitaciones,
        "precio_m2":     round(precio / m2, 0) if precio and m2 else None,
        "bajada_precio": bajada,
        "tipo_vendedor": tipo_vendedor,
        "antiguedad":    "",
        "url":           url,
        "fecha_scrape":  datetime.now().strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# Paginación
# ---------------------------------------------------------------------------

def url_pagina(url_base, pagina):
    url = url_base.rstrip("/")
    return url + "/" if pagina == 1 else url + f"/pagina-{pagina}.htm"


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def scrape_idealista(zona, vistos):
    """
    Scrapea Idealista para una zona usando Zenrows.
    Devuelve lista de anuncios nuevos (no vistos antes).
    """
    if not ZENROWS["habilitado"]:
        print("  [Idealista] Zenrows desactivado — configura la API key en config.py")
        return []

    nombre = zona["nombre"]
    nuevos = []

    print(f"\n  [Idealista — Zenrows]")

    for pagina in range(1, SCRAPER["max_paginas"] + 1):
        url = url_pagina(zona["idealista_url"], pagina)
        print(f"    Página {pagina}: {url}")

        html = fetch_con_zenrows(url)
        if not html:
            print("    Sin respuesta, parando.")
            break

        # Comprueba si DataDome sigue bloqueando
        if "datadome" in html.lower() or len(html) < 5000:
            print("    [!] Posible bloqueo de DataDome. Prueba activando premium_proxy en config.py")
            break

        anuncios = parsear_pagina_idealista(html, nombre)
        if not anuncios:
            print("    Sin anuncios, fin de resultados.")
            break

        nuevos_pagina = 0
        for a in anuncios:
            if a["id"] not in vistos:
                nuevos.append(a)
                vistos.add(a["id"])
                nuevos_pagina += 1

        print(f"    {len(anuncios)} anuncios, {nuevos_pagina} nuevos")

        # Si ninguno es nuevo, Idealista está repitiendo página → paramos
        if nuevos_pagina == 0:
            print("    Sin anuncios nuevos, fin de resultados.")
            break

    return nuevos
