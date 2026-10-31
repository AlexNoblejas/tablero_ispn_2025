# -*- coding: utf-8 -*-
"""Genera una imagen 1080x1920 por escena del reel, con los datos reales del tablero.

Cada imagen es el fondo de su escena. La franja util va de Y0 a Y1: arriba queda el
titulo y el aviso de IA, abajo la cifra grande y los subtitulos que dibuja reel.py.
Solo se usan formas y texto sin glifos especiales, porque la fuente variable no
trae flechas ni simbolos.
"""
import json, os, urllib.request
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.environ.get("ISPN_DATOS") or os.path.join(
    os.path.dirname(AQUI), "web", "data")
if not os.path.isdir(DATOS):
    raise SystemExit(f"No encuentro los datos del tablero en {DATOS}.\n"
                     "Corre antes scripts/preparar_datos.py, o indica la carpeta con ISPN_DATOS.")
OUT, FUENTES = os.path.join(AQUI, "imagenes"), os.path.join(AQUI, "fuentes")
os.makedirs(OUT, exist_ok=True); os.makedirs(FUENTES, exist_ok=True)

# Cada imagen es una FRANJA que se pega en el cuadro del reel bajo la cifra grande.
ANCHO, ALTO, MARGEN = 1080, 600, 70
FONDO, TEXTO, SUAVE = "#1C1A17", "#F7F3EC", "#B8AE9F"
PAL10 = ["#B01515","#B03015","#B04A15","#B06515","#B07F15","#B09A15","#ACB015","#91B015","#4BB015","#1DB015"]
VERDE, AMBAR, ROJO = "#1DB015", "#B09A15", "#B04A15"
CAJA = "#2A2723"
Y0, Y1 = 0, 600             # coordenadas dentro de la franja

_cache = {}
def fuente(nombre, tam, peso):
    k = (nombre, tam, peso)
    if k in _cache: return _cache[k]
    ruta = os.path.join(FUENTES, f"{nombre}.ttf")
    if not os.path.exists(ruta):
        urllib.request.urlretrieve(
            f"https://github.com/google/fonts/raw/main/ofl/{nombre.lower()}/{nombre}%5Bwght%5D.ttf", ruta)
    f = ImageFont.truetype(ruta, tam); f.set_variation_by_axes([peso])
    _cache[k] = f
    return f

def lienzo():
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    return img, ImageDraw.Draw(img)

def rotulo(d, texto, y=4):
    bloque(d, texto, fuente("PublicSans", 27, 700), MARGEN, y, ANCHO - 2*MARGEN, SUAVE)
    return y + 40

def col(v):
    return PAL10[max(0, min(9, int(v // 10)))]

def envolver(d, texto, f, ancho):
    lineas, act = [], ""
    for p in texto.split():
        t = f"{act} {p}".strip()
        if d.textlength(t, font=f) <= ancho: act = t
        else: lineas.append(act); act = p
    return lineas + [act]

def bloque(d, texto, f, x, y, ancho, fill, interlinea=1.28):
    for i, l in enumerate(envolver(d, texto, f, ancho)):
        d.text((x, y + i * f.size * interlinea), l, font=f, fill=fill)
    return y + len(envolver(d, texto, f, ancho)) * f.size * interlinea

def flecha(d, x, y, largo, color, grosor=3):
    d.line((x, y, x + largo, y), fill=color, width=grosor)
    d.polygon([(x + largo, y - 7), (x + largo + 13, y), (x + largo, y + 7)], fill=color)

def tache(d, x, y, lado, color, grosor=5):
    m = lado * 0.3
    d.line((x + m, y + m, x + lado - m, y + lado - m), fill=color, width=grosor)
    d.line((x + lado - m, y + m, x + m, y + lado - m), fill=color, width=grosor)

P  = json.load(open(f"{DATOS}/politicas.json", encoding="utf-8"))
CR = json.load(open(f"{DATOS}/criterios.json", encoding="utf-8"))
R  = json.load(open(f"{DATOS}/resumen.json", encoding="utf-8"))

# ------------------------------------------------------------------ escena 1
def e1():
    """Las 42 politicas sobre la escala del indice; la franja alta queda vacia."""
    img, d = lienzo()
    y = rotulo(d, "CADA PUNTO ES UNA POLÍTICA NACIONAL")
    x0, x1, base = MARGEN, ANCHO - MARGEN, Y1 - 108
    X = lambda v: x0 + (x1 - x0) * v / 100
    for a, b, c, nom in [(0,40,ROJO,"baja"), (40,60,AMBAR,"media"), (60,80,"#91B015","media-alta"), (80,100,VERDE,"alta")]:
        d.rectangle((X(a), base + 16, X(b) - 5, base + 23), fill=c)
        d.text((X(a), base + 40), nom.upper(), font=fuente("PublicSans", 27, 700), fill=c)
        if a: d.line((X(a), y + 36, X(a), base + 10), fill="#2E2A26")
    pila = {}
    for p in sorted(P, key=lambda p: p["ispn"]):
        k = p["ispn"]; i = pila[k] = pila.get(k, 0) + 1
        cy = base - 15 - (i - 1) * 27
        d.ellipse((X(k)-12, cy-12, X(k)+12, cy+12), fill=col(k), outline=FONDO, width=3)
    for v in (0, 20, 40, 60, 80, 100):
        d.text((X(v), base + 86), str(v), font=fuente("PublicSans", 28, 500), fill=SUAVE, anchor="mm")
    d.text((X(90), y + 86), "VACÍA", font=fuente("Oswald", 58, 600), fill=VERDE, anchor="mm")
    d.line((X(83), y + 122, X(97), y + 122), fill=VERDE, width=4)
    return img

# ------------------------------------------------------------------ escena 2
def e2():
    """Perfil de los seis criterios: promedio sobre su maximo."""
    img, d = lienzo()
    x0, x1 = MARGEN, ANCHO - MARGEN - 150
    fn, fv = fuente("PublicSans", 28, 600), fuente("Oswald", 38, 600)
    fil = (Y1 - 24) // len(CR)
    for i, c in enumerate(CR):
        y = 12 + i * fil
        pct = 100 * (c["promedio"] - 1) / (c["maximo"] - 1)
        d.text((x0, y), c["nombre"].upper(), font=fn, fill=SUAVE)
        yb = y + 36
        d.rounded_rectangle((x0, yb, x1, yb + 26), radius=13, fill=CAJA)
        d.rounded_rectangle((x0, yb, x0 + max(26, (x1-x0) * pct / 100), yb + 26), radius=13, fill=col(pct))
        d.text((x1 + 22, yb + 13), f"{c['promedio']:.1f} / {c['maximo']}",
               font=fv, fill=TEXTO, anchor="lm")
    return img

# ------------------------------------------------------------------ escena 3
def e3():
    """40 de 42: una cuadricula de politicas segun el criterio del problema publico."""
    img, d = lienzo()
    y = rotulo(d, "CADA CUADRO ES UNA POLÍTICA NACIONAL")
    cols, lado, gap = 7, 62, 11
    ancho = cols * lado + (cols - 1) * gap
    x0, y0 = (ANCHO - ancho) // 2, y + 10
    for i, p in enumerate(sorted(P, key=lambda p: -p["criterios"][0])):
        f_, c_ = divmod(i, cols)
        x, y = x0 + c_ * (lado + gap), y0 + f_ * (lado + gap)
        acredita = p["criterios"][0] >= 3
        d.rounded_rectangle((x, y, x + lado, y + lado), radius=14,
                            fill="#15300F" if acredita else "#30201A",
                            outline=VERDE if acredita else ROJO, width=3)
        if acredita:
            d.line((x+20, y+lado*0.55, x+lado*0.44, y+lado-21), fill=VERDE, width=6)
            d.line((x+lado*0.44, y+lado-21, x+lado-18, y+20), fill=VERDE, width=6)
        else:
            tache(d, x, y, lado, ROJO, 4)
    yl = y0 + 6 * (lado + gap) + 14
    tache(d, x0, yl, 34, ROJO, 3)
    d.text((x0 + 48, yl + 17), "el problema público no mejora o no se puede acreditar",
           font=fuente("PublicSans", 26, 500), fill=SUAVE, anchor="lm")
    return img

# ------------------------------------------------------------------ escena 4
def e4():
    """Servicios en marcha frente a indicadores de servicio que mejoran."""
    img, d = lienzo()
    y = rotulo(d, "CADA PUNTO ES UNA POLÍTICA NACIONAL")
    x0, x1 = MARGEN + 46, ANCHO - MARGEN
    yt, yb = y + 62, Y1 - 62
    X = lambda v: x0 + (x1 - x0) * v / 100
    Y = lambda v: yb - (yb - yt) * v / 100
    d.rectangle((X(75), Y(100), X(100), Y(50)), fill="#1B2A16")
    d.rectangle((X(75), Y(50), X(100), Y(0)), fill="#2E1D15")
    for t in (0, 25, 50, 75, 100):
        d.line((X(t), Y(0), X(t), Y(100)), fill="#2E2A26")
        d.line((X(0), Y(t), X(100), Y(t)), fill="#2E2A26")
    d.line((X(75), Y(0), X(75), Y(100)), fill=SUAVE, width=2)
    d.line((X(0), Y(50), X(100), Y(50)), fill=SUAVE, width=2)
    arriba = abajo = 0
    for p in P:
        if p["c3"]["pct"] is None or p["c4"]["pct"] is None: continue
        if p["c3"]["pct"] >= 75:
            arriba += p["c4"]["pct"] >= 50
            abajo  += p["c4"]["pct"] <  50
        cx, cy = X(p["c3"]["pct"]), Y(p["c4"]["pct"])
        d.ellipse((cx-11, cy-11, cx+11, cy+11), fill=col(p["ispn"]), outline=FONDO, width=3)
    fe, fn = fuente("PublicSans", 24, 700), fuente("Oswald", 40, 600)
    def marca(texto, n, color, ybase):
        xr = X(100) - 12
        d.text((xr, ybase), texto, font=fe, fill=color, anchor="rs")
        d.text((xr - d.textlength(texto, font=fe) - 12, ybase + 3), str(n), font=fn, fill=color, anchor="rs")
    marca("CON 50% O MÁS FAVORABLES", arriba, VERDE, Y(100) - 10)
    marca("CON MENOS DEL 50% FAVORABLES", abajo, ROJO, Y(0) - 16)
    f = fuente("PublicSans", 26, 700)
    d.text((x0, yb + 24), "SERVICIOS IMPLEMENTADOS", font=f, fill=SUAVE)
    flecha(d, x0 + d.textlength("SERVICIOS IMPLEMENTADOS", font=f) + 14, yb + 37, 38, SUAVE)
    # eje vertical, rotado, para que se entienda que arriba es mejor
    etq = Image.new("RGBA", (int(d.textlength("INDICADORES FAVORABLES", font=f)) + 8, 34), (0, 0, 0, 0))
    ImageDraw.Draw(etq).text((0, 0), "INDICADORES FAVORABLES", font=f, fill=SUAVE)
    etq = etq.rotate(90, expand=True)
    img.paste(etq, (MARGEN - 10, int(Y(100))), etq)
    return img

# ------------------------------------------------------------------ escena 5
def e5():
    """Criterio 6: que tan especificas son las alternativas de mejora que propone cada entidad."""
    img, d = lienzo()
    y = rotulo(d, "CRITERIO 6 · ALTERNATIVAS PARA MEJORAR LA IMPLEMENTACIÓN")
    c6 = next(c for c in CR if c["c"] == "C6")
    niveles = [
        (3, c6["dist"][2], VERDE,
         "Específicas y viables: se identifica quién hace qué"),
        (2, c6["dist"][1], AMBAR,
         "De carácter general, sin precisar acciones ni mecanismos"),
        (1, c6["dist"][0], ROJO,
         "Sin alternativas, solo ajustes de diseño, o medidas repetidas sin informar avances"),
    ]
    tot = sum(n for _, n, _, _ in niveles)
    x0 = MARGEN + 150
    ancho = ANCHO - MARGEN - x0 - 60
    fil = (Y1 - y - 30) // 3
    fn, fe = fuente("Oswald", 62, 600), fuente("PublicSans", 25, 600)
    for i, (niv, n, c, txt) in enumerate(niveles):
        yy = y + 14 + i * fil
        d.text((MARGEN, yy + 10), f"NIVEL {niv}", font=fuente("PublicSans", 24, 700), fill=SUAVE)
        d.text((MARGEN, yy + 40), str(n), font=fn, fill=c)
        barra = max(14, ancho * n / tot)
        d.rounded_rectangle((x0, yy + 16, x0 + barra, yy + 60), radius=10, fill=c)
        bloque(d, txt, fe, x0, yy + 74, ancho + 40, TEXTO if niv == 3 else SUAVE)
    return img

# ------------------------------------------------------------------ escena 6
def e6():
    """Cierre: el tablero mismo, en una ventana de navegador."""
    cap = os.path.join(AQUI, "capturas", "panorama.png")
    if not os.path.exists(cap):
        raise SystemExit("Falta capturas/panorama.png: corre antes hacer_capturas.py")
    img, d = lienzo()
    barra = 34
    foto = Image.open(cap).convert("RGB")
    # recorte del encabezado y la escala, en la proporción del hueco
    alto_util = ALTO - barra
    rec_h = int(foto.width * alto_util / ANCHO)
    foto = foto.crop((0, int(foto.height * 0.12), foto.width, int(foto.height * 0.12) + rec_h))
    foto = foto.resize((ANCHO, alto_util), Image.LANCZOS)
    img.paste(foto, (0, barra))
    d.rectangle((0, 0, ANCHO, barra), fill="#2A2723")
    for i, c in enumerate(("#B04A15", "#B09A15", "#1DB015")):
        d.ellipse((22 + i*26, barra/2 - 6, 34 + i*26, barra/2 + 6), fill=c)
    d.rounded_rectangle((116, 7, ANCHO - 22, barra - 7), radius=9, fill="#1C1A17")
    d.text((134, barra/2), "ispn 2025 · situación de las políticas nacionales del Perú",
           font=fuente("PublicSans", 19, 500), fill=SUAVE, anchor="lm")
    return img


def e6_mosaico():
    """Alternativa: las 42 politicas como mosaico, ordenadas por puntaje."""
    img, d = lienzo()
    y0 = rotulo(d, "LAS 42 POLÍTICAS, DE MAYOR A MENOR PUNTAJE") + 8
    cols, gx, gy = 7, 12, 9
    w = (ANCHO - 2*MARGEN - (cols-1)*gx) // cols
    h = (Y1 - y0 - 10 - 5*gy) // 6
    fv, fs = fuente("Oswald", 30, 600), fuente("PublicSans", 15, 600)
    for i, p in enumerate(sorted(P, key=lambda p: -p["ispn"])):
        f_, c_ = divmod(i, cols)
        x, y = MARGEN + c_*(w+gx), y0 + f_*(h+gy)
        d.rounded_rectangle((x, y, x+w, y+h), radius=12, fill=col(p["ispn"]))
        d.text((x+w/2, y+h/2 - 11), f"{p['ispn']:.1f}", font=fv, fill="#FFFFFF", anchor="mm")
        sigla = p["etiqueta"]
        while d.textlength(sigla, font=fs) > w - 10 and len(sigla) > 3:
            sigla = sigla[:-1]
        d.text((x+w/2, y+h/2 + 18), sigla, font=fs, fill="#FFFFFFCC", anchor="mm")
    return img

if __name__ == "__main__":
    for nombre, fn in [("e1_escala", e1), ("e2_criterios", e2), ("e3_problema", e3),
                       ("e4_cuadrante", e4), ("e5_alternativas", e5), ("e6_tablero", e6), ("e6b_mosaico", e6_mosaico)]:
        ruta = os.path.join(OUT, nombre + ".png")
        fn().save(ruta)
        print(f"  {nombre}.png  {os.path.getsize(ruta)/1024:.0f} KB")
