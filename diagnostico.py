"""
diagnostico.py — Guarda el HTML que ve Playwright de Idealista y Fotocasa.
Ejecuta esto y comparte los archivos data/debug_idealista.html y data/debug_fotocasa.html
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

URL_IDEALISTA = "https://www.idealista.com/venta-viviendas/pozuelo-de-alarcon/urbanizaciones/monteclaro/"
URL_FOTOCASA  = "https://www.fotocasa.es/es/comprar/viviendas/pozuelo-de-alarcon/monteclaro/l"

def diagnosticar(url, nombre, page):
    print(f"\n[{nombre}] Cargando {url} ...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)  # espera extra para JS

        # Intenta aceptar cookies
        for selector in [
            "#didomi-notice-agree-button",
            "button:has-text('Aceptar')",
            "button:has-text('Acepto')",
            "button:has-text('Accept')",
            "[data-testid='TcfAccept']",
        ]:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    print(f"  Aceptando cookies con: {selector}")
                    btn.click()
                    time.sleep(2)
                    break
            except Exception:
                pass

        time.sleep(3)

        # Guarda el HTML completo
        html = page.content()
        archivo = DATA_DIR / f"debug_{nombre.lower()}.html"
        archivo.write_text(html, encoding="utf-8")
        print(f"  HTML guardado en {archivo} ({len(html):,} chars)")

        # Imprime los primeros tags article/div que encuentre
        print(f"  Buscando contenedores de anuncios...")
        for sel in ["article", "[class*='item']", "[class*='card']", "[class*='Card']", "[class*='listing']"]:
            items = page.query_selector_all(sel)
            if items:
                print(f"    '{sel}': {len(items)} elementos")
                # Muestra las clases del primero
                first_class = items[0].get_attribute("class") or "(sin clase)"
                print(f"      Primero: class='{first_class[:100]}'")

        # Título de la página
        title = page.title()
        print(f"  Título de página: {title}")

    except Exception as e:
        print(f"  ERROR: {e}")

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # visible para reducir detección
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="es-ES",
        timezone_id="Europe/Madrid",
    )
    page = context.new_page()

    diagnosticar(URL_IDEALISTA, "idealista", page)
    diagnosticar(URL_FOTOCASA,  "fotocasa",  page)

    browser.close()

print("\nFicheros generados:")
print("  data/debug_idealista.html")
print("  data/debug_fotocasa.html")
print("\nAbre esos ficheros en el navegador o compártelos para ajustar los selectores.")
