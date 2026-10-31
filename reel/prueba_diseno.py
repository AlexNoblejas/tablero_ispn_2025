"""Render de prueba: arma el reel con una voz simulada, solo para revisar el diseño.

No usa TTS ni Whisper. Inventa la duración de cada escena (a 2.6 palabras por segundo)
y reparte las palabras dentro de ella, para ver el encuadre, los gráficos, los subtítulos
y la mezcla con la música antes de grabar la voz de verdad.

    python prueba_diseno.py                  # salidas_prueba/portada_eN.png + reel_prueba.mp4
    python prueba_diseno.py --solo-cuadros   # solo las imágenes, sin armar el video
"""
import json
import sys
from pathlib import Path

import numpy as np

import reel
import reel_visual

AQUI = Path(__file__).parent
SAL = AQUI / "salidas_prueba"
SAL.mkdir(exist_ok=True)
PPS = 2.6   # palabras por segundo


def narracion_simulada(guion, sr=24000):
    partes, escenas, palabras, t = [np.zeros(int(reel.INICIO * sr), np.float32)], [], [], reel.INICIO
    for e in guion["escenas"]:
        ws = e["frase"].split()
        dur = len(ws) / PPS
        n = int(dur * sr)
        # tono suave modulado, solo para que la pista tenga nivel
        x = np.arange(n) / sr
        env = 0.5 + 0.5 * np.sin(2 * np.pi * 2.4 * x)
        w = (0.08 * env * np.sin(2 * np.pi * 150 * x)).astype(np.float32)
        escenas.append((t, t + dur))
        paso = dur / len(ws)
        for i, p in enumerate(ws):
            palabras.append((t + i * paso, t + (i + 1) * paso - 0.02, p))
        partes += [w, np.zeros(int(reel.PAUSA * sr), np.float32)]
        t += dur + reel.PAUSA
    partes.append(np.zeros(int(reel.FINAL * sr), np.float32))
    return reel.Narracion(np.concatenate(partes), sr, escenas, palabras)


if __name__ == "__main__":
    guion = json.loads((AQUI / "salidas" / "guion.json").read_text(encoding="utf-8"))
    nar = narracion_simulada(guion)
    print(f"duración simulada: {nar.duracion:.1f} s · {len(nar.palabras)} palabras")

    # un cuadro por escena, para revisar encuadre y gráficos
    for i in range(len(guion["escenas"])):
        reel_visual.portada(guion, nar, SAL / f"portada_e{i+1}.png",
                            "CEPLAN, Informe Anual de Políticas Nacionales 2025",
                            "Alexander Noblejas", imagenes=str(AQUI / "imagenes"),
                            credito_musica="pista de prueba", escena=i)
    print("cuadros:", *(p.name for p in sorted(SAL.glob("portada_e*.png"))))

    if "--solo-cuadros" not in sys.argv:
        reel_visual.video(guion, nar, SAL / "reel_prueba.mp4",
                          "CEPLAN, Informe Anual de Políticas Nacionales 2025",
                          "Alexander Noblejas", imagenes=str(AQUI / "imagenes"),
                          musica=str(AQUI / "musica" / "fondo.wav"),
                          credito_musica="pista original generada con hacer_musica.py")
        print("video:", SAL / "reel_prueba.mp4")
