#!/usr/bin/env python3
"""
vincular_encc_incaa.py
Cruza y vincula la demanda cultural (ENCC 2022-2023) con la oferta real de taquilla (INCAA 2022-2023).

Salidas:
1. cruce_encc_incaa_generos.csv   -> Tabla comparativa de % de preferencia en la población vs % de taquilla vendida.
2. cruce_gamers_cine.csv          -> Análisis de penetración de cine y géneros en gamers vs no-gamers.
3. encc_con_contexto_mercado.csv  -> Base individual con métricas macro de taquilla asociadas a los gustos de cada persona.

Uso:
    python3 vincular_encc_incaa.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

def obtener_ruta_existente(candidatos):
    for c in candidatos:
        p = Path(c)
        if p.exists():
            return p
    return Path(candidatos[0])


RUTA_ENCC = obtener_ruta_existente(["encc_encuesta_limpia_ml.csv", "encc_limpia_ml.csv"])
RUTA_INCAA = obtener_ruta_existente(["incaa_peliculas_enriquecidas.csv", "incaa_con_genero.csv"])


def vincular():
    if not RUTA_ENCC.exists() or not RUTA_INCAA.exists():
        raise FileNotFoundError(f"Faltan archivos requeridos: '{RUTA_ENCC}' o '{RUTA_INCAA}'")

    print(f"Cargando {RUTA_ENCC} y {RUTA_INCAA}...")
    encc = pd.read_csv(RUTA_ENCC)
    incaa = pd.read_csv(RUTA_INCAA)

    # Filtrar estrenos comerciales con match ok en INCAA
    incaa_com = incaa[incaa["es_estreno_comercial"] & (incaa["tmdb_estado"] == "ok")].copy()
    total_entradas_incaa = incaa_com["entradas"].sum()

    # Mapeo de columnas de género entre ambos datasets
    generos = [
        ("accion_aventura", "cine_g_accion_aventura", "g_accion_aventura"),
        ("comedia", "cine_g_comedia", "g_comedia"),
        ("ciencia_ficcion", "cine_g_ciencia_ficcion", "g_ciencia_ficcion"),
        ("suspenso", "cine_g_suspenso", "g_suspenso"),
        ("infantiles", "cine_g_infantiles", "g_infantiles"),
        ("animacion", "cine_g_animacion", "g_animacion"),
        ("terror", "cine_g_terror", "g_terror"),
        ("drama", "cine_g_drama", "g_drama"),
        ("romantico", "cine_g_romantico", "g_romantico"),
        ("documental", "cine_g_documental", "g_documental"),
    ]

    # 1. Comparativa Demanda (ENCC) vs Oferta (INCAA) por Género
    peso = encc["ponderador"]
    filtro_asistentes = encc["cine_fue_ultimo_ano"] == 1
    total_asistentes_ponderado = peso[filtro_asistentes].sum()

    tabla_generos = []
    for nombre, col_encc, col_incaa in generos:
        # Demanda ENCC: % de espectadores de cine que eligen este género (ponderado)
        pref_ponderada = (encc[col_encc] * peso)[filtro_asistentes].sum()
        pct_demanda_encc = (pref_ponderada / total_asistentes_ponderado) * 100

        # Oferta INCAA: % de entradas vendidas para películas con este género
        sub_incaa = incaa_com[incaa_com[col_incaa] == 1]
        entradas_genero = sub_incaa["entradas"].sum()
        titulos_genero = len(sub_incaa)
        pct_oferta_incaa = (entradas_genero / total_entradas_incaa) * 100

        # Ratio Taquilla / Preferencia: > 1 indica concentración comercial superior al interés declarado
        ratio_taquilla_interes = round(pct_oferta_incaa / pct_demanda_encc, 2) if pct_demanda_encc > 0 else 0

        tabla_generos.append({
            "genero": nombre,
            "pct_demanda_encc": round(pct_demanda_encc, 1),
            "pct_taquilla_incaa": round(pct_oferta_incaa, 1),
            "titulos_estrenados": titulos_genero,
            "entradas_totales": int(entradas_genero),
            "ratio_taquilla_vs_demanda": ratio_taquilla_interes,
        })

    df_generos = pd.DataFrame(tabla_generos).sort_values("entradas_totales", ascending=False)
    df_generos.to_csv("cruce_demanda_oferta_generos.csv", index=False)
    print("\n[1] Comparación Géneros ENCC vs INCAA generada: cruce_demanda_oferta_generos.csv")
    print(df_generos.to_string(index=False))

    # 2. Análisis Gamers vs Asistencia al Cine y Preferencias
    gamers = encc[encc["vj_jugo_ultimo_ano"] == 1]
    no_gamers = encc[encc["vj_jugo_ultimo_ano"] == 0]

    tasa_cine_gamers = (gamers["cine_fue_ultimo_ano"] * gamers["ponderador"]).sum() / gamers["ponderador"].sum()
    tasa_cine_no_gamers = (no_gamers["cine_fue_ultimo_ano"] * no_gamers["ponderador"]).sum() / no_gamers["ponderador"].sum()

    edad_media_gamers = (gamers["edad"] * gamers["ponderador"]).sum() / gamers["ponderador"].sum()
    edad_media_no_gamers = (no_gamers["edad"] * no_gamers["ponderador"]).sum() / no_gamers["ponderador"].sum()

    # Preferencia por Acción / Animación entre gamers vs no gamers en cines
    accion_gamers = (gamers["cine_g_accion_aventura"] * gamers["ponderador"]).sum() / gamers["ponderador"].sum()
    accion_no_gamers = (no_gamers["cine_g_accion_aventura"] * no_gamers["ponderador"]).sum() / no_gamers["ponderador"].sum()

    anim_gamers = (gamers["cine_g_animacion"] * gamers["ponderador"]).sum() / gamers["ponderador"].sum()
    anim_no_gamers = (no_gamers["cine_g_animacion"] * no_gamers["ponderador"]).sum() / no_gamers["ponderador"].sum()

    df_gamers = pd.DataFrame([
        {
            "segmento": "Gamers (juegan videojuegos)",
            "poblacion_muestral": len(gamers),
            "edad_promedio": round(edad_media_gamers, 1),
            "tasa_asistencia_cine": f"{tasa_cine_gamers:.1%}",
            "pref_cine_accion": f"{accion_gamers:.1%}",
            "pref_cine_animacion": f"{anim_gamers:.1%}",
        },
        {
            "segmento": "No Gamers",
            "poblacion_muestral": len(no_gamers),
            "edad_promedio": round(edad_media_no_gamers, 1),
            "tasa_asistencia_cine": f"{tasa_cine_no_gamers:.1%}",
            "pref_cine_accion": f"{accion_no_gamers:.1%}",
            "pref_cine_animacion": f"{anim_no_gamers:.1%}",
        }
    ])
    df_gamers.to_csv("cruce_gamers_vs_cine.csv", index=False)
    print("\n[2] Segmentación Gamers vs Cine generada: cruce_gamers_vs_cine.csv")
    print(df_gamers.to_string(index=False))

    # 3. Base ENCC enriquecida con features de mercado INCAA
    # A cada individuo le asignamos el tamaño de mercado de sus géneros favoritos
    dict_entradas_genero = dict(zip([g[1] for g in generos], df_generos.set_index("genero")["entradas_totales"]))
    
    # Calcular volumen de taquilla correspondiente a los géneros que consume cada encuestado
    encc_mercado = encc.copy()
    encc_mercado["mkt_volumen_entradas_interes"] = 0
    for col_encc, entradas in dict_entradas_genero.items():
        encc_mercado["mkt_volumen_entradas_interes"] += encc_mercado[col_encc] * entradas

    # Peso relativo de películas de videojuegos en la taquilla de los géneros que ve el individuo
    vj_movies = incaa_com[incaa_com["es_adaptacion_videojuego"] == True]
    entradas_vj_total = vj_movies["entradas"].sum()
    encc_mercado["mkt_exposicion_taquilla_videojuegos"] = np.where(
        encc_mercado["cine_g_accion_aventura"] | encc_mercado["cine_g_animacion"],
        entradas_vj_total / total_entradas_incaa,
        0.0
    )

    encc_mercado.to_csv("encc_con_contexto_mercado.csv", index=False)
    print(f"\n[3] Base ENCC con contexto de mercado guardada: encc_con_contexto_mercado.csv ({encc_mercado.shape})")


if __name__ == "__main__":
    vincular()
