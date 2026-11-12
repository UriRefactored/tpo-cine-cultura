#!/usr/bin/env python3
"""Paso 07 — Contexto de mercado: taquilla INCAA 2022–2023 enriquecida con TMDB.

Este bloque es contexto agregado. No identifica a los compradores de entradas ni se vincula persona a persona
con la ENCC. Tres cuidados explícitos:
1. Una película puede tener varios géneros en TMDB: la participación por género se calcula sobre el total de
   entradas y por eso la suma de géneros supera el 100%.
2. Cobertura: se informa qué parte de las entradas tiene un match TMDB confiable (alta/media) y se usa solo esa.
3. Cronología: la ENCC pregunta por el "último año" a personas encuestadas entre nov-2022 y ene-2023. Las
   películas estrenadas después no pueden haber sido vistas por esas personas. La comparación con la encuesta
   usa solo los estrenos de 2022.
"""

import numpy as np
import pandas as pd

import comun as c
from encuesta import Diseno, proporcion

CONFIABLE = ["alta", "media"]


def main():
    inc = pd.read_csv(c.RAW_TMDB, parse_dates=["fecha_estreno"])
    total = inc["entradas"].sum()

    # ------------------------------------------------------------------ cobertura del enriquecimiento
    inc["calidad_match"] = np.select(
        [inc["tmdb_estado"].eq("no_buscado"), inc["tmdb_estado"].eq("sin_resultados"),
         inc["tmdb_confianza"].isin(CONFIABLE), inc["tmdb_confianza"].eq("baja")],
        ["no buscado (< 1.000 entradas)", "sin resultados en TMDB", "match confiable (alta/media)", "match dudoso (baja)"],
        "otro")
    cob = inc.groupby("calidad_match").agg(titulos=("codigo", "size"), entradas=("entradas", "sum")).reset_index()
    cob["pct_titulos"] = cob["titulos"] / len(inc)
    cob["pct_entradas"] = cob["entradas"] / total
    c.guardar_tabla(cob.sort_values("entradas", ascending=False), "incaa_cobertura_tmdb")

    ok = inc[inc["tmdb_confianza"].isin(CONFIABLE)].copy()

    # ------------------------------------------------------------------ taquilla por año y origen
    anio = inc.groupby(["anio_estreno", "tipo_origen"]).agg(titulos=("codigo", "size"), entradas=("entradas", "sum")).reset_index()
    c.guardar_tabla(anio, "incaa_taquilla_anio_origen")

    # ------------------------------------------------------------------ participación por género
    filas = []
    for anio_sel, sub in [("2022", ok[ok["anio_estreno"] == 2022]), ("2023", ok[ok["anio_estreno"] == 2023]), ("2022–2023", ok)]:
        tot = sub["entradas"].sum()
        for g in c.GENEROS_CINE:
            s = sub[sub[f"g_{g}"] == 1]
            filas.append({"periodo": anio_sel, "genero": g, "etiqueta": c.ETIQUETA_GENERO[g], "titulos": len(s),
                          "entradas": int(s["entradas"].sum()), "pct_entradas": s["entradas"].sum() / tot})
    gen = pd.DataFrame(filas)
    c.guardar_tabla(gen, "incaa_generos")
    suma_pct = gen[gen["periodo"] == "2022–2023"]["pct_entradas"].sum()

    # Comparación con lo declarado por quienes fueron al cine (ENCC), solo estrenos 2022
    encc = c.cargar_encc()
    asis = encc[encc["cine_asistio"] == 1]
    dis = Diseno.desde(asis)
    comp = []
    for g in c.GENEROS_CINE:
        p = proporcion(asis[f"cine_g_{g}"], dis)
        fila = gen[(gen["periodo"] == "2022") & (gen["genero"] == g)].iloc[0]
        comp.append({"genero": g, "etiqueta": c.ETIQUETA_GENERO[g], "pct_asistentes_que_vieron": p["estimacion"],
                     "ic_inf": p["ic_inf"], "ic_sup": p["ic_sup"], "pct_entradas_2022": fila["pct_entradas"]})
    comp = pd.DataFrame(comp)
    c.guardar_tabla(comp, "encc_vs_incaa_generos")

    # ------------------------------------------------------------------ adaptaciones de videojuegos
    vj = inc[inc["es_adaptacion_videojuego"] == True].copy()  # noqa: E712
    vj["respecto_campo_encc"] = np.where(vj["fecha_estreno"] < c.CAMPO_INICIO, "antes del trabajo de campo",
                                         np.where(vj["fecha_estreno"] <= c.CAMPO_FIN, "durante", "después del trabajo de campo"))
    vj["pct_entradas_del_anio"] = vj.apply(lambda r: r["entradas"] / inc.loc[inc["anio_estreno"] == r["anio_estreno"], "entradas"].sum(), axis=1)
    vj = vj.sort_values("fecha_estreno")[["titulo", "fecha_estreno", "anio_estreno", "entradas", "pct_entradas_del_anio",
                                          "generos_tmdb", "tmdb_confianza", "respecto_campo_encc"]]
    c.guardar_tabla(vj, "incaa_adaptaciones_videojuegos")

    top = (inc.sort_values("entradas", ascending=False).groupby("anio_estreno").head(10)
           [["anio_estreno", "titulo", "tipo_origen", "entradas", "generos_tmdb", "es_adaptacion_videojuego"]])
    c.guardar_tabla(top, "incaa_top10_por_anio")

    c.actualizar_resumen("mercado", {
        "estrenos": len(inc), "entradas_total": int(total),
        "entradas_por_anio": inc.groupby("anio_estreno")["entradas"].sum().astype(int).to_dict(),
        "pct_entradas_match_confiable": float(ok["entradas"].sum() / total),
        "titulos_match_confiable": len(ok),
        "suma_pct_generos_2022_2023": float(suma_pct),
        "adaptaciones_vj": len(vj), "entradas_vj": int(vj["entradas"].sum()),
        "pct_entradas_vj": float(vj["entradas"].sum() / total),
        "vj_antes_del_campo": vj.loc[vj["respecto_campo_encc"] == "antes del trabajo de campo", "titulo"].tolist(),
    })
    pd.set_option("display.width", 200)
    print(cob.to_string(index=False))
    print(gen[gen["periodo"] == "2022–2023"].round(3).to_string(index=False), f"\nSuma de % por género: {suma_pct:.0%}")
    print(comp.round(3).to_string(index=False))
    print(vj.to_string(index=False))


if __name__ == "__main__":
    main()
