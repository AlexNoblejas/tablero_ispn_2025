"""Paso 2 de la Tarea 3: guion.json -> voz clonada -> reel vertical con gráficos y música.

Mismo flujo de la sesión 15 (`hacer_reel.py`), con tres añadidos que pide la tarea:
el reel muestra un gráfico por escena, lleva música de fondo por debajo de la voz
y acredita esa música en el video.

    # 1) los gráficos de cada escena, desde los datos del tablero
    python hacer_imagenes.py

    # 2) el reel
    python hacer_reel_visual.py --voz mi_voz.m4a \
        --autor "Alexander Noblejas" \
        --fuente "CEPLAN, Informe Anual de Políticas Nacionales 2025" \
        --musica musica/fondo.mp3 --credito-musica "Título — Autor (CC0)"

Guarda en salidas/: reel.mp4, reel.wav, reel.srt, portada.png y posts.md,
y añade el WER de cada escena a guion.json.
"""
import argparse
import json
import time

import reel
import reel_visual

p = argparse.ArgumentParser()
p.add_argument("--voz", required=True, help="10 a 20 s de tu voz: wav, m4a, ogg o mp3")
p.add_argument("--autor", required=True)
p.add_argument("--fuente", required=True, help="fuente de los datos, aparece en el video")
p.add_argument("--imagenes", default="imagenes", help="carpeta con el gráfico de cada escena")
p.add_argument("--musica", default=None, help="pista de fondo (mp3, m4a, wav); se mezcla por debajo de la voz")
p.add_argument("--credito-musica", default="", help="título y autor de la música, aparece en el video")
p.add_argument("--musica-lufs", type=float, default=-30, help="volumen de la música; más negativo = más baja")
p.add_argument("--device", default="auto", help="auto, cpu, mps (Mac) o cuda")
p.add_argument("--motor", default="qwen", choices=["qwen", "voxcpm"], help="voxcpm acepta estilo de locutor por escena")
p.add_argument("--tts", default=reel.TTS, help="con --motor qwen; Qwen/Qwen3-TTS-12Hz-0.6B-Base es más rápido en CPU")
p.add_argument("--sin-estilo", action="store_true", help="con --motor voxcpm: clona sin indicar estilo")
p.add_argument("--velocidad", type=float, default=1.0, help="1.08 = 8 %% más rápido, sin cambiar el tono")
p.add_argument("--salidas", default=str(reel_visual.AQUI / "salidas"))
a = p.parse_args()

t0 = time.time()
salidas = reel.Path(a.salidas)
salidas.mkdir(exist_ok=True)
archivo_guion = salidas / "guion.json"

guion = json.loads(archivo_guion.read_text(encoding="utf-8"))
for e in guion["escenas"]:
    print(f"   {'ok ' if e.get('cifra_en_texto') else '¡¡ '} {e['cifra'] or '-':>10} | {e['frase']}")
if not all(e.get("cifra_en_texto") for e in guion["escenas"]):
    print("   ¡Ojo! Hay cifras que no aparecen tal cual en el texto: revisen guion.json antes de publicar.")

# se verifica que exista el gráfico de cada escena antes de gastar minutos en la voz
reel_visual._imagenes(guion, a.imagenes)
if a.musica and not reel.Path(a.musica).exists():
    raise SystemExit(f"No se encuentra la música: {a.musica}")
if a.musica and not a.credito_musica:
    print("   ¡Ojo! Falta --credito-musica: la pista debe quedar acreditada en el video.")

if a.device == "auto":
    import torch
    a.device = "cuda" if torch.cuda.is_available() else "cpu"

if a.motor == "voxcpm":
    voz = reel.VozExpresiva(a.voz, device=a.device, con_estilo=not a.sin_estilo)
else:
    voz = reel.Voz(a.voz, modelo=a.tts, device=a.device)
reel._reloj(f"voz cargada; referencia: «{voz.texto_ref}»", t0)
narracion = reel.narrar(voz, guion, velocidad=a.velocidad)
archivo_guion.write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
reel._reloj(f"narración: {narracion.duracion:.1f} s; WER por escena: "
            + ", ".join(f"{e['wer']:.2f}" for e in guion["escenas"]), t0)

if any(e["wer"] > 0.25 for e in guion["escenas"]):
    raise SystemExit("La voz no supera el control de transcripción; revisa el WER antes de publicar.")
if not 45 <= narracion.duracion <= 75:
    raise SystemExit(f"Duración {narracion.duracion:.1f}s fuera del rango 45–75s; ajusta --velocidad.")

reel.subtitulos(narracion, guion)
reel.a_srt(narracion, salidas / "reel.srt")
reel._reloj(f"subtítulos: {len(narracion.palabras)} palabras", t0)

# Guardar la narración antes del montaje permite reanudar sin volver a clonar la voz.
import soundfile as sf
import gc
sf.write(salidas / "reel.wav", narracion.audio, narracion.sr)
(salidas / "narracion.json").write_text(json.dumps({"sr": narracion.sr, "escenas": narracion.escenas,
                                                 "palabras": narracion.palabras}, ensure_ascii=False), encoding="utf-8")
del voz
reel._ASR = None
gc.collect()
try:
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
except ImportError:
    pass

reel_visual.portada(guion, narracion, salidas / "portada.png", a.fuente, a.autor,
                    imagenes=a.imagenes, credito_musica=a.credito_musica)
reel_visual.video(guion, narracion, salidas / "reel.mp4", a.fuente, a.autor,
                  imagenes=a.imagenes, musica=a.musica, credito_musica=a.credito_musica,
                  musica_lufs=a.musica_lufs)
reel.posts(guion, salidas / "posts.md")
reel._reloj(f"listo: {salidas / 'reel.mp4'}", t0)
