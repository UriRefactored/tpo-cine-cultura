#!/usr/bin/env python3
"""Reúne en presentacion/datos.json todas las cifras que usa la presentación (leídas de outputs/).

    python presentacion/datos_presentacion.py && node presentacion/construir.js
"""

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import comun as c  # noqa: E402


def t(nombre):
    return pd.read_csv(c.TABLAS / f"{nombre}.csv")


def registros(df):
    return json.loads(df.to_json(orient="records", force_ascii=False))


def main():
    R = json.loads(c.RESUMEN.read_text(encoding="utf-8"))
    desc = t("descriptivos_segmentos")
    trans = t("transformaciones_encc").set_index("variable")["casos_afectados"].to_dict()
    gen_d = t("generos_descriptivos")
    gen_c = t("generos_contrastes")
    test = t("prediccion_test")
    difs = t("prediccion_diferencias_auc")
    imp = t("prediccion_importancia_permutacion")
    vj = t("incaa_adaptaciones_videojuegos")
    top = t("incaa_top10_por_anio")
    rank_mario = int((pd.read_csv(c.RAW_TMDB)["entradas"] > vj.loc[vj["titulo"].str.contains("MARIO"), "entradas"].iloc[0]).sum() + 1)

    datos = {
        "resumen": R,
        "descriptivos": registros(desc),
        "edad": registros(t("asistencia_por_edad_segmento")),
        "ajustada": registros(t("asistencia_probabilidades_ajustadas")),
        "contrastes": registros(t("asistencia_contrastes")),
        "sensibilidad": registros(t("asistencia_sensibilidad")),
        "generos_desc": registros(gen_d),
        "generos_contrastes": registros(gen_c),
        "pred_test": registros(test),
        "pred_difs": registros(difs),
        "importancia": registros(imp.head(8)),
        "adaptaciones": registros(vj),
        "mario_puesto": rank_mario,
        "top10": registros(top),
        "encc_vs_incaa": registros(t("encc_vs_incaa_generos")),
        "cobertura": registros(t("incaa_cobertura_tmdb")),
        "clustering_k": registros(t("clustering_seleccion_k")),
        "clustering_perfiles": registros(t("clustering_perfiles")),
        "transformaciones": trans,
        "calidad": registros(t("calidad_saltos_encc")),
        "auditoria_ok": bool((t("auditoria_fuentes")["resultado"] == "OK").all()),
        "n_controles_auditoria": int(len(t("auditoria_fuentes"))),
    }
    salida = Path(__file__).with_name("datos.json")
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {salida.relative_to(RAIZ)}  (Mario: puesto {rank_mario} de {R['mercado']['estrenos']})")


if __name__ == "__main__":
    main()
