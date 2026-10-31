"""Reanuda el montaje desde salidas/reel.wav y narracion.json, sin cargar modelos de IA."""
import argparse
import json
from pathlib import Path
import soundfile as sf
import reel
import reel_visual


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salidas", type=Path, default=Path(__file__).parent / "salidas")
    p.add_argument("--autor", default="Alexander Noblejas")
    p.add_argument("--fuente", default="CEPLAN, Informe Anual de Políticas Nacionales 2025")
    a = p.parse_args()
    base = Path(__file__).parent
    g = json.loads((a.salidas / "guion.json").read_text(encoding="utf-8"))
    meta = json.loads((a.salidas / "narracion.json").read_text(encoding="utf-8"))
    audio, sr = sf.read(a.salidas / "reel.wav", dtype="float32")
    n = reel.Narracion(audio, sr, meta["escenas"], meta["palabras"])
    if not 45 <= n.duracion <= 75:
        raise SystemExit("La narración debe durar entre 45 y 75 segundos.")
    reel_visual.video(g, n, a.salidas / "reel.mp4", a.fuente, a.autor,
                      imagenes=base / "imagenes", musica=base / "musica/fondo.wav",
                      credito_musica="composición original del autor")
    reel.posts(g, a.salidas / "posts.md")
    print("Listo:", a.salidas / "reel.mp4")


if __name__ == "__main__":
    main()
