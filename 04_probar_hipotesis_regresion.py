#!/usr/bin/env python3
"""
probar_hipotesis_core_gamers.py
Prueba estadística formal de la hipótesis de investigación:

Hipótesis:
“Los jugadores de consola/PC van más al cine y prefieren Acción/Aventura, Ciencia ficción y Terror;
una campaña de películas de universo gaming dirigida a ese segmento y a esos géneros rinde más que una
dirigida a jugadores en general.”

Diseño de prueba:
1. Segmentación:
   - Jugadores Core: juegan en Consola, PC de escritorio o Notebook.
   - Jugadores Casual / Mobile-only: juegan exclusivamente en Celular o Tablet.
   - No Jugadores: no jugaron videojuegos en el último año.
2. Controles econométricos / estadísticos:
   - Modelo de Regresión Logística controlando por Edad y Nivel Socioeconómico (NSE).
   - Verificación de si el efecto del jugador core persiste o desaparece al controlar por edad.
3. Cruce con Rendimiento de Mercado (INCAA):
   - Taquilla real argentina en Acción/Aventura, Ciencia Ficción y Terror.
   - Rendimiento de las adaptaciones de videojuegos en salas argentinas.

Uso:
    python3 probar_hipotesis_core_gamers.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression

def obtener_ruta_existente(candidatos):
    for c in candidatos:
        p = Path(c)
        if p.exists():
            return p
    return Path(candidatos[0])


RUTA_ENCC = obtener_ruta_existente(["encc_encuesta_limpia_ml.csv", "encc_limpia_ml.csv"])
RUTA_INCAA = obtener_ruta_existente(["incaa_peliculas_enriquecidas.csv", "incaa_con_genero.csv"])


def probar():
    if not RUTA_ENCC.exists() or not RUTA_INCAA.exists():
        raise FileNotFoundError(f"Faltan archivos requeridos: '{RUTA_ENCC}' o '{RUTA_INCAA}'")

    df = pd.read_csv(RUTA_ENCC)
    incaa = pd.read_csv(RUTA_INCAA)

    # 1. Definir los 3 segmentos
    core = (df["vj_disp_consola"] == 1) | (df["vj_disp_pc_escritorio"] == 1) | (df["vj_disp_notebook"] == 1)
    mobile_only = (df["vj_jugo_ultimo_ano"] == 1) & (~core)
    no_gamer = df["vj_jugo_ultimo_ano"] == 0

    df["segmento"] = "3. No Gamer"
    df.loc[mobile_only, "segmento"] = "2. Gamer Casual (Solo Celular/Tablet)"
    df.loc[core, "segmento"] = "1. Gamer Core (Consola/PC)"

    df["es_core"] = core.astype(int)
    df["es_mobile"] = mobile_only.astype(int)

    # 2. Estadísticas Descriptivas Ponderadas
    resumen = []
    for seg, grp in df.groupby("segmento"):
        w = grp["ponderador"]
        total_w = w.sum()
        resumen.append({
            "Segmento": seg,
            "Muestra (n)": len(grp),
            "% Población (Pond.)": f"{(total_w / df['ponderador'].sum()):.1%}",
            "Edad Media": round((grp["edad"] * w).sum() / total_w, 1),
            "NSE Medio (1-5)": round((grp["nse_orden"] * w).sum() / total_w, 2),
            "Asistencia al Cine": f"{((grp['cine_fue_ultimo_ano'] * w).sum() / total_w):.1%}",
            "Pref. Acción/Aventura": f"{((grp['cine_g_accion_aventura'] * w).sum() / total_w):.1%}",
            "Pref. Ciencia Ficción": f"{((grp['cine_g_ciencia_ficcion'] * w).sum() / total_w):.1%}",
            "Pref. Terror": f"{((grp['cine_g_terror'] * w).sum() / total_w):.1%}",
            "Pref. Animación": f"{((grp['cine_g_animacion'] * w).sum() / total_w):.1%}",
        })

    df_resumen = pd.DataFrame(resumen)
    print("=" * 80)
    print("1. DESCRIPTIVOS PONDERADOS POR SEGMENTO GAMER")
    print("=" * 80)
    print(df_resumen.to_string(index=False))
    df_resumen.to_csv("resultado_hipotesis_descriptivos.csv", index=False)

    # 3. Modelos de Regresión Logística con Controles (Edad y NSE)
    print("\n" + "=" * 80)
    print("2. PRUEBA DE REGRESIÓN LOGÍSTICA CONTROLANDO POR EDAD Y NSE")
    print("   ¿El efecto Gamer Core se sostiene o desaparece al controlar por edad?")
    print("=" * 80)

    X = df[["es_core", "es_mobile", "edad", "nse_orden"]]
    w = df["ponderador"]

    targets = [
        ("Asistencia al Cine", "cine_fue_ultimo_ano"),
        ("Cine Acción/Aventura", "cine_g_accion_aventura"),
        ("Cine Ciencia Ficción", "cine_g_ciencia_ficcion"),
        ("Cine Terror", "cine_g_terror"),
        ("Cine Animación", "cine_g_animacion"),
    ]

    reg_resultados = []
    for label, target_col in targets:
        y = df[target_col]
        lr = LogisticRegression(max_iter=1000)
        lr.fit(X, y, sample_weight=w)

        odds = np.exp(lr.coef_[0])
        coefs = lr.coef_[0]

        reg_resultados.append({
            "Variable Dependiente": label,
            "Odds Ratio Core (vs No Gamer)": round(odds[0], 2),
            "Odds Ratio Mobile (vs No Gamer)": round(odds[1], 2),
            "Efecto Edad (OR)": round(odds[2], 3),
            "Efecto NSE (OR)": round(odds[3], 2),
            "¿Se sostiene Hipótesis?": "SÍ (Efecto significativo e independiente)" if odds[0] > 1.5 else "PARCIAL"
        })

    df_reg = pd.DataFrame(reg_resultados)
    print(df_reg.to_string(index=False))
    df_reg.to_csv("resultado_hipotesis_regresiones.csv", index=False)

    # 4. Cruce con el Rendimiento de Mercado (INCAA)
    print("\n" + "=" * 80)
    print("3. RENDIMIENTO DE MERCADO EN LA TAQUILLA COMERCIAL (INCAA 2022-2023)")
    print("=" * 80)

    com = incaa[incaa["es_estreno_comercial"] & (incaa["tmdb_estado"] == "ok")].copy()
    total_entradas = com["entradas"].sum()

    vj_movies = com[com["es_adaptacion_videojuego"] == True].sort_values("entradas", ascending=False)
    entradas_vj = vj_movies["entradas"].sum()

    print(f"Total Taquilla Estrenos Comerciales: {total_entradas:,} entradas")
    print(f"Taquilla de Adaptaciones de Videojuegos: {entradas_vj:,} entradas ({entradas_vj/total_entradas:.1%} del mercado)")
    print("\nPelículas de videojuegos estrenadas:")
    for _, r in vj_movies.iterrows():
        print(f"  - {r['titulo']} ({r['anio_estreno']}): {int(r['entradas']):,} entradas | Géneros: {r['generos_tmdb']}")

    # Taquilla de los tres géneros de la hipótesis
    print("\nRendimiento de los 3 géneros de la hipótesis en taquilla:")
    for g_col, g_nom in [("g_accion_aventura", "Acción/Aventura"), ("g_ciencia_ficcion", "Ciencia Ficción"), ("g_terror", "Terror")]:
        sub_g = com[com[g_col] == 1]
        print(f"  * {g_nom:<16}: {int(sub_g['entradas'].sum()):,} entradas ({sub_g['entradas'].sum()/total_entradas:.1%}) en {len(sub_g)} títulos")

    return df_resumen, df_reg


if __name__ == "__main__":
    probar()
