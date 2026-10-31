# -*- coding: utf-8 -*-
"""
Informe Anual de Politicas Nacionales 2025 - preparacion de datos del tablero.

Fuentes
  - Resultados del ISPN 2025 por politica, criterio e indicador (sin complementarios)
  - Reportes de cumplimiento 2025 (texto por objetivo prioritario) y 2024 (nivel reportado)
  - Base de seguimiento de indicadores de politicas nacionales (series 2019-2025)
  - Matriz de consistencia de las politicas nacionales aprobadas (tipo de politica)

Se publica solo el resultado de la evaluacion. Quedan fuera las rondas de control
de calidad, los historiales de revision, los niveles de confianza, las alertas y
cualquier campo de auditoria interna.
"""
import openpyxl, json, os, re, difflib, unicodedata
from collections import Counter, defaultdict

# Rutas relativas a este archivo: <tarea_3>/repositorio/scripts/preparar_datos.py
# Las fuentes viven fuera del repositorio (no se versionan) en <tarea_3>/fuentes/.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.environ.get("ISPN_FUENTES") or os.path.join(os.path.dirname(RAIZ), "fuentes")
OUT = os.path.join(RAIZ, "web", "data")
os.makedirs(f"{OUT}/rc", exist_ok=True)

F_PROG = f"{SRC}/progreso_sin_complementarios.json"
F_ISPN = f"{SRC}/evaluacion_ispn_2025_sin_complementarios.xlsx"
F_RC25 = f"{SRC}/matriz_rc_2025.xlsx"
F_RC24 = f"{SRC}/matriz_rc_2024.xlsx"
F_SEG  = f"{SRC}/base_seguimiento_pn_2025.xlsx"
F_MC   = f"{SRC}/matriz_consistencia_50_pn.xlsx"

faltan = [os.path.basename(f) for f in (F_PROG, F_ISPN, F_RC25, F_RC24, F_SEG, F_MC) if not os.path.exists(f)]
if faltan:
    raise SystemExit(f"Faltan estas fuentes en {SRC}:\n  - " + "\n  - ".join(faltan) +
                     "\n\nColocalas ahi o define la variable de entorno ISPN_FUENTES con su carpeta.")

ANIO = 2025
ANIOS = list(range(2019, 2026))

# ------------------------------------------------------------------ utilidades
def limpiar(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v not in (None, "") else ""

SOLO_CIFRAS = re.compile(r"^[\d\s.,%()\-–|/+:x°N]*$")

def texto(v, resumen=False):
    """Conserva los parrafos del reporte y elimina residuos de su formato Word:
    filas de tablas aplanadas (tabuladores o celdas separadas por barras),
    lineas de solo cifras y, en el resumen, el bloque inicial del formulario
    (casillas de nivel y conteo de servicios), que ya se muestra en la ficha."""
    if v in (None, ""): return ""
    lineas = []
    for ln in str(v).replace("\r", "").split("\n"):
        if "\t" in ln or ln.count("|") >= 2:
            continue
        ln = re.sub(r"[  ]+", " ", ln).strip()
        if ln and (SOLO_CIFRAS.match(ln) or ln == "(%)"):
            continue
        if ln.startswith("(Se sugiere"):      # instruccion de la plantilla que la entidad no borro
            continue
        lineas.append(ln)
    if resumen:
        while lineas and len(lineas[0]) < 80:
            lineas.pop(0)
    t = "\n".join(lineas)
    return re.sub(r"\n{3,}", "\n\n", t).strip()

MARCADOR = re.compile(r"\[TEXTO COMPLETO EN HOJA[^\]]*?ID_REPORTE=(.+?)\s*·\s*SECCION=([A-Z_]+)(?:\s*·\s*N_OP=([A-Z.\d]+))?[^\]]*\]")

def completo(v, literal):
    """Excel corta las celdas largas y deja un marcador que apunta a la hoja de
    fragmentos; aqui se reemplaza la celda por el texto literal reconstruido."""
    m = MARCADOR.search(str(v or ""))
    if not m: return v
    clave = (m.group(1).strip(), m.group(2), (m.group(3) or "").strip(" ."))
    if clave not in literal: raise KeyError(f"Fragmentos no encontrados: {clave}")
    return literal[clave]

def num(v):
    if isinstance(v, bool): return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v or "").strip().replace("%", "").replace(" ", "")
    if not s or s.upper().startswith("ND"): return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+,\d+", s): s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d+,\d+", s): s = s.replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s): s = s.replace(",", "")
    try: return float(s)
    except ValueError: return None

def r2(v):
    return None if v is None else round(v, 2)

def plano(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s)

MENORES = {"de","del","la","las","los","y","e","en","el","para","a","con","al","sus","su"}
def oracion(s):
    """MAYUSCULAS -> Tipo oracion, respetando siglas conocidas."""
    s = limpiar(s)
    if not s or not s.isupper(): return s
    t = s.lower()
    t = t[:1].upper() + t[1:]
    return re.sub(r"\b(peru|perú)\b", "Perú", t)

def separar_codigo(s):
    """'IOP.01.01. PORCENTAJE ...' -> ('IOP.01.01', 'Porcentaje ...')"""
    s = limpiar(s)
    m = re.match(r"^([A-Z]{1,4}(?:\.\d+)+)\.?\s*(.*)$", s)
    return (m.group(1), oracion(m.group(2))) if m else ("", oracion(s))

def entidad(v):
    t = limpiar(v)
    t = re.sub(r"^\d+\s*:\s*", "", t)
    t = re.split(r"\s*[(–—]\s*|\s+a trav[eé]s de\s+|\s*,\s*que\s+|\s+\|", t)[0].strip(" .")
    out = []
    for i, w in enumerate(t.split()):
        b = w.lower()
        out.append(b if (i and b in MENORES) else b[:1].upper() + b[1:])
    return " ".join(out)

def guardar(nombre, obj):
    ruta = os.path.join(OUT, nombre)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
    return os.path.getsize(ruta)

def hoja(ruta, nombre):
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = [r for r in wb[nombre].iter_rows(min_row=2, values_only=True)]
    wb.close()
    return filas

# ------------------------------------------------------------- 1. resultados
print("[1/6] Resultados del ISPN")
prog = json.load(open(F_PROG, encoding="utf-8"))["resultados"]
resumen_x = {limpiar(r[0]): r for r in hoja(F_ISPN, "RESUMEN_ISPN") if r[0]}

ESCALA_MAX = [5, 5, 5, 5, 5, 3]
def ispn(crit):
    """ISPN = promedio de los seis criterios estandarizados a 0-100."""
    est = [(c - 1) / (m - 1) for c, m in zip(crit, ESCALA_MAX)]
    return round(100 * sum(est) / len(est), 1)

def situacion(v):
    if v < 40: return "Baja"
    if v < 60: return "Media"
    if v < 80: return "Media-alta"
    return "Alta"

# ------------------------------------------------------ 2. contexto de diseño
print("[2/6] Reportes de cumplimiento y matriz de consistencia")
rc25 = {limpiar(r[1]): r for r in hoja(F_RC25, "POR_POLITICA") if r[1]}
rc25_op = defaultdict(list)
for r in hoja(F_RC25, "INFO_GENERAL"):
    if r[1]: rc25_op[limpiar(r[1])].append(r)

frag = defaultdict(list)
for r in hoja(F_RC25, "RC_TEXTO_LITERAL"):
    if r[0] and r[4]:
        frag[(limpiar(r[0]), limpiar(r[1]), limpiar(r[2]).strip(" ."))].append((int(r[3] or 0), str(r[4])))
literal = {k: "".join(t for _, t in sorted(v)) for k, v in frag.items()}

niv24 = {}
for r in hoja(F_RC24, "INFO_GENERAL"):
    if r[1] and r[6]:
        partes = limpiar(r[1]).split("_")
        if len(partes) >= 4:
            niv24.setdefault(partes[2].upper(), limpiar(r[6]))

mc = {}
for r in hoja(F_MC, "50 aprobadas"):
    if r[1]:
        k = plano(r[1])
        if k not in mc:
            mc[k] = {"tipo": limpiar(r[7]), "periodo": limpiar(r[4]),
                     "problema": limpiar(r[10]), "sfd": limpiar(r[13]),
                     "poblacion": limpiar(r[11])}

# Siglas repetidas (PNA, PNC) se distinguen por la entidad, como en el informe
RECTOR = {"MINAM": "MINAM", "MIDAGRI": "MIDAGRI", "PRODUCE": "PRODUCE", "MINCUL": "CULTURA"}

politicas = []
for pid, x in sorted(prog.items()):
    rx = resumen_x.get(pid)
    rc = rc25.get(pid)
    numero = int(re.search(r"RC_(\d+)", pid).group(1))
    sigla = limpiar(rx[1]) if rx else pid.split("_")[-2]
    sector = re.search(r"RC_\d+\.\s*([A-Z]+)_", pid).group(1)
    nombre = re.sub(r"\s+[-–]\s+[A-Z0-9\-]+\s*$", "", limpiar(rx[2] if rx else x["politica"])).rstrip(".")
    if nombre.isupper():
        nombre = " ".join(w.lower() if (i and w.lower() in MENORES) else w.capitalize() for i, w in enumerate(nombre.split()))
    m = difflib.get_close_matches(plano(nombre), list(mc), n=1, cutoff=0.6)
    dis = mc[m[0]] if m else {}
    crit = [x["C1"]["puntaje"], x["C2"]["c2"], x["C3"]["c3"], x["C4"]["c4"], x["C5"]["c5"], x["C6"]["puntaje"]]
    crit = [int(c) for c in crit]
    valor = ispn(crit)
    aprob = int(num(rc[6])) if rc and num(rc[6]) else None
    c3, c2, c4, c5 = x["C3"], x["C2"], x["C4"], x["C5"]
    an3 = c3.get("analisis_ia") or {}
    politicas.append({
        "id": pid, "n": numero,
        "sigla": sigla, "etiqueta": sigla,
        "sector": sector,
        "nombre": nombre,
        "ministerio": entidad(rx[3] if rx else x["ministerio"]),
        "tipo": dis.get("tipo", "").strip() or "Sin dato",
        "periodo": dis.get("periodo", ""),
        "aprobacion": aprob,
        "anios": (ANIO - aprob) if aprob else None,
        "dispositivo": limpiar(rc[5]) if rc else "",
        "problema": limpiar(rc[4]) if rc else dis.get("problema", ""),
        "sfd": dis.get("sfd", "")[:900],
        "nivel": limpiar(x.get("nivel_implementacion_reportado")) or "No reportó",
        "nivel_2024": niv24.get(sigla.upper(), ""),
        "criterios": crit,
        "ispn": valor,
        "situacion": situacion(valor),
        "c2": {"num": c2.get("numerador"), "den": c2.get("denominador"), "pct": c2.get("porcentaje")},
        "c3": {"num": int(c3.get("numerador") or 0), "den": int(c3.get("denominador") or 0), "pct": c3.get("porcentaje")},
        "c4": {"num": c4.get("numerador"), "den": c4.get("denominador"), "pct": c4.get("porcentaje"),
               "excluidos": c4.get("excluidos_nd"), "registrados": c4.get("iss_registrados")},
        "c5": {"num": c5.get("numerador"), "den": c5.get("denominador"), "pct": c5.get("porcentaje")},
        "com": {
            "C1": limpiar(x["C1"].get("comentario_completo")),
            "C2": limpiar(c2.get("comentario_calculo")),
            "C3": limpiar(c3.get("comentario_completo") or c3.get("comentario_calculo")),
            "C4": limpiar(c4.get("comentario_calculo")),
            "C5": limpiar(c5.get("comentario_calculo")),
            "C6": limpiar(x["C6"].get("comentario_completo")),
        },
        "destacados": [limpiar(s) for s in an3.get("servicios_destacados", []) if s][:6],
        "dificultades": [limpiar(s) for s in an3.get("servicios_con_dificultades", []) if s][:6],
        "texto": limpiar(x.get("SITUACION_POLITICA")),
    })

cuenta = Counter(p["sigla"] for p in politicas)
for p in politicas:
    if cuenta[p["sigla"]] > 1:
        p["etiqueta"] = f'{p["sigla"]}-{RECTOR.get(p["sector"], p["sector"])}'

politicas.sort(key=lambda p: (-p["ispn"], p["etiqueta"]))
for i, p in enumerate(politicas, 1):
    p["puesto"] = i

# ----------------------------------------------------------- 3. indicadores
print("[3/6] Indicadores y series 2019-2025")
serie = {}
for r in hoja(F_SEG, "BD_PN"):
    if not r[1] or not r[6]: continue
    npol = re.match(r"\s*(\d+)", str(r[1]))
    cod, _ = separar_codigo(r[6])
    if not npol or not cod: continue
    ln_cod, ln_nom = separar_codigo(r[4])
    serie[(int(npol.group(1)), cod)] = {
        "lb_anio": int(num(r[16])) if num(r[16]) else None,
        "lb": r2(num(r[17])),
        "le": [r2(num(r[18 + j])) for j in range(7)],
        "vo": [r2(num(r[25 + j])) for j in range(7)],
        "fuente": limpiar(r[8])[:160],
        # avance tipo I: logro obtenido frente al logro esperado, tope 100 (informe)
        "av": r2(num(r[32])),
        "tipo_ind": limpiar(r[10]).capitalize() if limpiar(r[10]) not in ("", "NO APLICA") else "",
        "estandar": limpiar(r[11]).capitalize() if limpiar(r[11]) not in ("", "NO APLICA") else "",
        "parametro": limpiar(r[15]).capitalize() if limpiar(r[15]) not in ("", "-") else "",
        "ln": ln_cod, "lnn": ln_nom[:220],
        # comentario que la entidad registro junto al valor del indicador
        "comentario": limpiar(r[33])[:700],
    }

def escala_inconsistente(s):
    """Porcentaje registrado como proporcion en un anio y como porcentaje en el
    siguiente (por ejemplo 0.83 y 83). Se senala; no se corrige."""
    if not s or s.get("parametro") != "Porcentaje": return False
    v = [x for x in s["vo"]]
    for a, b in zip(v, v[1:]):
        if a in (None, 0) or b in (None, 0): continue
        lo, hi = min(a, b), max(a, b)
        if lo <= 1 and hi > 1.5 and hi / lo >= 20:
            return True
    return False

def estado_c2(d):
    if not d.get("cuenta"): return "Sin dato"
    return "Favorable" if d.get("BE_positivo") else "No favorable"

def estado_c4(d):
    e = limpiar(d.get("estado")).lower()
    if not d.get("cuenta") or e.startswith("nd"): return "Sin dato"
    return "Favorable" if e.startswith("mejor") else "No favorable"

indicadores = []
pol_por_id = {p["id"]: p for p in politicas}
sin_serie = 0
for pid, x in prog.items():
    p = pol_por_id[pid]
    npol = int(re.match(r"\s*(\d+)", x["C5"]["detalle"][0]["politica"]).group(1)) if x["C5"].get("detalle") else None
    est = {}
    for d in x["C2"].get("detalle", []):
        est[separar_codigo(d["indicador"])[0]] = (estado_c2(d), d)
    for d in x["C4"].get("detalle", []):
        est[separar_codigo(d["indicador"])[0]] = (estado_c4(d), d)
    for d in x["C5"].get("detalle", []):
        cod, nom = separar_codigo(d["indicador"])
        e, dd = est.get(cod, ("Sin dato", {}))
        s = serie.get((npol, cod))
        if not s: sin_serie += 1
        tipo = "OP" if d.get("tipo_elemento") == "OBJETIVO" else "Servicio"
        op_cod, op_nom = separar_codigo(d.get("objetivo"))
        sv_cod, sv_nom = separar_codigo(d.get("servicio"))
        ref = None
        if tipo == "Servicio" and dd:
            ref = "año anterior" if "2024" in limpiar(dd.get("estado")) else ("línea de base" if "LB" in limpiar(dd.get("estado")) else None)
        indicadores.append({
            "p": pid, "c": cod, "nm": nom, "t": tipo,
            "op": op_cod, "opn": op_nom[:200],
            "sv": sv_cod, "svn": sv_nom[:220],
            "se": limpiar(d.get("sentido")).capitalize(),
            "rs": limpiar(d.get("responsable"))[:90],
            "lb": r2(d.get("lb")), "le": r2(d.get("le")),
            "vo": r2(d.get("vo")), "vp": r2(num(dd.get("vo_previo"))) if dd else None,
            "e": e, "ref": ref,
            "s": s,
            "esc": escala_inconsistente(s),
        })
print(f"      {len(indicadores)} indicadores | sin serie en la base: {sin_serie}")

# resumen por politica para filtros y graficos
agg = defaultdict(Counter)
meta = defaultdict(Counter)        # cruce: mejora frente al anio anterior x alcance de la meta 2025
for i in indicadores:
    agg[i["p"]][(i["t"], i["e"])] += 1
    av = (i["s"] or {}).get("av")
    if av is not None:
        meta[i["p"]]["con_meta"] += 1
        meta[i["p"]]["alcanza"] += av >= 100
        if i["e"] != "Sin dato":
            mejora = i["e"] == "Favorable"
            meta[i["p"]][("mejora" if mejora else "retrocede") + "_" + ("alcanza" if av >= 100 else "no_alcanza")] += 1
for p in politicas:
    a = agg[p["id"]]
    p["ind"] = {t: {e: a[(t, e)] for e in ["Favorable", "No favorable", "Sin dato"]} for t in ["OP", "Servicio"]}
    m = meta[p["id"]]
    p["meta"] = {k: m[k] for k in ["con_meta", "alcanza", "mejora_alcanza", "mejora_no_alcanza", "retrocede_alcanza", "retrocede_no_alcanza"]}
    p["pct_meta"] = round(100 * m["alcanza"] / m["con_meta"], 1) if m["con_meta"] >= 5 else None
    p["n_ind"] = sum(a.values())
    p["n_serv"] = p["c3"]["den"]
    p["n_op"] = len({i["op"] for i in indicadores if i["p"] == p["id"] and i["op"]})
    p["atencion"] = sum(1 for i in indicadores if i["p"] == p["id"] and i["e"] == "No favorable"
                        and (i["s"] or {}).get("av") is not None and i["s"]["av"] < 100)

# Desempeno de los servicios segun el estandar de cumplimiento que mide su indicador
por_estandar = defaultdict(Counter)
for i in indicadores:
    s = i["s"] or {}
    if i["t"] != "Servicio" or i["e"] == "Sin dato": continue
    est = s.get("estandar") or "Sin estándar"
    est = {"Accesibilidad geográfica": "Accesibilidad geográfica"}.get(est, est)
    por_estandar[est]["n"] += 1
    por_estandar[est]["fav"] += i["e"] == "Favorable"
    if s.get("av") is not None:
        por_estandar[est]["con_meta"] += 1
        por_estandar[est]["alcanza"] += s["av"] >= 100
estandares = sorted([{"estandar": k, "n": v["n"], "fav": v["fav"], "pct_fav": round(100*v["fav"]/v["n"], 1),
                      "con_meta": v["con_meta"], "pct_meta": round(100*v["alcanza"]/v["con_meta"], 1) if v["con_meta"] else None}
                     for k, v in por_estandar.items() if v["n"] >= 25 and k != "Sin estándar"],
                    key=lambda x: -x["pct_fav"])

# ------------------------------------------------- 4. reportes de cumplimiento
print("[4/6] Reportes de cumplimiento 2025 (un archivo por politica)")

RE_FIG   = re.compile(r"^(ilustraci[oó]n|gr[aá]fico|figura|tabla|cuadro|mapa|imagen)\s*(?:n\.?\s*[°º]?\s*)?(\d+)\s*[:.\-–]?\s*(.*)$", re.I)
RE_TIT   = re.compile(r"^(OP|OE)\.?\s?\d+\.?\s+\S")
RE_SRC   = re.compile(r"^(fuente|elaboraci[oó]n)\b", re.I)
RE_NOTA  = re.compile(r"^nota al pie\s*(\d+)\s*[:.]?\s*(.*)$", re.I)
RE_LI    = re.compile(r"^[•\-–▪●◦]\s*")
RE_COD   = re.compile(r"^(IOP|ISS|OP|SS|LN|AO)(\.\d+)+\.?$")

def es_resto_tabla(ln):
    """Celdas de una tabla del Word que quedaron como lineas sueltas."""
    if RE_COD.match(ln): return True
    return len(ln) < 70 and not re.search(r"[.:;?!)]$", ln) and not RE_LI.match(ln) and not RE_FIG.match(ln)

SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
RE_LLAMADA = re.compile(r"(?<=[a-záéíóúñ\)])(\d{1,2})(?=[\s,.;:)]|$)")
RE_LLAMADA_ANIO = re.compile(r"\b(20[0-3]\d)(\d)(?=[\s,.;:)]|$)")

def llamadas(t):
    """Las llamadas de nota al pie quedaron pegadas al texto ('indicadores5',
    '20254'); se convierten en superindices."""
    t = RE_LLAMADA_ANIO.sub(lambda m: m.group(1) + m.group(2).translate(SUP), t)
    return RE_LLAMADA.sub(lambda m: m.group(1).translate(SUP), t)

def bloques(t):
    if re.search(r"(?im)^nota al pie\s*\d", t):
        t = "\n".join(l if RE_NOTA.match(l.strip()) else llamadas(l) for l in t.split("\n"))
    return _bloques(t)

def _bloques(t):
    """Convierte el texto plano del reporte en bloques tipados para el tablero:
    p (parrafo), li (vineta), fig (lugar donde el original tenia un grafico o
    tabla), src (fuente de ese grafico) y nota (nota al pie)."""
    lineas = [l for l in t.split("\n") if l.strip()]
    out, notas, i = [], [], 0
    while i < len(lineas):
        ln = lineas[i].strip()
        # racha de restos de tabla: se reemplaza por un solo marcador
        j = i
        while j < len(lineas) and es_resto_tabla(lineas[j].strip()):
            j += 1
        if j - i >= 2 or (j - i == 1 and RE_COD.match(ln)):
            if j - i >= 3 and (not out or out[-1][0] != "fig"):
                out.append(["fig", "Tabla del documento original"])
            i = j
            continue
        m = RE_FIG.match(ln)
        if m:
            titulo = (m.group(3) or "").strip(" .") or "Sin título"
            out.append(["fig", f"{m.group(1).capitalize()} {m.group(2)} · {titulo}"])
        elif RE_TIT.match(ln) and len(ln) < 260:
            out.append(["h", ln])
        elif RE_SRC.match(ln) and len(ln) < 220:
            out.append(["src", ln])
        elif RE_NOTA.match(ln):
            mm = RE_NOTA.match(ln)
            notas.append(["nota", f"{mm.group(1)}. {mm.group(2)}"])
        elif RE_LI.match(ln):
            out.append(["li", RE_LI.sub("", ln)])
        else:
            out.append(["p", ln])
        i += 1
    return out + notas

catalogo_op = {(i["p"], i["op"]): i["opn"] for i in indicadores if i["op"]}
peso_rc = 0
rc_todo = {}
residuos = Counter()
for p in politicas:
    filas = rc25_op.get(p["id"], [])
    if not filas: continue
    cab = filas[0]
    ops = []
    for r in filas:
        cod = limpiar(r[8])
        cum, act = texto(completo(r[9], literal)), texto(completo(r[10], literal))
        assert "TEXTO COMPLETO" not in cum + act, f"Marcador sin reconstruir en {p['id']} {cod}"
        ops.append({"cod": cod, "nombre": catalogo_op.get((p["id"], cod), ""),
                    "cumplimiento": bloques(cum), "actividades": bloques(act)})
    res, alt = texto(completo(cab[7], literal), resumen=True), texto(completo(cab[11], literal))
    assert "TEXTO COMPLETO" not in res + alt, f"Marcador sin reconstruir en {p['id']}"
    doc = {"id": p["id"], "resumen": bloques(res), "alternativas": bloques(alt), "ops": ops}
    for seccion in [doc["resumen"], doc["alternativas"]] + [o[k] for o in ops for k in ("cumplimiento", "actividades")]:
        for b in seccion: residuos[b[0]] += 1
    archivo = f"rc_{p['n']:03d}.json"
    peso_rc += guardar(f"rc/{archivo}", doc)
    p["rc"] = archivo
    rc_todo[archivo] = doc
print(f"      {len(rc_todo)} reportes, {peso_rc/1024:.0f} KB en total | bloques: {dict(residuos)}")

# ------------------------------------------------------------- 5. agregados
print("[5/6] Agregados")
vals = [p["ispn"] for p in politicas]
sit = Counter(p["situacion"] for p in politicas)
st = sum(p["c3"]["den"] for p in politicas); si = sum(p["c3"]["num"] for p in politicas)
ie = Counter(i["e"] for i in indicadores)
resumen = {
    "politicas": len(politicas), "promedio": round(sum(vals)/len(vals), 1),
    "maximo": max(vals), "minimo": min(vals),
    "baja": sit["Baja"], "media": sit["Media"], "media_alta": sit["Media-alta"], "alta": sit["Alta"],
    "serv_total": st, "serv_impl": si, "pct_serv": round(100*si/st, 1),
    "indicadores": len(indicadores),
    "ind_fav": ie["Favorable"], "ind_nofav": ie["No favorable"], "ind_nd": ie["Sin dato"],
    "ministerios": len({p["ministerio"] for p in politicas}),
}

crit_def = [
    ("C1", "Avance del problema público", "Resultados", "Si el problema que motivó la política mejora hacia la situación futura deseada."),
    ("C2", "Avance de los objetivos prioritarios", "Resultados", "Proporción de indicadores de objetivos prioritarios con resultado favorable."),
    ("C3", "Implementación de los servicios", "Implementación", "Proporción de servicios reportados como implementados o en proceso."),
    ("C4", "Avance de los servicios", "Implementación", "Proporción de indicadores de servicios con resultado favorable."),
    ("C5", "Información para el seguimiento", "Mejora continua", "Proporción de indicadores con información suficiente para medirse."),
    ("C6", "Alternativas de mejora", "Mejora continua", "Si las alternativas propuestas son específicas, viables y con acciones claras."),
]
criterios = []
for i, (c, nom, dim, desc) in enumerate(crit_def):
    vs = [p["criterios"][i] for p in politicas]
    mx = ESCALA_MAX[i]
    criterios.append({"c": c, "nombre": nom, "dimension": dim, "descripcion": desc, "maximo": mx,
                      "promedio": round(sum(vs)/len(vs), 2),
                      "estandar": round(100*sum((v-1)/(mx-1) for v in vs)/len(vs), 1),
                      "dist": [vs.count(k) for k in range(1, mx+1)]})

# ----------------------------------------------------------- 6. verificacion
print("[6/6] Verificacion contra el informe publicado")
pub = {"politicas": 42, "promedio": 40.1, "maximo": 70.8, "minimo": 8.3, "baja": 18, "media": 23, "media_alta": 1, "alta": 0}
fallas = 0
for k, v in pub.items():
    ok = abs(resumen[k] - v) < 0.15 if isinstance(v, float) else resumen[k] == v
    fallas += 0 if ok else 1
    print(f"      {k:<11} {resumen[k]!s:<7} informe {v!s:<7} {'OK' if ok else 'DIFIERE'}")
dif = [p["etiqueta"] for p in politicas if resumen_x.get(p["id"]) and abs(p["ispn"] - (num(resumen_x[p["id"]][10]) or -1)) > 0.05]
print(f"      ISPN recalculado = ISPN del libro en {42-len(dif)}/42 politicas" + (f" (difieren: {dif})" if dif else ""))
assert fallas == 0, "Las cifras no reproducen el informe publicado"

# Formato compacto: los nombres de OP y servicios se guardan una sola vez por
# politica y cada indicador es una fila posicional (ver ESQUEMA_IND en el tablero).
catalogo = defaultdict(dict)
filas_ind = []
TIPOS = {"OP": 0, "Servicio": 1}
ESTADOS = {"Favorable": 0, "No favorable": 1, "Sin dato": 2}
CAMPOS = ["n", "c", "nm", "t", "op", "ln", "sv", "se", "rs", "lb", "le", "vo", "vp", "e", "ref",
          "lbA", "voS", "leS", "fu", "av", "ti", "es", "pa", "co", "esc"]
for i in indicadores:
    cat = catalogo[i["p"]]
    s = i["s"] or {}
    if i["op"]: cat.setdefault(i["op"], i["opn"])
    if i["sv"]: cat.setdefault(i["sv"], i["svn"])
    if s.get("ln"): cat.setdefault(s["ln"], s["lnn"])
    filas_ind.append([
        pol_por_id[i["p"]]["n"], i["c"], i["nm"], TIPOS[i["t"]], i["op"], s.get("ln", ""), i["sv"],
        i["se"], i["rs"], i["lb"], i["le"], i["vo"], i["vp"], ESTADOS[i["e"]], i["ref"] or "",
        s.get("lb_anio"), s.get("vo", []), s.get("le", []), s.get("fuente", ""),
        s.get("av"), s.get("tipo_ind", ""), s.get("estandar", ""), s.get("parametro", ""),
        s.get("comentario", ""), 1 if i["esc"] else 0,
    ])

# cruce global mejora x meta
cruce = Counter()
for p in politicas:
    for k in ["mejora_alcanza", "mejora_no_alcanza", "retrocede_alcanza", "retrocede_no_alcanza"]:
        cruce[k] += p["meta"][k]
resumen["cruce_meta"] = dict(cruce)

# De los que cumplen la meta sin mejorar: en cuantos la meta 2025 ya estaba alcanzada
# con el valor del anio anterior. Explica el cuadrante sin suponer nada: la meta era
# menos exigente que el nivel ya logrado.
def _meta_previa(i):
    av = (i["s"] or {}).get("av")
    if av is None or av < 100 or i["e"] != "No favorable":
        return False
    vp, le = i["vp"], i["le"]
    if vp is None or le is None:
        return False
    return vp >= le if i["se"].lower().startswith("asc") else vp <= le

resumen["meta_ya_alcanzada"] = sum(1 for i in indicadores if _meta_previa(i))
resumen["con_meta"] = sum(p["meta"]["con_meta"] for p in politicas)
resumen["alcanza_meta"] = sum(p["meta"]["alcanza"] for p in politicas)
resumen["escala_inconsistente"] = sum(1 for i in indicadores if i["esc"])
print(f"      cruce mejora x meta: {dict(cruce)} | escala inconsistente: {resumen['escala_inconsistente']}")

guardar("politicas.json", politicas)
guardar("indicadores.json", {"campos": CAMPOS, "catalogo": {str(pol_por_id[k]["n"]): v for k, v in catalogo.items()},
                             "filas": filas_ind})
guardar("estandares.json", estandares)
guardar("criterios.json", criterios)
guardar("resumen.json", resumen)
# Copia unica con los 42 reportes; la usa empaquetar.py para la version autocontenida.
json.dump(rc_todo, open(os.path.join(RAIZ, "web", "rc_todo.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("listo")
