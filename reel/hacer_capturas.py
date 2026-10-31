# -*- coding: utf-8 -*-
"""Capturas del tablero: para el reel y para la publicación de LinkedIn.

Levanta un servidor local sobre la carpeta `web` del tablero, abre cada vista con
Chromium y guarda una imagen a 2x. Si alguna vista deja errores en consola, los avisa.

    python hacer_capturas.py
    python hacer_capturas.py --web ../repositorio/web
"""
import argparse
import asyncio
import contextlib
import functools
import http.server
import os
import socketserver
import threading
from pathlib import Path

AQUI = Path(__file__).parent
VISTAS = [("panorama", "#/panorama"), ("analisis", "#/analisis"),
          ("ficha", "#/ficha/PNMTFE"), ("indicadores", "#/indicadores"),
          ("reportes", "#/reportes/PNMTFE"), ("metodologia", "#/metodologia")]


@contextlib.contextmanager
def servidor(carpeta, puerto=0):
    class Silencioso(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):   # sin registro de accesos en la consola
            pass
    handler = functools.partial(Silencioso, directory=str(carpeta))
    with socketserver.TCPServer(("127.0.0.1", puerto), handler) as s:
        s.allow_reuse_address = True
        threading.Thread(target=s.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{s.server_address[1]}"
        finally:
            s.shutdown()


async def capturar(base, salida, ancho, alto):
    from playwright.async_api import async_playwright
    salida.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        navegador = await pw.chromium.launch()
        pg = await navegador.new_page(viewport={"width": ancho, "height": alto}, device_scale_factor=2)
        errores = []
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errores.append(str(e)))
        for nombre, ruta in VISTAS:
            await pg.goto(f"{base}/index.html{ruta}", wait_until="networkidle")
            await pg.wait_for_timeout(1200)
            await pg.screenshot(path=salida / f"{nombre}.png")
            print(f"  {nombre}.png")
        await navegador.close()
    # las tipografías vienen de Google Fonts: si no hay red, falla solo ese recurso
    reales = [e for e in errores if "fonts.g" not in e and "ERR_TUNNEL" not in e]
    print("errores de consola:", reales or "ninguno")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--web", default=str(AQUI.parent / "web"))
    p.add_argument("--salida", default=str(AQUI / "capturas"))
    p.add_argument("--ancho", type=int, default=1440)
    p.add_argument("--alto", type=int, default=900)
    a = p.parse_args()
    web = Path(a.web)
    if not (web / "index.html").exists():
        raise SystemExit(f"No encuentro el tablero en {web}")
    with servidor(web) as base:
        asyncio.run(capturar(base, Path(a.salida), a.ancho, a.alto))
