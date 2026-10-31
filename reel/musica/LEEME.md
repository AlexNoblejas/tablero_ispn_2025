# Música de fondo del reel

`fondo.wav` no se descargó de ningún sitio: lo genera `hacer_musica.py` sumando ondas
con numpy (acordes de La menor, ataques lentos, nada de percusión ni melodía). Es una
pista propia, así que no hay licencia que respetar ni atribución que gestionar, y el
video la acredita igual, como corresponde:

> Música: pista original generada con hacer_musica.py

Para cambiarla:

```bash
python hacer_musica.py --segundos 90        # vuelve a generar fondo.wav
```

## Si prefieres una pista de catálogo

Sirve cualquier archivo con licencia que permita su uso. Al pasarla con `--musica`,
el script mide su sonoridad y la baja sola a −30 LUFS, dieciséis unidades por debajo
de la narración, así que no hace falta editarla antes:

```bash
python hacer_reel_visual.py ... --musica musica/otra.mp3 --credito-musica "Título — Autor (CC0)"
```

Fuentes habituales de música libre: Free Music Archive (filtro CC0), Pixabay Music,
Incompetech (CC BY, exige citar al autor) y la Biblioteca de audio de YouTube. En todos
los casos hay que copiar el crédito tal como lo pide la licencia en `--credito-musica`:
aparece al pie del video.
