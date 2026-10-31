# -*- coding: utf-8 -*-
"""Arma web/data.js (lo que el tablero carga al inicio) y dist/ispn_2025_tablero.html,
una copia autocontenida que ademas incluye los 42 reportes de cumplimiento.

En GitHub Pages los reportes se cargan bajo demanda desde web/data/rc/; la copia
autocontenida sirve para abrir el tablero sin servidor.
"""
import json, os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB, DIST = os.path.join(RAIZ, "web"), os.path.join(RAIZ, "dist")
DATOS = os.path.join(WEB, "data")

bundle = {k: json.load(open(os.path.join(DATOS, k + ".json"), encoding="utf-8"))
          for k in ["politicas", "criterios", "resumen", "indicadores", "estandares"]}
js = "// Generado por scripts/empaquetar.py - no editar a mano\nwindow.DATOS = " + \
     json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(os.path.join(WEB, "data.js"), "w", encoding="utf-8").write(js)

html = open(os.path.join(WEB, "index.html"), encoding="utf-8").read()
rc = json.dumps({f: json.load(open(os.path.join(DATOS, "rc", f), encoding="utf-8"))
                 for f in sorted(os.listdir(os.path.join(DATOS, "rc"))) if f.endswith(".json")}, ensure_ascii=False)
html = html.replace('<script src="data.js"></script>', "<script>\n" + js + "window.RC_TODO = " + rc + ";\n</script>")
os.makedirs(DIST, exist_ok=True)
sal = os.path.join(DIST, "ispn_2025_tablero.html")
open(sal, "w", encoding="utf-8").write(html)

kb = lambda p: f"{os.path.getsize(p)/1024:.0f} KB"
print(f"web/data.js {kb(os.path.join(WEB,'data.js'))}  |  {sal} {kb(sal)}")
