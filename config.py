# =============================================================================
# CONFIGURACIÓN DEL SISTEMA DE CAPTACIÓN
# Las credenciales sensibles se leen desde variables de entorno de Railway.
# El resto (zonas, scoring) se edita directamente aquí.
# =============================================================================

import os

# ---------------------------------------------------------------------------
# ZONAS A MONITORIZAR
# ---------------------------------------------------------------------------

ZONAS = [
    {
        "nombre": "Monteclaro - Pozuelo",
        "idealista_url": "https://www.idealista.com/venta-viviendas/pozuelo-de-alarcon/urbanizaciones/monteclaro/",
        "fotocasa_url": "https://www.fotocasa.es/es/comprar/viviendas/pozuelo-de-alarcon/monteclaro/l",
        "precio_medio_m2": 5200,
    },
    # Para añadir zona nueva, copia este bloque:
    # {
    #     "nombre": "Aravaca - Madrid",
    #     "idealista_url": "https://www.idealista.com/venta-viviendas/madrid/aravaca/",
    #     "fotocasa_url": "https://www.fotocasa.es/es/comprar/viviendas/madrid/aravaca/l",
    #     "precio_medio_m2": 5800,
    # },
]

# ---------------------------------------------------------------------------
# PARÁMETROS DE SCORING
# ---------------------------------------------------------------------------

SCORING = {
    "peso_precio":    50,
    "peso_urgencia":  30,
    "peso_vendedor":  20,
    "descuento_max":  20,
    "descuento_min":   0,
    "dias_urgencia":  60,
    "score_minimo":    0,
}

# ---------------------------------------------------------------------------
# NOTIFICACIONES WhatsApp (CallMeBot)
# API keys configuradas como variables de entorno en Railway:
#   CALLMEBOT_NUMERO_1, CALLMEBOT_APIKEY_1
#   CALLMEBOT_NUMERO_2, CALLMEBOT_APIKEY_2
# ---------------------------------------------------------------------------

NOTIFICACIONES = {
    "habilitado": True,
    "tipo": "callmebot",
    "destinatarios": [
        {
            "numero":  os.getenv("CALLMEBOT_NUMERO_1", ""),
            "apikey":  os.getenv("CALLMEBOT_APIKEY_1", ""),
        },
        {
            "numero":  os.getenv("CALLMEBOT_NUMERO_2", ""),
            "apikey":  os.getenv("CALLMEBOT_APIKEY_2", ""),
        },
    ]
}

# ---------------------------------------------------------------------------
# CORREO ELECTRÓNICO
# Credenciales configuradas como variables de entorno en Railway:
#   EMAIL_SMTP_HOST   → servidor SMTP  (p.ej. smtp.gmail.com)
#   EMAIL_SMTP_PORT   → puerto         (587 para TLS, 465 para SSL)
#   EMAIL_USER        → cuenta de envío (p.ej. tucuenta@gmail.com)
#   EMAIL_PASSWORD    → contraseña o App Password de Gmail
#
# Para Gmail: activa "Verificación en dos pasos" y genera una
# "Contraseña de aplicación" en myaccount.google.com/apppasswords
# ---------------------------------------------------------------------------

EMAIL = {
    "habilitado":   True,
    "smtp_host":    os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
    "smtp_port":    int(os.getenv("EMAIL_SMTP_PORT", "587")),
    "usuario":      os.getenv("EMAIL_USER", ""),
    "password":     os.getenv("EMAIL_PASSWORD", ""),
    "remitente":    os.getenv("EMAIL_USER", ""),   # mismo que usuario por defecto
    "destinatarios": [
        "guille7287@gmail.com",
        "javierfalferez@gmail.com",
    ],
}

# ---------------------------------------------------------------------------
# ZENROWS — API key como variable de entorno en Railway: ZENROWS_API_KEY
# ---------------------------------------------------------------------------

ZENROWS = {
    "habilitado":    True,
    "api_key":       os.getenv("ZENROWS_API_KEY", ""),
    "js_render":     True,
    "premium_proxy": True,
    "antibot":       True,
}

# ---------------------------------------------------------------------------
# GOOGLE SHEETS (opcional)
# ---------------------------------------------------------------------------

GOOGLE_SHEETS = {
    "habilitado": False,
    "spreadsheet_id": None,
    "credentials_file": "credentials.json",
    "hoja_nombre": "Captación",
}

# ---------------------------------------------------------------------------
# COMPORTAMIENTO DEL SCRAPER
# ---------------------------------------------------------------------------

SCRAPER = {
    "delay_min":  3,
    "delay_max":  7,
    "max_paginas": 3,
    "timeout":    60,
}
