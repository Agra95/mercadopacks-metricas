#!/usr/bin/env python3
"""
descargar_lightdata.py
-----------------------
Inicia sesión en LightData, filtra el listado de envíos por la fecha de
"ayer" (Desde = Hasta = ayer) SIN filtro de Estado — se necesitan todos los
estados (entregado, cancelado, reprogramado, etc.), no solo uno — y descarga
el .xls resultante a datos_crudos/.

Uso:
    LIGHTDATA_USER=... LIGHTDATA_PASS=... python3 descargar_lightdata.py

Pensado para correr sin supervisión (GitHub Actions), por eso:
- Corre el navegador en modo headless.
- Si algo falla, guarda una captura de pantalla para poder diagnosticar sin
  tener que reproducirlo a mano.
- Calcula "ayer" en UTC a propósito: el workflow corre a las 03:00 UTC
  (00:00 hora Argentina), momento en el que la fecha UTC ya coincide con la
  fecha del día que acaba de arrancar en Argentina.

Los selectores de este script salieron de grabar la navegación real con
`playwright codegen https://mercadopacks.lightdata.app/`. Si LightData
cambia el diseño de la página y el script empieza a fallar, la forma más
rápida de arreglarlo es volver a grabar con esa misma herramienta y
actualizar los selectores de abajo (ver README de la carpeta scripts/).
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

LIGHTDATA_URL = "https://mercadopacks.lightdata.app/"
CARPETA_SALIDA = Path(__file__).resolve().parent.parent / "datos_crudos"
TIMEOUT_MS = 20_000


def seleccionar_dia(page, dia: int):
    """
    Clickea el botón del día indicado en el calendario que está abierto.

    Nota / limitación conocida: si "ayer" cae en el mes anterior (es decir,
    hoy es el día 1 del mes), el calendario podría no mostrar ese día sin
    antes navegar al mes anterior. Esto no se probó todavía porque no
    ocurrió durante la grabación del flujo — si el script falla el primer
    día de cada mes, revisar este paso primero (agregar un click al botón
    de "mes anterior" del picker antes de buscar el día).
    """
    page.get_by_role("button", name=str(dia), exact=True).click()


def descargar(usuario: str, clave: str) -> Path:
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    dia_ayer = ayer.day

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(TIMEOUT_MS)

        try:
            page.goto(LIGHTDATA_URL)

            page.get_by_role("textbox", name="Username").fill(usuario)
            page.get_by_role("textbox", name="Password").fill(clave)
            page.get_by_text("Ingresar").click()

            page.get_by_role("link", name="local_shipping Envios").click()
            page.get_by_role("link", name="menu Envios").click()

            page.get_by_role("textbox", name="Fecha desde/hasta").click()
            seleccionar_dia(page, dia_ayer)
            page.get_by_role("button", name="Ok").click()

            page.get_by_role("textbox", name="Hasta", exact=True).click()
            seleccionar_dia(page, dia_ayer)
            page.get_by_role("button", name="Ok").click()

            # Cierra un chip/tooltip que queda abierto tras elegir las
            # fechas — parte del flujo grabado; sin este click el botón de
            # buscar de abajo queda tapado y no se puede clickear.
            page.get_by_text("×").first.click()

            # Botón "Buscar/Filtrar": no tiene texto visible en la página,
            # por eso el selector es estructural (más frágil ante cambios
            # de diseño que uno por texto o rol).
            page.locator(".row > div:nth-child(3) > .row > div > .btn").first.click()

            with page.expect_download() as download_info:
                with page.expect_popup() as popup_info:
                    # Botón de exportar — mismo caso, sin texto visible.
                    page.locator("div:nth-child(3) > .row > div:nth-child(2) > .btn").click()
                popup = popup_info.value
            download = download_info.value
            popup.close()

        except PlaywrightTimeoutError as e:
            captura = Path(__file__).resolve().parent / "error_descarga.png"
            page.screenshot(path=str(captura))
            context.close()
            browser.close()
            raise RuntimeError(
                f"Timeout esperando un elemento de LightData. Se guardó una "
                f"captura de pantalla en {captura} para diagnosticar. "
                f"Error original: {e}"
            )

        nombre = "listado_envios_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + ".xls"
        destino = CARPETA_SALIDA / nombre
        download.save_as(str(destino))

        context.close()
        browser.close()

    return destino


def main():
    usuario = os.environ.get("LIGHTDATA_USER")
    clave = os.environ.get("LIGHTDATA_PASS")
    if not usuario or not clave:
        sys.exit("Faltan las variables de entorno LIGHTDATA_USER / LIGHTDATA_PASS.")

    destino = descargar(usuario, clave)
    print(f"Archivo descargado: {destino}")


if __name__ == "__main__":
    main()
