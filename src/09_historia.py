#!/usr/bin/env python3
"""Paso 09 — Página de storytelling (outputs/historia.html).

Una sola página HTML autocontenida que cuenta el análisis en orden, con gráficos interactivos dibujados en SVG
sin librerías externas (funciona sin internet; las fuentes web son opcionales). Todas las cifras se leen de
outputs/: la plantilla (src/historia_plantilla.html) no contiene números escritos a mano.
"""

import datetime as dt
import json
import re

import pandas as pd

import comun as c

PLANTILLA = c.RAIZ / "src/historia_plantilla.html"
SALIDA = c.RAIZ / "outputs/historia.html"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def t(nombre):
    return pd.read_csv(c.TABLAS / f"{nombre}.csv")


def es(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=0):
    return es(100 * x, d) + "%"


def titulo_corto(s):
    s = s.split(":")[0].replace(" LA PELICULA", "").rstrip(".").lower()
    menores = {"at", "de", "a", "la", "el", "del"}
    return " ".join(p if i and p in menores else p.capitalize() for i, p in enumerate(s.split()))


def cuotas(pobl: dict) -> dict:
    """Reparto de 100 butacas por mayor resto (mismo criterio que la página)."""
    raw = {k: v * 100 for k, v in pobl.items()}
    base = {k: int(v) for k, v in raw.items()}
    resto = 100 - sum(base.values())
    for k in sorted(raw, key=lambda k: raw[k] - base[k], reverse=True)[:resto]:
        base[k] += 1
    return base


def main():
    R = json.loads(c.RESUMEN.read_text(encoding="utf-8"))
    desc = t("descriptivos_segmentos").set_index("segmento")
    aj = t("asistencia_probabilidades_ajustadas").set_index("segmento")
    cont = t("asistencia_contrastes")
    gdesc = t("generos_descriptivos")
    gcon = t("generos_contrastes")
    test = t("prediccion_test").set_index(["modelo", "bloque"])
    difs = t("prediccion_diferencias_auc").set_index("comparacion")

    pc_no = cont[(cont["contraste"] == "pc_consola vs no_juega")].set_index("especificacion")
    accion = gdesc[gdesc["genero"] == "accion_aventura"].set_index("segmento")
    d_gam = difs.loc["logistica|3_demo_gaming − logistica|1_demografia", "dif_auc"]
    d_str = difs.loc["logistica|4_demo_gaming_streaming − logistica|3_demo_gaming", "dif_auc"]
    n_sig = int(gcon["significativo_holm_5pct"].sum())
    auc = lambda b: float(test.loc[("logistica", b), "roc_auc"])

    datos = {
        "grupos": {s: {"pob": float(desc.loc[s, "pct_poblacion"]), "asist": float(desc.loc[s, "asistencia"]),
                       "ajust": float(aj.loc[s, "prob_ajustada"]), "edad": float(desc.loc[s, "edad_media"]),
                       "accion_pob": float(accion.loc[s, "pct_en_toda_la_poblacion"]),
                       "accion_asis": float(accion.loc[s, "pct_entre_asistentes"])} for s in c.SEGMENTOS},
        "brecha": {"cruda": float(pc_no.loc["crudo", "dif_pp"]), "ajustada": float(pc_no.loc["completo", "dif_pp"]),
                   "ic": [float(pc_no.loc["completo", "dif_ic_inf"]), float(pc_no.loc["completo", "dif_ic_sup"])]},
        "n_gen": int(len(gcon)), "n_sig": n_sig,
        "auc": [["Solo demografía", auc("1_demografia"), "#9A968C"],
                ["+ videojuegos", auc("3_demo_gaming"), "#B26D0C"],
                ["+ streaming", auc("4_demo_gaming_streaming"), "#2F64B8"]],
        "veredictos": [
            ["H1", "Van más al cine, a igual edad y perfil", f"Sí · +{es(pc_no.loc['completo', 'dif_pp'])} pp", True],
            ["H2", "Prefieren Acción, Ciencia ficción y Terror", "No" if n_sig == 0 else "En parte", False],
            ["H3", "Una campaña dirigida a ellos rinde más", "Sin datos", False],
            ["+", "El gaming ayuda a predecir quién va", "No" if d_gam <= 0.01 else "Sí", False],
        ],
    }

    cu = cuotas({s: datos["grupos"][s]["pob"] for s in c.SEGMENTOS})
    n100 = lambda x: str(round(100 * x))
    sgn = lambda x: ("+" if x >= 0 else "−") + es(abs(x), 3)
    fecha = dt.datetime.fromtimestamp(c.RESUMEN.stat().st_mtime)
    valores = {
        "n": es(R["muestra"]["n"], 0), "localidades": R["muestra"]["localidades"], "estrenos": es(R["mercado"]["estrenos"], 0),
        "pob_pc": cu["pc_consola"], "pob_movil": cu["solo_movil"], "pob_no": cu["no_juega"],
        "asis_pc": n100(desc.loc["pc_consola", "asistencia"]), "asis_movil": n100(desc.loc["solo_movil", "asistencia"]),
        "asis_no": n100(desc.loc["no_juega", "asistencia"]),
        "edad_pc": round(desc.loc["pc_consola", "edad_media"]), "edad_no": round(desc.loc["no_juega", "edad_media"]),
        "brecha_cruda": es(pc_no.loc["crudo", "dif_pp"]), "brecha_ajustada": es(pc_no.loc["completo", "dif_pp"]),
        "accion_pob_pc": n100(accion.loc["pc_consola", "pct_en_toda_la_poblacion"]),
        "accion_pob_no": n100(accion.loc["no_juega", "pct_en_toda_la_poblacion"]),
        "accion_asis_pc": pct(accion.loc["pc_consola", "pct_entre_asistentes"]),
        "accion_asis_no": pct(accion.loc["no_juega", "pct_entre_asistentes"]),
        "n_gen": len(gcon), "gen_sig": "ninguno" if n_sig == 0 else f"{n_sig} de ellos",
        "dif_gaming": sgn(d_gam), "dif_stream": sgn(d_str),
        "fecha": f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}",
    }

    html = PLANTILLA.read_text(encoding="utf-8")
    faltan = set(re.findall(r"{{(\w+)}}", html)) - set(valores)
    if faltan:
        raise ValueError(f"Marcadores sin valor: {sorted(faltan)}")
    for k, v in valores.items():
        html = html.replace("{{" + k + "}}", str(v))
    html = html.replace("/*__DATOS__*/null", json.dumps(datos, ensure_ascii=False))
    cuerpo = '\n<div class="relato">'
    if cuerpo not in html:
        raise ValueError("No encuentro el inicio del cuerpo en la plantilla")
    SALIDA.write_text("<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
                      "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
                      + html.replace(cuerpo, "\n</head>\n<body>" + cuerpo, 1) + "\n</body>\n</html>\n", encoding="utf-8")
    print(f"→ {SALIDA.relative_to(c.RAIZ)} ({SALIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
