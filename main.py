"""
main.py — Punto de entrada. Ejecuta el ciclo completo:
  scraper → scorer → reporter

Uso:
  python main.py              # ciclo completo
  python main.py --solo-score # recalcula scores sin scrapear (útil para ajustar pesos)
  python main.py --solo-informe # regenera informe HTML sin scrapear ni puntuar
"""

import sys

import scraper
import scorer
import reporter


def main():
    args = sys.argv[1:]

    if "--solo-informe" in args:
        import csv
        from pathlib import Path
        from config import SCORING
        archivo = Path("data/anuncios_scored.csv")
        if not archivo.exists():
            print("No hay datos puntuados. Ejecuta sin argumentos primero.")
            sys.exit(1)
        with open(archivo, newline="", encoding="utf-8") as f:
            datos = list(csv.DictReader(f))
        datos.sort(key=lambda x: int(x.get("score_total", 0)), reverse=True)
        oportunidades = [d for d in datos if int(d.get("score_total", 0)) >= SCORING["score_minimo"]]
        reporter.run(oportunidades)
        return

    if "--solo-score" in args:
        oportunidades = scorer.run()
        reporter.run(oportunidades)
        return

    # Ciclo completo
    anuncios_nuevos = scraper.run()
    oportunidades   = scorer.run(anuncios_nuevos)
    reporter.run(oportunidades)


if __name__ == "__main__":
    main()
