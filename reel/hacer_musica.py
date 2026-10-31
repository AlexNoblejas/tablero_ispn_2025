# -*- coding: utf-8 -*-
"""Genera la pista de fondo del reel: un colchón sintetizado, propio y sin licencias.

No descarga nada. Arma acordes con ondas sumadas, ataques lentos y un poco de aire,
en la nota de la institución: sobrio, sin percusión y sin melodía que compita con la voz.

    python hacer_musica.py                 # musica/fondo.wav, 72 s
    python hacer_musica.py --segundos 90
"""
import argparse

import numpy as np
import soundfile as sf

SR = 48000
# La menor: Am - F - C - G, ocho segundos cada acorde, dos vueltas
NOTAS = {"A2": 110.00, "C3": 130.81, "E3": 164.81, "F2": 87.31, "A3": 220.00,
         "C4": 261.63, "G2": 98.00, "B3": 246.94, "D4": 293.66, "E4": 329.63, "G4": 392.00}
ACORDES = [("A2", "E3", "A3", "C4"), ("F2", "C3", "A3", "C4"),
           ("C3", "G2", "E4", "G4"), ("G2", "D4", "B3", "G4")]


def _voz(f, n, sr=SR):
    """Una nota: fundamental más dos armónicos suaves y un vibrato muy leve."""
    t = np.arange(n) / sr
    vib = 1 + 0.0015 * np.sin(2 * np.pi * 0.18 * t)
    y = np.sin(2 * np.pi * f * vib * t)
    y += 0.30 * np.sin(2 * np.pi * 2 * f * vib * t + 0.7)
    y += 0.12 * np.sin(2 * np.pi * 3 * f * vib * t + 1.9)
    return y


def _envolvente(n, ataque, caida, sr=SR):
    e = np.ones(n)
    a, c = int(ataque * sr), int(caida * sr)
    e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    e[n - c:] = np.cos(np.linspace(0, np.pi / 2, c)) ** 2
    return e


def pista(segundos=72, compas=8.0, sr=SR):
    n = int(segundos * sr)
    y = np.zeros(n)
    paso = int(compas * sr)
    largo = int((compas + 2.5) * sr)          # los acordes se encabalgan
    for i, acorde in enumerate(ACORDES * (int(segundos / compas / len(ACORDES)) + 2)):
        ini = i * paso
        if ini >= n:
            break
        m = min(largo, n - ini)
        bloque = sum(_voz(NOTAS[k], m, sr) * p for k, p in zip(acorde, (0.9, 0.5, 0.35, 0.22)))
        y[ini:ini + m] += bloque * _envolvente(m, 2.2, 2.2, sr)

    t = np.arange(n) / sr
    aire = np.random.default_rng(7).normal(0, 1, n)       # ruido filtrado: "aire" de sala
    k = np.hanning(2001); k /= k.sum()
    aire = np.convolve(aire, k, "same")
    y = y / (np.abs(y).max() + 1e-9) * 0.82 + aire / (np.abs(aire).max() + 1e-9) * 0.06
    y *= 0.9 + 0.1 * np.sin(2 * np.pi * 0.045 * t)        # respiración lenta
    y *= _envolvente(n, 0.8, 3.0, sr)
    return (y / (np.abs(y).max() + 1e-9) * 0.7).astype(np.float32)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--segundos", type=float, default=72)
    p.add_argument("--salida", default="musica/fondo.wav")
    a = p.parse_args()
    sf.write(a.salida, pista(a.segundos), SR)
    print(f"  {a.salida}  {a.segundos:.0f} s")
