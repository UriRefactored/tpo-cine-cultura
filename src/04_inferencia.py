#!/usr/bin/env python3
"""Paso 04 — Análisis descriptivo e inferencial con diseño muestral.

Preguntas:
  P1. ¿Cómo cambia la asistencia al cine entre quienes juegan en PC/consola, quienes juegan solo en el
      celular/tablet y quienes no juegan?
  P2. ¿La diferencia se sostiene al ajustar por características sociodemográficas?
  P3. Entre quienes fueron al cine, ¿difieren los géneros que vieron?

Especificaciones fijadas antes de estimar:
  - Crudo:      cine_asistio ~ segmento
  - Edad + NSE: + spline cúbico de edad (4 gl) + NSE categórico
  - Completo:   + género + nivel educativo + condición de actividad + región + tamaño de localidad
Resultados en odds ratio y en probabilidades ajustadas (estandarización marginal) con diferencias en puntos
porcentuales. Géneros: familia de 10 contrastes PC/consola vs. no juega, con corrección de Holm.
"""

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

import comun as c
from encuesta import Diseno, logit, proporcion

REF = "C(segmento, Treatment('no_juega'))"
COV_EDAD_NSE = "bs(edad, df=4) + C(nse, Treatment('C3'))"
COV_COMPLETO = (COV_EDAD_NSE + " + es_mujer + C(educacion_grupo, Treatment('secundario_completo'))"
                " + C(actividad, Treatment('trabaja')) + C(region, Treatment('centro')) + C(tamanio)")
ESPECIFICACIONES = {
    "crudo": f"cine_asistio ~ {REF}",
    "edad_nse": f"cine_asistio ~ {REF} + {COV_EDAD_NSE}",
    "completo": f"cine_asistio ~ {REF} + {COV_COMPLETO}",
}


def coef_segmento(m, nivel):
    return f"{REF}[T.{nivel}]"


def vector(m, nivel_a, nivel_b=None):
    v = np.zeros(len(m.params))
    v[list(m.params.index).index(coef_segmento(m, nivel_a))] = 1
    if nivel_b:
        v[list(m.params.index).index(coef_segmento(m, nivel_b))] = -1
    return v


def contrastes(m, muestra, especificacion, desenlace):
    filas = []
    for a, b in [("pc_consola", "no_juega"), ("solo_movil", "no_juega"), ("pc_consola", "solo_movil")]:
        orc = m.contraste(vector(m, a) if b == "no_juega" else vector(m, a, b))
        dif = m.diferencia_ajustada(muestra, "segmento", a, b)
        filas.append({"desenlace": desenlace, "especificacion": especificacion, "contraste": f"{a} vs {b}",
                      **orc, **dif, "n": m.n})
    return filas


def main():
    df = c.cargar_encc()
    df = df[df["segmento"].notna()].copy()  # 1 jugador sin dispositivo declarado
    dis = Diseno.desde(df)
    c.actualizar_resumen("diseno", {"gl": dis.gl, "upm": int(df["localidad"].nunique()), "estratos": int(df["region"].nunique())})

    # ------------------------------------------------------------------ descriptivos
    desc = []
    tot_w = df["ponderador"].sum()
    for seg in c.SEGMENTOS:
        d = (df["segmento"] == seg).to_numpy()
        g = df[d]
        r = proporcion(df["cine_asistio"], dis, d)
        pob = proporcion(pd.Series(d.astype(float), index=df.index), dis)
        desc.append({
            "segmento": seg, "etiqueta": c.ETIQUETA_SEGMENTO[seg], "n": int(d.sum()),
            "pct_poblacion": pob["estimacion"], "pct_poblacion_ic_inf": pob["ic_inf"], "pct_poblacion_ic_sup": pob["ic_sup"],
            "personas_expandidas": float(g["expansor"].sum()),
            "edad_media": float(np.average(g["edad"], weights=g["ponderador"])),
            "pct_menores_30": float(np.average(g["edad"] < 30, weights=g["ponderador"])),
            "pct_abc1_c2": float(np.average(g["nse"].isin(["ABC1", "C2"]), weights=g["ponderador"])),
            "pct_mujer": float(np.average(g["es_mujer"], weights=g["ponderador"])),
            "asistencia": r["estimacion"], "asistencia_ic_inf": r["ic_inf"], "asistencia_ic_sup": r["ic_sup"],
            "n_asistentes": int(g["cine_asistio"].sum()),
        })
    general = proporcion(df["cine_asistio"], dis)
    desc.append({"segmento": "total", "etiqueta": "Total", "n": len(df), "pct_poblacion": 1.0,
                 "personas_expandidas": float(df["expansor"].sum()),
                 "edad_media": float(np.average(df["edad"], weights=df["ponderador"])),
                 "pct_menores_30": float(np.average(df["edad"] < 30, weights=df["ponderador"])),
                 "pct_abc1_c2": float(np.average(df["nse"].isin(["ABC1", "C2"]), weights=df["ponderador"])),
                 "pct_mujer": float(np.average(df["es_mujer"], weights=df["ponderador"])),
                 "asistencia": general["estimacion"], "asistencia_ic_inf": general["ic_inf"],
                 "asistencia_ic_sup": general["ic_sup"], "n_asistentes": int(df["cine_asistio"].sum())})
    desc = pd.DataFrame(desc)
    c.guardar_tabla(desc, "descriptivos_segmentos")

    # Asistencia por grupo de edad y segmento (comparación "dentro de la misma edad", sin modelo)
    df["tramo_edad"] = pd.cut(df["edad"], [12, 17, 29, 39, 49, 99], labels=["13–17", "18–29", "30–39", "40–49", "50+"])
    filas = []
    for tramo in df["tramo_edad"].cat.categories:
        for seg in c.SEGMENTOS:
            d = ((df["tramo_edad"] == tramo) & (df["segmento"] == seg)).to_numpy()
            r = proporcion(df["cine_asistio"], dis, d)
            filas.append({"tramo_edad": tramo, "segmento": seg, "asistencia": r["estimacion"],
                          "ic_inf": r["ic_inf"], "ic_sup": r["ic_sup"], "n": r["n"], "muestra_chica": r["n"] < 50})
    c.guardar_tabla(pd.DataFrame(filas), "asistencia_por_edad_segmento")

    # ------------------------------------------------------------------ modelos de asistencia
    muestra = df.dropna(subset=["educacion_grupo", "actividad"]).copy()
    tablas_or, cont = [], []
    for nombre, f in ESPECIFICACIONES.items():
        m = logit(f, muestra)
        t = m.tabla()
        t.insert(0, "especificacion", nombre)
        tablas_or.append(t)
        cont += contrastes(m, muestra, nombre, "asistencia")
        if nombre == "completo":
            modelo_completo = m
    c.guardar_tabla(pd.concat(tablas_or), "asistencia_modelos_coeficientes")
    cont = pd.DataFrame(cont)
    c.guardar_tabla(cont, "asistencia_contrastes")

    prob = []
    for seg in c.SEGMENTOS:
        p, g = modelo_completo.prob_ajustada(muestra, "segmento", seg)
        se = float(np.sqrt(g @ modelo_completo.cov.values @ g))
        t = dis.t_crit()
        prob.append({"segmento": seg, "prob_ajustada": p, "ic_inf": p - t * se, "ic_sup": p + t * se})
    c.guardar_tabla(pd.DataFrame(prob), "asistencia_probabilidades_ajustadas")

    # ------------------------------------------------------------------ sensibilidad
    sens = []
    base = ESPECIFICACIONES["completo"]
    variantes = [
        ("Principal (diseño completo)", base, muestra, {}),
        ("Sin ponderar", base, muestra, {"ponderar": False}),
        ("Varianza: solo conglomerado por localidad", base, muestra, {"diseno": "solo_upm"}),
        ("Varianza: robusta por persona (sin diseño)", base, muestra, {"diseno": "iid"}),
        ("Edad lineal y NSE ordinal (especificación original)",
         f"cine_asistio ~ {REF} + edad + nse_orden", muestra, {}),
        ("Solo 13 a 49 años (zona con jugadores de PC/consola)", base, muestra[muestra["edad"] <= 49], {}),
        ("Ponderadores recortados al percentil 99", base,
         muestra.assign(ponderador=muestra["ponderador"].clip(upper=muestra["ponderador"].quantile(0.99))), {}),
    ]
    for etiqueta, f, datos, kw in variantes:
        m = logit(f, datos, **kw)
        r = m.contraste(vector(m, "pc_consola"))
        dif = m.diferencia_ajustada(datos, "segmento", "pc_consola", "no_juega")
        sens.append({"variante": etiqueta, "n": m.n, **r, **dif})
    # Definición alternativa de segmento (core sin notebook)
    alt = muestra.assign(segmento=muestra["segmento_sin_notebook"].replace({"otros_jugadores": "solo_movil"}))
    m = logit(base, alt)
    sens.append({"variante": "Segmento PC/consola sin notebook (notebook pasa a 'otros jugadores')", "n": m.n,
                 **m.contraste(vector(m, "pc_consola")), **m.diferencia_ajustada(alt, "segmento", "pc_consola", "no_juega")})
    sens = pd.DataFrame(sens)
    c.guardar_tabla(sens, "asistencia_sensibilidad")

    # ------------------------------------------------------------------ géneros entre asistentes
    asis = muestra[muestra["cine_asistio"] == 1].copy()
    dis_a = Diseno.desde(asis)
    gen_desc, gen_cont = [], []
    for g in c.GENEROS_CINE:
        col = f"cine_g_{g}"
        for seg in c.SEGMENTOS:
            r = proporcion(asis[col], dis_a, (asis["segmento"] == seg).to_numpy())
            # consumo en toda la población (lo que medía la versión anterior): asistió × vio el género
            pob = proporcion(df[col].fillna(0), dis, (df["segmento"] == seg).to_numpy())
            gen_desc.append({"genero": g, "etiqueta": c.ETIQUETA_GENERO[g], "segmento": seg,
                             "pct_entre_asistentes": r["estimacion"], "ic_inf": r["ic_inf"], "ic_sup": r["ic_sup"],
                             "n_asistentes": r["n"], "pct_en_toda_la_poblacion": pob["estimacion"]})
        f = f"{col} ~ {REF} + bs(edad, df=3) + C(nse, Treatment('C3')) + es_mujer + C(educacion_grupo, Treatment('secundario_completo')) + C(region, Treatment('centro'))"
        m = logit(f, asis)
        r = m.contraste(vector(m, "pc_consola"))
        dif = m.diferencia_ajustada(asis, "segmento", "pc_consola", "no_juega")
        r_m = m.contraste(vector(m, "pc_consola", "solo_movil"))
        gen_cont.append({"genero": g, "etiqueta": c.ETIQUETA_GENERO[g], "n": m.n, "casos": int(asis[col].sum()),
                         **r, "dif_pp": dif["dif_pp"], "dif_ic_inf": dif["dif_ic_inf"], "dif_ic_sup": dif["dif_ic_sup"],
                         "or_vs_movil": r_m["or"], "p_vs_movil": r_m["p_valor"]})
    gen_cont = pd.DataFrame(gen_cont)
    gen_cont["p_holm"] = multipletests(gen_cont["p_valor"], method="holm")[1]
    gen_cont["significativo_holm_5pct"] = gen_cont["p_holm"] < 0.05
    c.guardar_tabla(pd.DataFrame(gen_desc), "generos_descriptivos")
    c.guardar_tabla(gen_cont, "generos_contrastes")

    # ------------------------------------------------------------------ resumen
    principal = cont[(cont["especificacion"] == "completo")].set_index("contraste")
    c.actualizar_resumen("asistencia", {
        "descriptiva": desc.set_index("segmento")[["n", "asistencia", "asistencia_ic_inf", "asistencia_ic_sup", "pct_poblacion", "edad_media"]].to_dict("index"),
        "ajustada": pd.DataFrame(prob).set_index("segmento").to_dict("index"),
        "contrastes_completo": principal[["or", "or_ic_inf", "or_ic_sup", "p_valor", "dif_pp", "dif_ic_inf", "dif_ic_sup"]].to_dict("index"),
        "n_modelo": int(modelo_completo.n),
        "sensibilidad_or_rango": [float(sens["or"].min()), float(sens["or"].max())],
    })
    c.actualizar_resumen("generos", {
        "n_asistentes": int(len(asis)),
        "significativos_holm": gen_cont.loc[gen_cont["significativo_holm_5pct"], "genero"].tolist(),
        "p_min_sin_ajustar": float(gen_cont["p_valor"].min()),
    })

    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(desc[["segmento", "n", "pct_poblacion", "edad_media", "asistencia", "asistencia_ic_inf", "asistencia_ic_sup"]].round(3).to_string(index=False))
    print(cont[["especificacion", "contraste", "or", "or_ic_inf", "or_ic_sup", "p_valor", "dif_pp", "dif_ic_inf", "dif_ic_sup"]].round(3).to_string(index=False))
    print(sens[["variante", "n", "or", "or_ic_inf", "or_ic_sup", "dif_pp"]].round(3).to_string(index=False))
    print(gen_cont[["genero", "casos", "or", "or_ic_inf", "or_ic_sup", "p_valor", "p_holm", "dif_pp", "or_vs_movil", "p_vs_movil"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
