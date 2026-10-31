# Reel del tablero ISPN 2025

Parte 3 de la Tarea 3. Reel vertical de ~52 segundos, narrado con la voz clonada del
autor, con un gráfico de datos reales en cada escena, subtítulos palabra por palabra,
música de fondo por debajo de la voz y el aviso de que la voz fue generada con IA.

## Qué hay aquí

| Archivo | Qué es |
|---|---|
| `salidas/guion.json` | Guion de 6 escenas (131 palabras ≈ 52 s) y los tres posts |
| `hacer_imagenes.py` | Genera los seis gráficos desde los datos del tablero |
| `imagenes/e1…e6.png` | Franjas 1080×600, una por escena |
| `capturas/*.png` | Capturas del tablero: la escena 6 y las que van a LinkedIn |
| `hacer_musica.py` · `musica/fondo.wav` | Pista de fondo propia, sintetizada con numpy |
| `reel_visual.py` | Extiende `reel.py` de la clase: imagen por escena + mezcla con música |
| `hacer_reel_visual.py` | El script que arma el reel (equivale a `hacer_reel.py`) |
| `hacer_reel.bat` | Lo anterior en un doble clic, para Windows |
| `mi_voz.wav` | La grabación de referencia, 22.8 s. No se versiona |
| `prueba_diseno.py` | Render de prueba con voz simulada, para revisar el diseño sin TTS |
| `reel.py` | Adaptación del módulo de la sesión 15: GPU y caché de escenas |

Todas las cifras del guion y de los posts están verificadas con el propio validador
de la clase (`guion._numeros`) contra el README del proyecto, que a su vez `preparar_datos.py`
verifica contra el informe publicado.

## Cómo se arma el reel

### 1. Grabar la voz

Ya está: `mi_voz.wav`, 22.8 segundos recortados de la grabación original. Se le quitó
el retumbe por debajo de 70 Hz y se le dejó 3 dB de aire para que no sature. No se
versiona (`.gitignore`).

Si hace falta regrabarla: de 15 a 25 segundos, cuarto callado, a un palmo del micrófono,
leyendo cualquier cosa con el tono que quieras en el reel. El clon copia la energía de
la grabación. Sirve `.wav`, `.m4a`, `.ogg` o `.mp3`.

### 2. Armar el reel en Windows

Doble clic en **`hacer_reel.bat`**. Crea el entorno la primera vez, baja los modelos
(unos 4 GB) y arma el reel. Con `hacer_reel.bat rapido` usa el modelo de voz chico,
útil para una primera prueba.

A mano, o fuera de Windows:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python hacer_reel_visual.py --voz mi_voz.wav \
    --autor "Alexander Noblejas" \
    --fuente "CEPLAN, Informe Anual de Políticas Nacionales 2025" \
    --musica musica/fondo.wav \
    --credito-musica "pista original generada con hacer_musica.py"
```

En una Mac con chip M, añadir `--device mps`. Si la narración sale lenta,
`--velocidad 1.08`. Con `--tts Qwen/Qwen3-TTS-12Hz-0.6B-Base` va más rápido en CPU.

Deja en `salidas/`: `reel.mp4`, `reel.wav`, `reel.srt`, `portada.png` y `posts.md`, y
escribe en `guion.json` el WER de cada escena: Whisper vuelve a transcribir la narración
y la compara con el texto; si una escena pasa de 0.25, el script la regenera solo.

### 3. Rehacer gráficos o música (ya están generados)

```bash
python hacer_imagenes.py      # lee los JSON del tablero y rehace imagenes/
python hacer_musica.py        # rehace musica/fondo.wav
```

`hacer_imagenes.py` busca los datos en `../web/data`; si el tablero está
en otro lado, se indica con la variable de entorno `ISPN_DATOS`.

### 4. Revisar el diseño sin gastar el modelo de voz

```bash
python prueba_diseno.py       # salidas_prueba/portada_eN.png y reel_prueba.mp4
```

Inventa la duración de cada escena y una voz de prueba, así se ve el encuadre, los
gráficos, los subtítulos y la mezcla con la música antes de clonar nada.

## Decisiones de diseño

- **El cuadro se parte en dos.** Arriba la cifra grande y su etiqueta (franja 400–622);
  abajo el gráfico de la escena (660–1260). El original de la clase centraba la cifra
  justo donde ahora va el gráfico, así que `reel_visual.py` redibuja esa parte.
- **La música se nivela sola.** El script mide la sonoridad del archivo y lo baja a
  −30 LUFS, dieciséis unidades por debajo de la narración (−14 LUFS), con entrada de
  1.5 s y salida de 2.5 s. Así suena igual de discreta con cualquier pista.
- **Paleta institucional.** Los gráficos usan la escala de color oficial del ISPN,
  la misma del tablero, sobre el fondo oscuro del reel de la clase.
- **Sin glifos especiales.** Las flechas y las tachas se dibujan con líneas, porque la
  fuente variable subconjuntada no trae esos símbolos y salían como cuadritos.

La generación procesa una escena por vez para reducir el uso de memoria de video. Los audios intermedios quedan en `salidas/cache/` (excluidos de Git); se reutilizan al reanudar y se regeneran cuando falla el control de transcripción. Para NVIDIA se puede usar `--device cuda` y el modelo de 0.6B.

Si la voz y los subtítulos ya están generados y el montaje se interrumpe, ejecutar `python renderizar_video.py`. Reutiliza `salidas/reel.wav` y `salidas/narracion.json`; no vuelve a cargar el modelo de voz. El montaje limita la compresión a dos hilos para reducir el consumo de memoria.
