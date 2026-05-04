"""
reporter.py — Genera el informe HTML diario de oportunidades de captación.
Muestra todos los resultados (sin límite) y explica el scoring.
"""

import os
from datetime import datetime
from pathlib import Path

from config import SCORING, NOTIFICACIONES

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def score_color(score):
    if score >= 75: return "#1a7a4a"
    elif score >= 50: return "#b45309"
    else: return "#6b7280"

def score_bg(score):
    if score >= 75: return "#d1fae5"
    elif score >= 50: return "#fef3c7"
    else: return "#f3f4f6"

def formatear_precio(valor):
    try:
        return f"{int(float(valor)):,}€".replace(",", ".")
    except (TypeError, ValueError):
        return "—"

def badge_fuente(fuente):
    colores = {
        "idealista": ("#003d6b", "#e6f0f8"),
        "fotocasa":  ("#8b0000", "#fce8e8"),
    }
    fg, bg = colores.get((fuente or "").lower(), ("#374151", "#f3f4f6"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{(fuente or "").upper()}</span>'

def badge_vendedor(tipo):
    if tipo == "particular":
        return '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:12px;font-size:11px;">Particular ★</span>'
    elif tipo == "agencia":
        return '<span style="background:#e5e7eb;color:#374151;padding:2px 8px;border-radius:12px;font-size:11px;">Agencia</span>'
    return '<span style="background:#e5e7eb;color:#6b7280;padding:2px 8px;border-radius:12px;font-size:11px;">Desconocido</span>'


def generar_html(oportunidades):
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    fecha_archivo = datetime.now().strftime("%Y-%m-%d")
    n = len(oportunidades)

    filas = ""
    for i, o in enumerate(oportunidades, 1):
        score = int(o.get("score_total", 0))
        precio_str    = formatear_precio(o.get("precio"))
        precio_m2_str = formatear_precio(o.get("precio_m2"))
        precio_medio  = formatear_precio(o.get("precio_medio_zona"))
        titulo  = o.get("titulo", "Sin título")[:80]
        zona    = o.get("zona", "—")
        m2      = o.get("m2", "—")
        habs    = o.get("habitaciones", "—")
        dias    = o.get("dias_mercado", 0)
        ant     = o.get("antiguedad", "") or f"{dias}d"
        bajada  = "✓" if str(o.get("bajada_precio", "")).lower() in ("true", "1") else "—"
        url     = o.get("url", "#")
        fuente  = o.get("fuente", "")
        s_p     = o.get("score_precio", "—")
        s_u     = o.get("score_urgencia", "—")
        s_v     = o.get("score_vendedor", "—")

        # Descuento vs zona
        descuento = ""
        try:
            pm2 = float(o.get("precio_m2") or 0)
            pmed = float(o.get("precio_medio_zona") or 0)
            if pm2 and pmed:
                pct = (pmed - pm2) / pmed * 100
                color_desc = "#1a7a4a" if pct > 0 else "#dc2626"
                descuento = f'<br><span style="font-size:11px;color:{color_desc};font-weight:600;">{pct:+.1f}% vs zona</span>'
        except Exception:
            pass

        filas += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:12px 8px;font-weight:600;color:#374151;">{i}</td>
          <td style="padding:12px 8px;">
            <span style="background:{score_bg(score)};color:{score_color(score)};
                         font-size:20px;font-weight:700;padding:4px 10px;border-radius:8px;">{score}</span>
          </td>
          <td style="padding:12px 8px;">
            <a href="{url}" target="_blank" style="color:#1d4ed8;text-decoration:none;font-size:13px;font-weight:500;">{titulo}</a><br>
            <span style="font-size:11px;color:#6b7280;">{zona}</span>
          </td>
          <td style="padding:12px 8px;">{badge_fuente(fuente)}</td>
          <td style="padding:12px 8px;font-weight:600;">{precio_str}</td>
          <td style="padding:12px 8px;">{precio_m2_str}/m²{descuento}</td>
          <td style="padding:12px 8px;color:#6b7280;font-size:12px;">{precio_medio}/m²</td>
          <td style="padding:12px 8px;">{m2} m²</td>
          <td style="padding:12px 8px;">{habs}</td>
          <td style="padding:12px 8px;font-size:12px;color:#6b7280;">{ant}</td>
          <td style="padding:12px 8px;">{bajada}</td>
          <td style="padding:12px 8px;">{badge_vendedor(o.get("tipo_vendedor",""))}</td>
          <td style="padding:12px 8px;font-size:11px;color:#6b7280;">P:{s_p} U:{s_u} V:{s_v}</td>
        </tr>"""

    if not filas:
        filas = f'<tr><td colspan="13" style="padding:24px;text-align:center;color:#6b7280;">Sin oportunidades con score ≥ {SCORING["score_minimo"]}</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Captación — {fecha_archivo}</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:24px;background:#f9fafb;color:#111827; }}
  h1 {{ font-size:22px;font-weight:700;margin:0 0 4px; }}
  h2 {{ font-size:16px;font-weight:700;margin:0 0 12px; }}
  .meta {{ font-size:13px;color:#6b7280;margin-bottom:20px; }}
  .stat {{ display:inline-block;background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px 20px;margin-right:12px;margin-bottom:20px; }}
  .stat-n {{ font-size:28px;font-weight:700;color:#1d4ed8; }}
  .stat-label {{ font-size:12px;color:#6b7280; }}
  table {{ width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  th {{ background:#f3f4f6;padding:10px 8px;text-align:left;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap; }}
  tr:hover {{ background:#f9fafb; }}
  code {{ background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:12px; }}
  .leyenda {{ margin-top:12px;font-size:12px;color:#6b7280; }}
  .leyenda span {{ margin-right:16px; }}
  .scoring-box {{ background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:24px;margin-top:32px; }}
  .scoring-table td, .scoring-table th {{ padding:10px 12px;font-size:13px; }}
  .scoring-table th {{ background:#f3f4f6;font-weight:600;color:#374151; }}
  .scoring-table tr {{ border-top:1px solid #e5e7eb; }}
  .tip {{ margin-top:16px;padding:12px 16px;background:#f0fdf4;border-radius:8px;font-size:12px;color:#166534; }}
</style>
</head>
<body>

<h1>Informe de captación</h1>
<div class="meta">Generado el {fecha} · Score mínimo: {SCORING["score_minimo"]}</div>

<div>
  <div class="stat"><div class="stat-n">{n}</div><div class="stat-label">Anuncios encontrados</div></div>
</div>

<table>
  <thead>
    <tr>
      <th>#</th><th>Score</th><th>Anuncio</th><th>Fuente</th>
      <th>Precio</th><th>€/m²</th><th>Media zona</th>
      <th>m²</th><th>Hab.</th><th>Publicado</th><th>Bajada</th>
      <th>Vendedor</th><th>P / U / V</th>
    </tr>
  </thead>
  <tbody>{filas}</tbody>
</table>

<div class="leyenda">
  <span><b style="color:#1a7a4a">■</b> ≥75 Alta prioridad</span>
  <span><b style="color:#b45309">■</b> ≥50 Media</span>
  <span><b style="color:#6b7280">■</b> &lt;50 Baja</span>
  <span>· P=Precio U=Urgencia V=Vendedor</span>
</div>

<div class="scoring-box">
  <h2>¿Cómo se calcula el score?</h2>
  <p style="font-size:13px;color:#374151;margin:0 0 16px;">
    El score (0–100) combina tres criterios ponderados. Puedes ajustar los pesos y umbrales en <code>config.py</code>.
  </p>
  <table class="scoring-table" style="width:100%;border-collapse:collapse;">
    <thead>
      <tr>
        <th style="text-align:left;">Criterio</th>
        <th style="text-align:center;">Peso actual</th>
        <th style="text-align:left;">Qué mide</th>
        <th style="text-align:left;">Cuándo puntúa alto</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>P — Precio</strong></td>
        <td style="text-align:center;">{SCORING["peso_precio"]}%</td>
        <td style="color:#6b7280;">€/m² del anuncio vs precio medio de la zona</td>
        <td style="color:#6b7280;">Un {SCORING["descuento_max"]}% o más barato que la zona → 100 pts. Al precio de zona → 0 pts.</td>
      </tr>
      <tr>
        <td><strong>U — Urgencia</strong></td>
        <td style="text-align:center;">{SCORING["peso_urgencia"]}%</td>
        <td style="color:#6b7280;">Señales de que el vendedor tiene prisa o presión</td>
        <td style="color:#6b7280;">Bajada de precio detectada (+50 pts) + más de {SCORING["dias_urgencia"]} días publicado (+50 pts).</td>
      </tr>
      <tr>
        <td><strong>V — Vendedor</strong></td>
        <td style="text-align:center;">{SCORING["peso_vendedor"]}%</td>
        <td style="color:#6b7280;">Tipo de anunciante</td>
        <td style="color:#6b7280;">Particular (100 pts) → más fácil de captar. Agencia (20 pts) → ya tiene representación.</td>
      </tr>
    </tbody>
  </table>
  <div class="tip">
    <strong>💡 Cómo mejorar la precisión del scoring</strong><br><br>
    <strong>1. Actualiza el precio medio de zona</strong> en <code>config.py → precio_medio_m2</code> cada 2–3 meses con datos reales de cierre (no de oferta). Es el factor que más impacta en la utilidad del score de Precio.<br><br>
    <strong>2. Ajusta los pesos</strong> según tu estrategia. Si prefieres priorizar propiedades con señales de urgencia sobre precio, sube <code>peso_urgencia</code> y baja <code>peso_precio</code>.<br><br>
    <strong>3. Ajusta el umbral de días</strong> (<code>dias_urgencia</code>). En mercados de lujo como Monteclaro, 60 días puede ser corto — muchas propiedades tardan 6–12 meses. Prueba a subirlo a 120 o 180 días.<br><br>
    <strong>4. Baja el score mínimo</strong> (<code>score_minimo</code>) si quieres ver más resultados aunque sean de menor prioridad.
  </div>
</div>

</body>
</html>"""

    archivo = DATA_DIR / f"informe_{fecha_archivo}.html"
    archivo.write_text(html, encoding="utf-8")
    print(f"\n  Informe generado: {archivo.resolve()}")
    return archivo


def enviar_whatsapp(oportunidades):
    if not NOTIFICACIONES["habilitado"] or not oportunidades:
        return

    import urllib.parse, urllib.request, platform

    top3 = oportunidades[:3]
    lineas = [f"🏠 Captación {datetime.now().strftime('%d/%m')} — Top {len(top3)}:"]
    for i, o in enumerate(top3, 1):
        score = o.get("score_total", 0)
        precio = formatear_precio(o.get("precio"))
        titulo = (o.get("titulo") or "")[:40]
        lineas.append(f"{i}. [{score}pts] {titulo} — {precio}")
        lineas.append(f"   {o.get('url','')}")
    mensaje = "\n".join(lineas)

    destinatarios = NOTIFICACIONES.get("destinatarios", [])
    for d in destinatarios:
        numero = d.get("numero", "")
        apikey = d.get("apikey", "")
        if not numero or not apikey:
            continue
        try:
            params = urllib.parse.urlencode({
                "phone":  numero,
                "text":   mensaje,
                "apikey": apikey,
            })
            urllib.request.urlopen(
                f"https://api.callmebot.com/whatsapp.php?{params}",
                timeout=10
            )
            print(f"  WhatsApp enviado a {numero}")
        except Exception as e:
            print(f"  [!] Error WhatsApp {numero}: {e}")


def run(oportunidades):
    print(f"\n{'='*60}")
    print(f"  GENERANDO INFORME")
    print(f"{'='*60}")
    archivo = generar_html(oportunidades)
    enviar_whatsapp(oportunidades)

    # Solo abre el navegador si estamos en Mac (no en Railway/Linux servidor)
    import platform
    if platform.system() == "Darwin":
        import os
        os.system(f'open "{archivo.resolve()}"')

    return archivo


if __name__ == "__main__":
    import csv
    archivo_scored = DATA_DIR / "anuncios_scored.csv"
    if archivo_scored.exists():
        with open(archivo_scored, newline="", encoding="utf-8") as f:
            datos = list(csv.DictReader(f))
        datos.sort(key=lambda x: int(x.get("score_total", 0)), reverse=True)
        oportunidades = [d for d in datos if int(d.get("score_total", 0)) >= SCORING["score_minimo"]]
        run(oportunidades)
    else:
        print("No hay datos. Ejecuta primero: python main.py")
