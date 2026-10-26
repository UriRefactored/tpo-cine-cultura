#!/usr/bin/env python3
"""
limpiar_encc.py
Procesa y limpia la Encuesta Nacional de Consumos Culturales (ENCC 2022-2023).

- Resuelve los saltos de cuestionario (structural missings: personas que no fueron al cine o no juegan videojuegos).
- Convierte variables categóricas a formatos numéricos (binarias, ordinales y One-Hot).
- Estandariza los códigos de no respuesta (9, 99, 999).
- Genera variables agregadas para análisis de audiencias y Machine Learning.
- Produce 'encc_limpia_ml.csv' y 'encc_diccionario_variables.json'.

Uso:
    python3 limpiar_encc.py
"""

import json
import re
import numpy as np
import pandas as pd
from pathlib import Path

ENTRADA = Path("base-datos-encc-2022-2023.csv")
SALIDA_CSV = Path("encc_limpia_ml.csv")
SALIDA_DICC = Path("encc_diccionario_variables.json")

# Mapeos ordinales
MAPA_CINE3_FREQ = {
    "todas o casi todas las semanas": 52.0,
    "todos o casi todas los meses": 12.0,
    "algunas veces al ano": 3.0,
    "algunas veces al año": 3.0,
    "nunca": 0.0,
    "nsnc": np.nan,
    "ns nc": np.nan,
}

MAPA_VJ2_FREQ = {
    "todos o casi todos los dias": 365.0,
    "todos o casi todos los días": 365.0,
    "algunas veces por semana": 104.0,
    "algunas veces al mes": 24.0,
    "algunas veces al ano": 4.0,
    "algunas veces al año": 4.0,
    "nunca": 0.0,
    "nsnc": np.nan,
    "ns nc": np.nan,
}

MAPA_TV17_FREQ = {
    "todos o casi todos los dias": 365.0,
    "todos o casi todos los días": 365.0,
    "algunas veces a la semana": 104.0,
    "algunas veces al mes": 24.0,
    "algunas veces al ano": 4.0,
    "algunas veces al año": 4.0,
    "nunca": 0.0,
    "nsnc": 0.0,
    "ns nc": 0.0,
}

MAPA_EDUCACION = {
    "sin estudios": 0,
    "primarios incompletos": 1,
    "primarios completos": 2,
    "secundarios incompletos": 3,
    "secundarios completos": 4,
    "terciarios incompletos": 5,
    "terciarios completos": 6,
    "universitarios incompletos": 7,
    "universitarios completos": 8,
    "posgrado": 9,
}

MAPA_NSE = {
    "d2e": 1,
    "d1": 2,
    "c3": 3,
    "c2": 4,
    "abc1": 5,
}


def norm_txt(val) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip().lower()
    return re.sub(r"\s+", " ", s)


def limpiar_datos():
    if not ENTRADA.exists():
        raise FileNotFoundError(f"No se encontró el archivo {ENTRADA}")

    print(f"Cargando {ENTRADA}...")
    df = pd.read_csv(ENTRADA, low_memory=False)
    print(f"Filas originales: {len(df)} | Columnas originales: {len(df.columns)}")

    out = pd.DataFrame()

    # 1. Identificadores y Pesos Muestrales
    out["id"] = df["id"].astype(int)
    out["ponderador"] = pd.to_numeric(df["ponderador"], errors="coerce").fillna(1.0)
    out["expansor"] = pd.to_numeric(df["expansor"], errors="coerce").fillna(1)

    # 2. Variables Sociodemográficas
    out["edad"] = pd.to_numeric(df["edad"], errors="coerce")
    mediana_edad = out["edad"].median()
    out["edad"] = out["edad"].fillna(mediana_edad).astype(int)

    # Género: Varón, Mujer, No binario
    genero_norm = df["genero"].apply(norm_txt)
    out["gen_mujer"] = (genero_norm == "mujer").astype(int)
    out["gen_varon"] = (genero_norm == "varon").astype(int) | (genero_norm == "varón").astype(int)
    out["gen_no_binario"] = (genero_norm.str.contains("no binario")).astype(int)

    # Nivel Socioeconómico
    nse_norm = df["niv_socioe"].apply(norm_txt)
    out["nse_orden"] = nse_norm.map(MAPA_NSE).fillna(3).astype(int)
    out["nse_abc1"] = (nse_norm == "abc1").astype(int)
    out["nse_c2_c3"] = nse_norm.isin(["c2", "c3"]).astype(int)
    out["nse_d_e"] = nse_norm.isin(["d1", "d2e"]).astype(int)

    # Nivel Educativo (soc13.1)
    if "soc13.1" in df.columns:
        edu_norm = df["soc13.1"].apply(norm_txt)
        out["nivel_educativo_orden"] = edu_norm.map(MAPA_EDUCACION).fillna(4).astype(int)
        out["edu_universitaria_o_mas"] = (out["nivel_educativo_orden"] >= 7).astype(int)
    else:
        out["nivel_educativo_orden"] = 4
        out["edu_universitaria_o_mas"] = 0

    # Condición de actividad (soc14.1)
    if "soc14.1" in df.columns:
        trabaja = df["soc14.1"].apply(norm_txt).str.contains("trabaj").astype(int)
        out["es_ocupado"] = trabaja
    else:
        out["es_ocupado"] = 1

    # Región
    region_norm = df["region"].apply(norm_txt)
    for reg in ["caba", "gba", "centro", "cuyo", "nea", "noa", "patagonia"]:
        out[f"reg_{reg}"] = (region_norm == reg).astype(int)

    # Tamaño de Aglomerado
    tam_norm = df["tamanio"].apply(norm_txt)
    out["tam_mas_400k"] = tam_norm.str.contains("mas de 400mil|más de 400mil").astype(int)
    out["tam_80k_a_400k"] = tam_norm.str.contains("80mil a 400mil").astype(int)
    out["tam_menos_80k"] = tam_norm.str.contains("menos 80mil").astype(int)

    # 3. Módulo Cine
    cine1_si = (df["cine1"].apply(norm_txt) == "si")
    out["cine_fue_ultimo_ano"] = cine1_si.astype(int)

    # cine3: Frecuencia de asistencia (Ordinal convertida a días/año estimados)
    cine3_norm = df["cine3"].apply(norm_txt)
    cine3_freq = cine3_norm.map(MAPA_CINE3_FREQ)
    # Si no fue al cine -> 0. Si fue al cine y falta respuesta -> mediana de los que fueron (3 visitas al año)
    cine3_freq = np.where(~cine1_si, 0.0, cine3_freq.fillna(3.0))
    out["cine_frecuencia_anual_est"] = cine3_freq

    # cine4: Cantidad de veces que asistió en el año
    cine4_num = pd.to_numeric(df["cine4"], errors="coerce")
    # 999 suele ser no sabe/no contesta
    cine4_num = cine4_num.replace({999: np.nan, 99: np.nan})
    mediana_cine4 = cine4_num[cine1_si].median() if cine1_si.any() else 2.0
    cine4_num = np.where(~cine1_si, 0.0, cine4_num.fillna(mediana_cine4))
    # Winsorize al percentil 99 (evitar errores de tipeo de 100+ veces)
    p99_cine4 = np.percentile(cine4_num, 99) if len(cine4_num) else 20.0
    out["cine_visitas_anuales"] = np.clip(cine4_num, 0, p99_cine4)

    # cine5: Veces que fue a ver películas argentinas
    cine5_num = pd.to_numeric(df["cine5"], errors="coerce").replace({999: np.nan, 99: np.nan})
    cine5_num = np.where(~cine1_si, 0.0, cine5_num.fillna(0.0))
    out["cine_visitas_peliculas_arg"] = np.clip(cine5_num, 0, out["cine_visitas_anuales"])

    # Motivos de no ir al cine (para quienes no fueron)
    cine2_norm = df["cine2"].apply(norm_txt)
    out["cine_no_va_motivo_economico"] = ((~cine1_si) & cine2_norm.str.contains("económico|economico")).astype(int)
    out["cine_no_va_prefiere_casa"] = ((~cine1_si) & cine2_norm.str.contains("casa")).astype(int)
    out["cine_no_va_falta_interes"] = ((~cine1_si) & cine2_norm.str.contains("no le gusta|no le interesa|no le interesan")).astype(int)

    # Géneros de Cine (CINE 7_1 a 7_10) - Corresponden a los generos de TMDB
    mapa_generos_cine = {
        "cine7_1": "cine_g_accion_aventura",
        "cine7_2": "cine_g_ciencia_ficcion",
        "cine7_3": "cine_g_suspenso",
        "cine7_4": "cine_g_terror",
        "cine7_5": "cine_g_drama",
        "cine7_6": "cine_g_comedia",
        "cine7_7": "cine_g_romantico",
        "cine7_8": "cine_g_documental",
        "cine7_9": "cine_g_infantiles",
        "cine7_10": "cine_g_animacion",
        "cine7_11": "cine_g_otro",
    }
    for col_orig, col_nueva in mapa_generos_cine.items():
        if col_orig in df.columns:
            # Si no fue al cine -> 0. Si fue -> valor 1/0
            s = pd.to_numeric(df[col_orig], errors="coerce").fillna(0)
            out[col_nueva] = np.where(cine1_si, (s == 1).astype(int), 0)
        else:
            out[col_nueva] = 0

    # 4. Módulo Videojuegos
    vj1_si = (df["vj1"].apply(norm_txt) == "si")
    out["vj_jugo_ultimo_ano"] = vj1_si.astype(int)

    # vj2: Frecuencia de juego
    vj2_norm = df["vj2"].apply(norm_txt)
    vj2_freq = vj2_norm.map(MAPA_VJ2_FREQ)
    vj2_freq = np.where(~vj1_si, 0.0, vj2_freq.fillna(104.0))  # mediana semanal si falta
    out["vj_frecuencia_anual_est"] = vj2_freq

    # vj3: Dispositivos de juego
    mapa_disp_vj = {
        "vj3_1": "vj_disp_celular",
        "vj3_2": "vj_disp_tablet",
        "vj3_3": "vj_disp_pc_escritorio",
        "vj3_4": "vj_disp_notebook",
        "vj3_5": "vj_disp_consola",
    }
    for col_orig, col_nueva in mapa_disp_vj.items():
        if col_orig in df.columns:
            s = pd.to_numeric(df[col_orig], errors="coerce").fillna(0)
            out[col_nueva] = np.where(vj1_si, (s == 1).astype(int), 0)
        else:
            out[col_nueva] = 0

    # vj4: Modalidad social
    mapa_social_vj = {
        "vj4_1": "vj_modalidad_solo",
        "vj4_2": "vj_modalidad_amigos_presencial",
        "vj4_3": "vj_modalidad_online_conocidos",
        "vj4_4": "vj_modalidad_online_desconocidos",
        "vj4_5": "vj_modalidad_online_amigos",
        "vj4_6": "vj_modalidad_familiares",
    }
    for col_orig, col_nueva in mapa_social_vj.items():
        if col_orig in df.columns:
            s = pd.to_numeric(df[col_orig], errors="coerce").fillna(0)
            out[col_nueva] = np.where(vj1_si, (s == 1).astype(int), 0)
        else:
            out[col_nueva] = 0

    # vj5: Géneros de videojuegos jugados
    mapa_generos_vj = {
        "vj5_1": "vj_g_accion_aventura",
        "vj5_2": "vj_g_simuladores",
        "vj5_3": "vj_g_deportivos",
        "vj5_4": "vj_g_estrategia",
        "vj5_5": "vj_g_rol_rpg",
        "vj5_6": "vj_g_shooters",
        "vj5_7": "vj_g_preguntas",
        "vj5_8": "vj_g_puzzle",
        "vj5_9": "vj_g_novela_visual",
    }
    for col_orig, col_nueva in mapa_generos_vj.items():
        if col_orig in df.columns:
            s = pd.to_numeric(df[col_orig], errors="coerce").fillna(0)
            out[col_nueva] = np.where(vj1_si, (s == 1).astype(int), 0)
        else:
            out[col_nueva] = 0

    # vj6: Cantidad de juegos comprados
    vj6_num = pd.to_numeric(df["vj6"], errors="coerce").replace({999: np.nan, 99: np.nan})
    vj6_num = np.where(~vj1_si, 0.0, vj6_num.fillna(0.0))
    p99_vj6 = np.percentile(vj6_num, 99) if len(vj6_num) else 10.0
    out["vj_juegos_comprados_anual"] = np.clip(vj6_num, 0, p99_vj6)

    # 5. Módulo Televisión y Streaming (Consumo doméstico)
    out["tv_mira_television"] = (df["tv1"].apply(norm_txt) == "si").astype(int)

    # tv15: Géneros de películas y series en streaming
    mapa_streaming_g = {
        "tv15_1": "stream_g_accion_aventura",
        "tv15_2": "stream_g_ciencia_ficcion",
        "tv15_3": "stream_g_suspenso",
        "tv15_4": "stream_g_terror",
        "tv15_5": "stream_g_drama",
        "tv15_6": "stream_g_comedia",
        "tv15_7": "stream_g_romantico",
        "tv15_8": "stream_g_documental",
        "tv15_9": "stream_g_infantiles",
        "tv15_10": "stream_g_realities",
        "tv15_11": "stream_g_animacion",
    }
    for col_orig, col_nueva in mapa_streaming_g.items():
        if col_orig in df.columns:
            s = pd.to_numeric(df[col_orig], errors="coerce").fillna(0)
            out[col_nueva] = (s == 1).astype(int)
        else:
            out[col_nueva] = 0

    # tv17: Frecuencia de ver producciones argentinas en streaming
    tv17_norm = df["tv17"].apply(norm_txt) if "tv17" in df.columns else pd.Series(index=df.index, dtype=object)
    out["stream_freq_cine_arg_anual"] = tv17_norm.map(MAPA_TV17_FREQ).fillna(0.0)

    # 6. Feature Engineering de Audiencias (Interacciones de Alto Valor para ML)
    # Segmentos combinados Cine + Videojuegos
    out["feat_gamer_activo"] = ((out["vj_jugo_ultimo_ano"] == 1) & (out["vj_frecuencia_anual_est"] >= 104)).astype(int)
    out["feat_cinefilo_frecuente"] = ((out["cine_fue_ultimo_ano"] == 1) & (out["cine_visitas_anuales"] >= 6)).astype(int)
    out["feat_gamer_y_cinefilo"] = (out["feat_gamer_activo"] & (out["cine_fue_ultimo_ano"] == 1)).astype(int)

    # Preferencias cruzadas de géneros de acción / animación en cines y videojuegos
    out["feat_interes_accion_ambos"] = (out["cine_g_accion_aventura"] & out["vj_g_accion_aventura"]).astype(int)
    out["feat_interes_animacion_o_infantil"] = (out["cine_g_animacion"] | out["cine_g_infantiles"]).astype(int)

    # Suma de diversidad de consumos
    cols_g_cine = [c for c in out.columns if c.startswith("cine_g_") and c != "cine_g_otro"]
    out["feat_diversidad_generos_cine"] = out[cols_g_cine].sum(axis=1)

    cols_g_vj = [c for c in out.columns if c.startswith("vj_g_")]
    out["feat_diversidad_generos_vj"] = out[cols_g_vj].sum(axis=1)

    cols_g_stream = [c for c in out.columns if c.startswith("stream_g_")]
    out["feat_diversidad_generos_streaming"] = out[cols_g_stream].sum(axis=1)

    # 7. Verificación final de integridad
    nulos_restantes = out.isna().sum().sum()
    tipos_objeto = out.select_dtypes(include=["object"]).columns.tolist()

    if nulos_restantes > 0:
        print(f"ADVERTENCIA: Quedaron {nulos_restantes} nulos. Rellenando con 0...")
        out = out.fillna(0)

    if tipos_objeto:
        raise ValueError(f"Quedaron columnas no numéricas: {tipos_objeto}")

    # Guardar CSV limpio
    out.to_csv(SALIDA_CSV, index=False)
    print(f"\nDataset limpio guardado: {SALIDA_CSV}")
    print(f"Forma final: {out.shape} ({len(out)} encuestados, {len(out.columns)} variables 100% numéricas)")

    # Guardar diccionario de variables
    diccionario = {
        col: {
            "tipo": str(out[col].dtype),
            "min": float(out[col].min()),
            "max": float(out[col].max()),
            "media": round(float(out[col].mean()), 3),
        }
        for col in out.columns
    }
    SALIDA_DICC.write_text(json.dumps(diccionario, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Diccionario guardado: {SALIDA_DICC}")

    return out


if __name__ == "__main__":
    limpiar_datos()
