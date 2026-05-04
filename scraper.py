"""
scraper.py — Fotocasa scraper con scroll para activar lazy loading.

Fotocasa carga los artículos al hacer scroll. Sin scroll, solo aparecen
los primeros 3. El script hace scroll gradual hasta el final de la página
antes de parsear.
"""

import csv
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import ZONAS, SCRAPER, ZENROWS
from idealista import scrape_idealista

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

ARCHIVO_RAW    = DATA_DIR / "anuncios_raw.csv"
ARCHIVO_VISTOS = DATA_DIR / "vistos.json"

# ---------------------------------------------------------------------------
# Deduplicador
# ---------------------------------------------------------------------------

def cargar_vistos():
    if ARCHIVO_VISTOS.exists():
        return set(json.loads(ARCHIVO_VISTOS.read_text()))
    return set()

def guardar_vistos(vistos):
    ARCHIVO_VISTOS.write_text(json.dumps(list(vistos)))

# ---------------------------------------------------------------------------
# Scroll para activar lazy loading
# ---------------------------------------------------------------------------

def scroll_hasta_el_final(page, pausa=0.4):
    """Hace scroll gradual hasta el final de la página para cargar todos los artículos."""
    altura_total = page.evaluate("document.body.scrollHeight")
    posicion = 0
    paso = 600  # píxeles por paso

    while posicion < altura_total:
        posicion = min(posicion + paso, altura_total)
        page.evaluate(f"window.scrollTo(0, {posicion})")
        time.sleep(pausa)
        # La página puede crecer al cargar más contenido
        altura_total = page.evaluate("document.body.scrollHeight")

    # Vuelve arriba
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)

# ---------------------------------------------------------------------------
# Parser Fotocasa
# ---------------------------------------------------------------------------

def limpiar_precio(texto):
    """'7.150.000 €' → 7150000"""
    digits = re.sub(r"[^\d]", "", texto)
    return int(digits) if digits else None

def parsear_articulo(item, zona_nombre):
    # --- URL e ID ---
    url = ""
    item_id = ""
    for link in item.query_selector_all("a[href]"):
        href = link.get_attribute("href") or ""
        if "/es/comprar/vivienda/" in href and "/d" in href and "?" not in href:
            url = f"https://www.fotocasa.es{href}" if href.startswith("/") else href
            m = re.search(r"/(\d{7,})/d", href)
            item_id = f"fotocasa_{m.group(1)}" if m else ""
            break

    if not item_id or not url:
        return None

    texto = item.inner_text()

    # Artículo vacío (lazy loading no activado)
    if not texto.strip() or len(texto.strip()) < 20:
        return None

    # --- Filtro geográfico estricto ---
    # Fotocasa rellena con resultados de zonas cercanas. Solo aceptamos si el texto
    # menciona explícitamente cada palabra clave de la zona (más de 4 letras).
    texto_lower = texto.lower()
    palabras_zona = [p for p in re.split(r"[\s\-–,]+", zona_nombre.lower()) if len(p) > 4]
    if not all(p in texto_lower for p in palabras_zona):
        return None

    # --- Precio ---
    precio = None
    m = re.search(r"([\d\.]+)\s*€", texto)
    if m:
        precio = limpiar_precio(m.group(1))
    if not precio:
        return None

    # --- Título ---
    titulo = ""
    for linea in texto.split("\n"):
        linea = linea.strip()
        if re.search(r"(casa|chalet|piso|apartamento|finca|villa|ático|duplex|adosado)", linea, re.IGNORECASE):
            titulo = linea
            break

    # --- m² y habitaciones ---
    m2 = None
    habitaciones = None
    match_m2 = re.search(r"(\d+)\s*m²", texto)
    if match_m2:
        m2 = int(match_m2.group(1))
    match_hab = re.search(r"(\d+)\s*hab", texto, re.IGNORECASE)
    if match_hab:
        habitaciones = int(match_hab.group(1))

    # --- Tipo vendedor ---
    tipo_vendedor = "desconocido"
    if re.search(r"anunciante\s+particular|particular", texto, re.IGNORECASE):
        tipo_vendedor = "particular"
    elif re.search(r"agencia|inmobiliaria|real\s+estate|properties|homes|realty|pozuelo|gilmar|lucas\s+fox|engel", texto, re.IGNORECASE):
        tipo_vendedor = "agencia"

    # --- Bajada de precio ---
    bajada = bool(re.search(r"precio\s+reducido|baj[oó]\s+precio|rebaj", texto, re.IGNORECASE))

    # --- Antigüedad ---
    antiguedad = ""
    m_ant = re.search(r"(Hoy|Hace \d+ d[íi]as?|Hace \d+ semanas?|Más de \d+ mes(?:es)?)", texto)
    if m_ant:
        antiguedad = m_ant.group(1)

    return {
        "id":            item_id,
        "fuente":        "fotocasa",
        "zona":          zona_nombre,
        "titulo":        titulo[:120],
        "precio":        precio,
        "m2":            m2,
        "habitaciones":  habitaciones,
        "precio_m2":     round(precio / m2, 0) if precio and m2 else None,
        "bajada_precio": bajada,
        "tipo_vendedor": tipo_vendedor,
        "antiguedad":    antiguedad,
        "url":           url,
        "fecha_scrape":  datetime.now().strftime("%Y-%m-%d"),
    }


def parsear_fotocasa_page(page, zona_nombre):
    anuncios = []
    try:
        page.wait_for_selector("article", timeout=15000)
    except PlaywrightTimeout:
        print("    [!] Timeout esperando artículos")
        return []

    # Scroll para activar lazy loading antes de parsear
    print("    Haciendo scroll para cargar todos los anuncios...")
    scroll_hasta_el_final(page)
    time.sleep(1)

    todos = page.query_selector_all("article")
    items = [i for i in todos if "@container" in (i.get_attribute("class") or "")]
    if not items:
        items = todos

    print(f"    {len(items)} artículos tras scroll")

    for item in items:
        try:
            anuncio = parsear_articulo(item, zona_nombre)
            if anuncio:
                anuncios.append(anuncio)
        except Exception as e:
            print(f"    [!] Error: {e}")

    print(f"    {len(anuncios)} anuncios válidos")
    return anuncios

# ---------------------------------------------------------------------------
# Paginación
# ---------------------------------------------------------------------------

def url_pagina_fotocasa(url_base, pagina):
    url = url_base.rstrip("/")
    if pagina == 1:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}page={pagina}"

# ---------------------------------------------------------------------------
# Scraping de una zona
# ---------------------------------------------------------------------------

def scrape_zona(zona, browser):
    nombre = zona["nombre"]
    vistos = cargar_vistos()
    nuevos = []

    print(f"\n{'='*60}")
    print(f"  Zona: {nombre}")
    print(f"{'='*60}")

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )
    context.set_extra_http_headers({
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })

    page = context.new_page()
    page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,ico}", lambda route: route.abort())

    print("\n  [Fotocasa]")
    primera_pagina = True

    for pagina in range(1, SCRAPER["max_paginas"] + 1):
        url = url_pagina_fotocasa(zona["fotocasa_url"], pagina)
        print(f"    Página {pagina}: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(random.uniform(SCRAPER["delay_min"], SCRAPER["delay_max"]))

            if primera_pagina:
                for selector in [
                    "#didomi-notice-agree-button",
                    "button[data-testid='TcfAccept']",
                    "button:has-text('Aceptar todo')",
                    "button:has-text('Aceptar')",
                ]:
                    try:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            btn.click()
                            time.sleep(2)
                            break
                    except Exception:
                        pass
                primera_pagina = False

            time.sleep(1)

            anuncios = parsear_fotocasa_page(page, nombre)

            if not anuncios:
                print("    Sin anuncios válidos, fin de resultados.")
                break

            nuevos_pagina = 0
            for a in anuncios:
                if a["id"] not in vistos:
                    nuevos.append(a)
                    vistos.add(a["id"])
                    nuevos_pagina += 1

            print(f"    {nuevos_pagina} nuevos de {len(anuncios)}")

        except Exception as e:
            print(f"    [!] Error en página {pagina}: {e}")
            break

    context.close()
    guardar_vistos(vistos)

    # --- Idealista (via Zenrows) ---
    if ZENROWS["habilitado"]:
        nuevos_idealista = scrape_idealista(zona, vistos)
        nuevos.extend(nuevos_idealista)
        guardar_vistos(vistos)

    print(f"\n  Total nuevos en {nombre}: {len(nuevos)}")
    return nuevos

# ---------------------------------------------------------------------------
# Guardar CSV
# ---------------------------------------------------------------------------

def guardar_raw(anuncios):
    if not anuncios:
        return
    campos = ["id", "fuente", "zona", "titulo", "precio", "m2",
              "habitaciones", "precio_m2", "bajada_precio", "tipo_vendedor",
              "antiguedad", "url", "fecha_scrape"]
    modo = "a" if ARCHIVO_RAW.exists() else "w"
    with open(ARCHIVO_RAW, mode=modo, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        if modo == "w":
            writer.writeheader()
        writer.writerows(anuncios)
    print(f"\n  Guardados {len(anuncios)} anuncios en {ARCHIVO_RAW}")

# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def run():
    print(f"\n{'#'*60}")
    print(f"  SCRAPER DE CAPTACIÓN — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Zonas: {len(ZONAS)} | Fuente: Fotocasa")
    print(f"  Nota: Idealista bloquea scraping automatizado")
    print(f"{'#'*60}")

    todos_nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        for zona in ZONAS:
            nuevos = scrape_zona(zona, browser)
            todos_nuevos.extend(nuevos)
        browser.close()

    guardar_raw(todos_nuevos)

    print(f"\n{'#'*60}")
    print(f"  TOTAL ANUNCIOS NUEVOS: {len(todos_nuevos)}")
    print(f"{'#'*60}\n")

    return todos_nuevos

if __name__ == "__main__":
    run()
