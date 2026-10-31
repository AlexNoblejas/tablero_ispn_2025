# -*- coding: utf-8 -*-
"""Extiende el reel de la sesión 15 con lo que pide la Tarea 3.

Sobre el flujo original (guion -> voz clonada -> Whisper -> video) añade:

  - una imagen por escena (gráfico, mapa o captura) en la mitad inferior del cuadro,
  - música de fondo por debajo de la narración, con desvanecido al final,
  - el crédito de la música junto al de la fuente de datos.

Se mantiene todo lo demás de la clase: formato 9:16, aviso de voz generada con IA,
subtítulos palabra por palabra, barra de avance y archivo .srt.

Uso:
    python hacer_reel_visual.py --voz mi_voz.m4a --autor "Nombre Apellido" \
        --fuente "CEPLAN, Informe Anual de Políticas Nacionales 2025" \
        --musica musica/fondo.mp3 --credito-musica "Título — Autor (CC0)"
"""
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import reel
from reel import (ANCHO, ALTO, FPS, MARGEN, FONDO, TEXTO, SUAVE, ACENTO, CAJA,
                  _fuente, _envolver, _ajustar, _bloques, FFMPEG)

AQUI = Path(__file__).parent

# El cuadro se parte en dos: arriba la cifra y su etiqueta, abajo la imagen de la escena.
CIFRA_Y0, CIFRA_Y1 = 400, 622
IMG_Y, IMG_ALTO = 660, 600


def _cabecera(e):
    """Capa con la cifra grande y su etiqueta, centradas en la franja superior."""
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    ancho = ANCHO - 2 * MARGEN

    def alto(texto, f):
        return -d.textbbox((0, 0), texto, font=f, anchor="ls")[1]

    lineas = []
    if e.get("cifra"):
        f = _ajustar(d, e["cifra"], "Oswald", 700, ancho, 170, minimo=90)
        lineas.append((e["cifra"], f, TEXTO, alto(e["cifra"], f), 26))
        fe, color = _fuente("PublicSans", 44, 600), SUAVE
    else:
        fe, color = _fuente("Oswald", 86, 600), TEXTO
    lineas += [(x, fe, color, alto("H", fe), int(fe.size * 0.38))
               for x in _envolver(d, e["etiqueta"], fe, ancho)]

    y = (CIFRA_Y0 + CIFRA_Y1 - sum(h + g for *_, h, g in lineas) + lineas[-1][4]) / 2
    for texto, f, color, h, g in lineas:
        y += h
        d.text((MARGEN, y), texto, font=f, fill=color, anchor="ls")
        y += g
    return capa


def _imagenes(guion, carpeta):
    """Carga la imagen de cada escena, ya escalada a su hueco; None si la escena no tiene."""
    carpeta = Path(carpeta)
    out = []
    for e in guion["escenas"]:
        nombre = e.get("imagen")
        if not nombre:
            out.append(None); continue
        ruta = carpeta / nombre
        if not ruta.exists():
            raise SystemExit(f"Falta la imagen de una escena: {ruta}")
        img = Image.open(ruta).convert("RGB")
        if img.size != (ANCHO, IMG_ALTO):
            # se ajusta al ancho y se recorta centrado al alto del hueco
            escala = ANCHO / img.width
            img = img.resize((ANCHO, max(1, int(img.height * escala))), Image.LANCZOS)
            if img.height > IMG_ALTO:
                arriba = (img.height - IMG_ALTO) // 2
                img = img.crop((0, arriba, ANCHO, arriba + IMG_ALTO))
            elif img.height < IMG_ALTO:
                fondo = Image.new("RGB", (ANCHO, IMG_ALTO), FONDO)
                fondo.paste(img, (0, (IMG_ALTO - img.height) // 2))
                img = fondo
        out.append(img)
    return out


def _base(guion, fuente_datos, autor, credito_musica):
    """Lo fijo del video: título, aviso de IA y los créditos al pie."""
    img = reel._base(guion["titulo"], fuente_datos, autor)
    if credito_musica:
        d = ImageDraw.Draw(img)
        f = _fuente("PublicSans", 26, 400)
        d.text((MARGEN, 1596), f"Música: {credito_musica}", font=f, fill=SUAVE)
    return img


def _cuadro(base, cabeceras, imgs, narracion, t, bloques, fuente_sub):
    img = base.copy()
    i = max([k for k, (ini, _) in enumerate(narracion.escenas) if ini - reel.PAUSA <= t] or [0])
    a = min(1.0, max(0.0, (t - narracion.escenas[i][0] + reel.PAUSA) / 0.35))

    if imgs[i] is not None:
        if a < 1:                       # la imagen entra con un fundido corto
            fondo = Image.new("RGB", (ANCHO, IMG_ALTO), FONDO)
            img.paste(Image.blend(fondo, imgs[i], a), (0, IMG_Y))
        else:
            img.paste(imgs[i], (0, IMG_Y))

    capa = cabeceras[i]
    if a < 1:
        capa = capa.copy()
        capa.putalpha(capa.getchannel("A").point(lambda v: int(v * a)))
    img.paste(capa, (0, int(40 * (1 - a))), capa)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle((MARGEN, 180, ANCHO - MARGEN, 188), radius=4, fill=CAJA)
    d.rounded_rectangle((MARGEN, 180, MARGEN + (ANCHO - 2*MARGEN) * t / narracion.duracion, 188),
                        radius=4, fill=ACENTO)

    b = next((b for b in bloques if b[0][0] - 0.1 <= t <= b[-1][1] + 0.25), None)
    if b:
        texto = " ".join(p[2] for p in b)
        w = d.textlength(texto, font=fuente_sub)
        x, y = (ANCHO - w) / 2, 1330
        d.rounded_rectangle((x - 36, y - 26, x + w + 36, y + fuente_sub.size + 34), radius=28, fill=CAJA)
        for ini, fin, palabra in b:
            d.text((x, y), palabra, font=fuente_sub, fill=ACENTO if ini <= t <= fin + 0.05 else TEXTO)
            x += d.textlength(palabra + " ", font=fuente_sub)
    return img


def _lufs(ruta):
    """Sonoridad integrada del archivo, en LUFS, medida por ffmpeg."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(ruta),
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r'"input_i"\s*:\s*"(-?[\d.]+)"', r.stderr)
    if not m:
        raise SystemExit(f"No se pudo medir el volumen de la música: {ruta}")
    return float(m[-1])


def _audio(ruta_wav, musica, duracion, musica_lufs=-30):
    """Argumentos de ffmpeg para la pista de audio, con o sin música de fondo.

    La música se baja a `musica_lufs` según su sonoridad medida, de modo que quede
    igual de discreta sea cual sea el archivo que se use, y la mezcla completa se
    normaliza a -14 LUFS como en el reel de la clase.
    """
    if not musica:
        return (["-i", str(ruta_wav)],
                ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-map", "0:v", "-map", "1:a"])
    ganancia = max(-48.0, min(0.0, musica_lufs - _lufs(musica)))
    filtro = (f"[2:a]aresample=48000,volume={ganancia:.1f}dB,"
              f"afade=t=in:st=0:d=1.5,afade=t=out:st={max(0, duracion - 2.5):.2f}:d=2.5[mus];"
              f"[1:a]aresample=48000,loudnorm=I=-14:TP=-1.5:LRA=11[nar];"
              f"[nar][mus]amix=inputs=2:duration=first:normalize=0[mix];"
              f"[mix]loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    print(f"   música a {ganancia:.1f} dB ({musica_lufs} LUFS, voz a -14)")
    return (["-i", str(ruta_wav), "-stream_loop", "-1", "-i", str(musica)],
            ["-filter_complex", filtro, "-map", "0:v", "-map", "[a]"])


def video(guion, narracion, ruta, fuente_datos, autor, imagenes="imagenes",
          musica=None, credito_musica="", musica_lufs=-30):
    ruta = Path(ruta)
    wav = ruta.with_suffix(".wav")
    import soundfile as sf
    sf.write(wav, narracion.audio, narracion.sr)

    base = _base(guion, fuente_datos, autor, credito_musica)
    cabeceras = [_cabecera(e) for e in guion["escenas"]]
    imgs = _imagenes(guion, imagenes)
    bloques = _bloques(narracion.palabras)
    fuente_sub = _fuente("PublicSans", 58, 800)

    ent, mapa = _audio(wav, musica, narracion.duracion, musica_lufs)
    cmd = ([FFMPEG, "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-"]
           + ent
           + ["-c:v", "libx264", "-preset", "fast", "-threads", "2", "-crf", "20", "-pix_fmt", "yuv420p"]
           + mapa
           + ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(ruta)])
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for k in range(int(narracion.duracion * FPS)):
            proc.stdin.write(_cuadro(base, cabeceras, imgs, narracion, k / FPS, bloques, fuente_sub).tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass   # ffmpeg ya cortó: su mensaje de error está arriba
    if proc.wait() != 0:
        raise SystemExit("ffmpeg falló al armar el video; revisa el mensaje anterior")
    return ruta


def portada(guion, narracion, ruta, fuente_datos, autor, imagenes="imagenes",
            credito_musica="", escena=1):
    t = narracion.escenas[escena][0] + 1.0
    img = _cuadro(_base(guion, fuente_datos, autor, credito_musica),
                  [_cabecera(e) for e in guion["escenas"]], _imagenes(guion, imagenes),
                  narracion, t, _bloques(narracion.palabras), _fuente("PublicSans", 58, 800))
    img.save(ruta)
    return ruta
