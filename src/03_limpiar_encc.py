#!/usr/bin/env python3
"""Paso 03 — Limpieza y transformación de la ENCC 2022/23.

Principios:
- Mapeos estrictos: si aparece una etiqueta no prevista, el script falla (no hay valores por defecto silenciosos).
- Se distingue el "cero estructural" (la pregunta no corresponde por el salto del cuestionario y el valor 0 es
  verdadero, p. ej. quien no jugó no jugó en consola) de la no respuesta (Ns/Nc → NaN, nunca imputada aquí).
- Variables solo definidas para un subuniverso (géneros vistos en el cine) quedan NaN fuera de él.
- Las etiquetas de cada ítem se tomaron del cuestionario oficial (docs/fuentes/encc_2022_23_cuestionario.pdf).

Salidas:
- data/processed/encc_analitica.csv      base analítica (una fila por persona)
- data/processed/diccionario_variables.csv
- outputs/tablas/calidad_saltos_encc.csv  auditoría de saltos y no respuesta por pregunta
- outputs/tablas/transformaciones_encc.csv registro de decisiones con casos afectados
"""

import re

import numpy as np
import pandas as pd

import comun as c

# ---------------------------------------------------------------------------
# Mapeos (etiqueta original exacta → valor). Se valida que cubran todas las etiquetas observadas.
# ---------------------------------------------------------------------------
GENERO = {"Mujer": "mujer", "Varón": "varon", "No binario": "no_binario"}
NSE_ORDEN = {"D2E": 1, "D1": 2, "C3": 3, "C2": 4, "ABC1": 5}
EDUCACION_ORDEN = {
    "Sin Estudios": 0, "Primarios Incompletos": 1, "Primarios Completos": 2,
    "Secundarios Incompletos": 3, "Secundarios Completos": 4, "Terciarios Incompletos": 5,
    "Terciarios Completos": 6, "Universitarios Incompletos": 7, "Universitarios Completos": 8,
    "Posgrado": 9, "Ns Nc": np.nan,
}
# Agrupación para modelos (evita categorías con muy pocos casos)
EDUCACION_GRUPO = {0: "hasta_primario", 1: "hasta_primario", 2: "hasta_primario", 3: "secundario_incompleto",
                   4: "secundario_completo", 5: "superior_incompleto", 7: "superior_incompleto",
                   6: "superior_completo", 8: "superior_completo", 9: "superior_completo"}
ACTIVIDAD = {  # las etiquetas vienen truncadas en la base original
    "Trabajás/trabaja (incluye el trabajo en cooperativas)": "trabaja",
    "No trabajás, sos jubilado/a/ No trabaja, es jubilado/a": "jubilado",
    "No trabajás, sos estudiante/ No trabaja, es estudiante(pasa": "estudiante",
    "No trabajás, sos la/el principal responsable de las tareas d": "tareas_hogar",
    "No trabajas pero buscás trabajo/ No trabaja pero busca traba": "busca_trabajo",
    "Ns/Nc": np.nan,
}
REGION = {r: r.lower() for r in ["CABA", "GBA", "CENTRO", "CUYO", "NEA", "NOA", "PATAGONIA"]}
TAMANIO = {"Mas de 400mil": "mas_400k", "80mil a 400mil": "80k_400k", "Menos 80mil": "menos_80k"}
SI_NO = {"SI": 1, "NO": 0}
CINE3 = {"Todos o casi todas las semanas": "semanal", "Todos o casi todas los meses": "mensual",
         "Algunas veces al año": "algunas_al_anio", "NsNc": np.nan}
VJ2_ORDEN = {"Algunas veces al año": 1, "Algunas veces al mes": 2, "Algunas veces por semana": 3,
             "Todos o casi todos los días": 4}
FREQ_STREAM_ORDEN = {"Nunca": 0, "Algunas veces al año": 1, "Algunas veces al mes": 2,
                     "Algunas veces a la semana": 3, "Todos o casi todos los días": 4, "Ns/Nc": np.nan}

# Ítems de respuesta múltiple. Columna original → nombre nuevo (verificado contra el cuestionario).
CINE7 = {f"cine7_{i}": f"cine_g_{g}" for i, g in enumerate(c.GENEROS_CINE, start=1)} | {"cine7_11": "cine_g_otro"}
VJ3 = {"vj3_1": "vj_disp_celular", "vj3_2": "vj_disp_tablet", "vj3_3": "vj_disp_pc_escritorio",
       "vj3_4": "vj_disp_notebook", "vj3_5": "vj_disp_consola"}
VJ4 = {"vj4_1": "vj_con_solo", "vj4_2": "vj_con_amigos_presencial", "vj4_3": "vj_con_conocidos_online",
       "vj4_4": "vj_con_desconocidos", "vj4_5": "vj_con_amigos_online", "vj4_6": "vj_con_familiares"}
# VJ5: la base trae 12 columnas para los códigos V328–V339; el cuestionario publicado lista 10 ítems y omite
# V329 y V338. La correspondencia se hace por código de variable (vj5_k ↔ V327+k). Evidencia: quienes
# completaron el texto "¿Cuál?" (VJ 5.1) tienen vj5_12 = 1 (Otro) en el 100% de los casos, y vj5_9 (Puzzle,
# "Candy Crush, Tetris") es el ítem más frecuente después de Acción. vj5_11 (V338) está vacía.
VJ5 = {"vj5_1": "vj_g_accion_aventura", "vj5_2": "vj_g_v329_sin_etiqueta", "vj5_3": "vj_g_simuladores",
       "vj5_4": "vj_g_deportivos", "vj5_5": "vj_g_estrategia", "vj5_6": "vj_g_rol", "vj5_7": "vj_g_shooters",
       "vj5_8": "vj_g_preguntas", "vj5_9": "vj_g_puzzle", "vj5_10": "vj_g_novela_visual", "vj5_12": "vj_g_otro"}
TV15 = {f"tv15_{i}": f"stream_g_{g}" for i, g in enumerate(
    ["accion_aventura", "ciencia_ficcion", "suspenso", "terror", "drama", "comedia", "romantico",
     "documental", "infantiles", "realities", "animacion"], start=1)}


def mapear(serie: pd.Series, mapa: dict, nombre: str) -> pd.Series:
    no_previstas = set(serie.dropna().unique()) - set(mapa)
    if no_previstas:
        raise ValueError(f"{nombre}: etiquetas no previstas {sorted(no_previstas)}")
    return serie.map(mapa)


def binaria(serie: pd.Series, nombre: str) -> pd.Series:
    vals = set(serie.dropna().unique())
    if not vals <= {0, 1}:
        raise ValueError(f"{nombre}: valores no binarios {vals}")
    return serie


def conteo(serie: pd.Series, codigos_ns=(99, 999)) -> tuple[pd.Series, pd.Series]:
    """Convierte una pregunta numérica abierta. Devuelve (valor, es_ns_nc)."""
    num = pd.to_numeric(serie.replace({"Ns/Nc": np.nan, "NsNc": np.nan, "Ns Nc": np.nan}), errors="coerce")
    texto_no_numerico = serie.notna() & num.isna() & ~serie.isin(["Ns/Nc", "NsNc", "Ns Nc"])
    if texto_no_numerico.any():
        raise ValueError(f"valores no numéricos inesperados: {serie[texto_no_numerico].unique()[:5]}")
    ns = serie.isin(["Ns/Nc", "NsNc", "Ns Nc"]) | num.isin(codigos_ns)
    return num.mask(ns), ns


def main() -> None:
    c.asegurar_directorios()
    raw = pd.read_csv(c.RAW_ENCC, low_memory=False)
    log = []  # registro de transformaciones

    o = pd.DataFrame(index=raw.index)

    # --- Diseño muestral --------------------------------------------------
    o["id"] = raw["id"]
    o["ponderador"] = raw["ponderador"]
    o["expansor"] = raw["expansor"]
    o["region"] = mapear(raw["region"], REGION, "region")
    o["provincia"] = raw["provincia"]
    o["localidad"] = raw["localidad"]
    o["tamanio"] = mapear(raw["tamanio"], TAMANIO, "tamanio")

    # --- Sociodemografía ------------------------------------------------------
    o["edad"] = raw["edad"].astype(int)
    o["grupo_edad"] = raw["grupos_edad"]
    o["genero"] = mapear(raw["genero"], GENERO, "genero")
    o["es_mujer"] = (o["genero"] == "mujer").astype(int)
    log.append(("genero", "Se usa es_mujer (mujer vs. resto) en los modelos; 'No binario' tiene 1 caso y no permite estimar una categoría propia.", int((o["genero"] == "no_binario").sum())))

    o["nse"] = mapear(raw["niv_socioe"], {k: k for k in NSE_ORDEN}, "niv_socioe")
    o["nse_orden"] = o["nse"].map(NSE_ORDEN)

    o["educacion_orden"] = mapear(raw["soc13.1"], EDUCACION_ORDEN, "soc13.1")
    o["educacion_grupo"] = o["educacion_orden"].map(EDUCACION_GRUPO)
    log.append(("educacion", "Ns/Nc queda como NaN (antes se imputaba 'secundario completo' sin registrarlo).", int(o["educacion_orden"].isna().sum())))

    o["actividad"] = mapear(raw["soc14.1"], ACTIVIDAD, "soc14.1")
    o["ocupado"] = (o["actividad"] == "trabaja").astype(float).mask(o["actividad"].isna())
    viejo_ocupado = raw["soc14.1"].fillna("").str.lower().str.contains("trabaj")
    log.append(("ocupado", "Corrección: la versión anterior buscaba la subcadena 'trabaj' y marcaba como ocupadas también respuestas 'No trabaja…'. Casos que estaban mal clasificados:", int((viejo_ocupado & (o["actividad"] != "trabaja") & o["actividad"].notna()).sum())))
    log.append(("actividad", "Ns/Nc queda como NaN.", int(o["actividad"].isna().sum())))

    # --- Cine -------------------------------------------------------------------
    o["cine_asistio"] = mapear(raw["cine1"], SI_NO, "cine1").astype(int)
    asistio = o["cine_asistio"] == 1

    motivos = raw["cine2"].where(~asistio)
    o["cine_motivo_no_asistir"] = motivos.map(lambda s: np.nan if pd.isna(s) or s == "Ns Nc" else
                                              re.sub(r"[^a-z0-9]+", "_", s.lower().translate(str.maketrans("áéíóúñ", "aeioun"))).strip("_"))
    o["cine_frecuencia"] = mapear(raw["cine3"], CINE3, "cine3")
    o["cine_veces"], ns_cine4 = conteo(raw["cine4"])
    o["cine_veces_peliculas_arg"], ns_cine5 = conteo(raw["cine5"])
    log.append(("cine_veces", "CINE 4 'Ns/Nc' (código 999 o texto) → NaN; sin imputación ni recorte de extremos.", int(ns_cine4.sum())))
    log.append(("cine_veces_peliculas_arg", "CINE 5 código 99/999 → NaN.", int(ns_cine5.sum())))

    for col, nuevo in CINE7.items():
        o[nuevo] = binaria(raw[col], col).where(asistio)  # NaN para quien no asistió (fuera de universo)
    log.append(("cine_g_*", "Géneros vistos en el cine: solo definidos para quien asistió; NaN para el resto (antes se imputaba 0 y se medía 'preferencia' sobre toda la población).", int((~asistio).sum())))

    # --- Videojuegos --------------------------------------------------------------
    o["vj_jugo"] = mapear(raw["vj1"], SI_NO, "vj1").astype(int)
    jugo = o["vj_jugo"] == 1
    o["vj_frecuencia_orden"] = mapear(raw["vj2"], VJ2_ORDEN, "vj2").where(jugo, 0)
    for mapa in (VJ3, VJ4, VJ5):
        for col, nuevo in mapa.items():
            # Cero estructural válido: quien no jugó no jugó en ningún dispositivo, modalidad ni género.
            o[nuevo] = binaria(raw[col], col).where(jugo, 0)
    log.append(("vj_disp_* / vj_con_* / vj_g_*", "Cero estructural para quien no jugó (respuesta verdadera, no imputación).", int((~jugo).sum())))
    log.append(("vj_g_*", "Etiquetas de VJ5 corregidas por código de variable (V328–V339); la versión anterior las desplazaba un lugar (p. ej. llamaba 'novela visual' a Puzzle). vj5_2 (V329) no tiene etiqueta en el cuestionario publicado.", 0))
    comprados, ns_vj6 = conteo(raw["vj6"])
    o["vj_juegos_comprados"] = comprados.where(jugo, 0)
    log.append(("vj_juegos_comprados", "VJ 6 código 99/999 → NaN (el cuestionario define 999 como Ns/Nc; 99 se trata igual por su frecuencia anómala).", int(ns_vj6.sum())))

    o["vj_n_dispositivos"] = o[list(VJ3.values())].sum(axis=1)
    o["vj_n_generos"] = o[[v for v in VJ5.values() if v != "vj_g_otro"]].sum(axis=1)

    pc_consola = (o["vj_disp_consola"] + o["vj_disp_pc_escritorio"] + o["vj_disp_notebook"]) > 0
    movil = (o["vj_disp_celular"] + o["vj_disp_tablet"]) > 0
    o["segmento"] = np.select([~jugo, pc_consola, movil], ["no_juega", "pc_consola", "solo_movil"], default=None)
    o["segmento"] = o["segmento"].replace({None: np.nan})
    log.append(("segmento", "Jugador sin ningún dispositivo declarado: queda sin segmento (no se asume 'solo móvil').", int(o["segmento"].isna().sum())))
    # Definición alternativa para sensibilidad: core = PC de escritorio o consola (sin notebook)
    core_estricto = (o["vj_disp_consola"] + o["vj_disp_pc_escritorio"]) > 0
    o["segmento_sin_notebook"] = np.where(~jugo, "no_juega", np.where(core_estricto, "pc_consola", "otros_jugadores"))
    o.loc[o["segmento"].isna(), "segmento_sin_notebook"] = np.nan

    # --- Televisión y plataformas -------------------------------------------------
    o["tv_mira"] = mapear(raw["tv1"], SI_NO, "tv1").astype(int)
    usa_plat = raw["tv15_1"].notna()  # bloque TV11–TV16 solo para quien miró plataformas (TV 9 = Sí)
    if not (raw[list(TV15)].notna().all(axis=1) == usa_plat).all():
        raise ValueError("TV15: el patrón de salto no es homogéneo entre ítems")
    o["stream_usa_plataformas"] = usa_plat.astype(int)
    o["stream_pago_frecuencia_orden"] = mapear(raw["tv13.1"], FREQ_STREAM_ORDEN, "tv13.1").where(usa_plat, 0)
    o["stream_gratis_frecuencia_orden"] = mapear(raw["tv13.2"], FREQ_STREAM_ORDEN, "tv13.2").where(usa_plat, 0)
    for col, nuevo in TV15.items():
        o[nuevo] = binaria(raw[col], col).where(usa_plat, 0)
    o["stream_n_generos"] = o[list(TV15.values())].sum(axis=1)
    log.append(("stream_*", "Cero estructural para quien no miró plataformas (filtro TV 9).", int((~usa_plat).sum())))

    # --- Controles de consistencia --------------------------------------------------
    assert o["id"].is_unique and len(o) == 3380
    assert (o.loc[~asistio, [v for v in CINE7.values()]].isna().all().all())
    assert (o.loc[o["segmento"] == "pc_consola", ["vj_disp_consola", "vj_disp_pc_escritorio", "vj_disp_notebook"]].sum(axis=1) > 0).all()
    assert o.loc[asistio, "cine_veces"].dropna().ge(1).all(), "Asistentes con 0 visitas declaradas"

    o.to_csv(c.ENCC_LIMPIA, index=False)

    # --- Auditoría de saltos y no respuesta -------------------------------------------
    preguntas = [
        ("CINE 1", "cine1", "toda la muestra", pd.Series(True, index=raw.index), ()),
        ("CINE 2", "cine2", "no asistió al cine", ~asistio, ("Ns Nc",)),
        ("CINE 3", "cine3", "asistió al cine", asistio, ("NsNc",)),
        ("CINE 4", "cine4", "asistió al cine", asistio, ("Ns/Nc",)),
        ("CINE 7 (ítem 1)", "cine7_1", "asistió al cine", asistio, ()),
        ("VJ 1", "vj1", "toda la muestra", pd.Series(True, index=raw.index), ()),
        ("VJ 2", "vj2", "jugó videojuegos", jugo, ()),
        ("VJ 3 (ítem 1)", "vj3_1", "jugó videojuegos", jugo, ()),
        ("VJ 6", "vj6", "jugó videojuegos", jugo, (99, 999)),
        ("TV 15 (ítem 1)", "tv15_1", "miró plataformas (TV 9 = Sí)", usa_plat, ()),
        ("SOC 13.1", "soc13.1", "toda la muestra", pd.Series(True, index=raw.index), ("Ns Nc",)),
        ("SOC 14.1", "soc14.1", "toda la muestra", pd.Series(True, index=raw.index), ("Ns/Nc",)),
    ]
    calidad = []
    for etiqueta, col, universo, mask, codigos_ns in preguntas:
        s = raw[col]
        ns = s.isin(codigos_ns) if codigos_ns else pd.Series(False, index=s.index)
        calidad.append({
            "pregunta": etiqueta, "columna": col, "universo": universo,
            "n_universo": int(mask.sum()),
            "n_respuesta_valida": int((mask & s.notna() & ~ns).sum()),
            "n_ns_nc": int((mask & ns).sum()),
            "n_faltante_en_universo": int((mask & s.isna()).sum()),
            "n_fuera_universo_con_dato": int((~mask & s.notna()).sum()),
            "n_salto_estructural": int((~mask).sum()),
        })
    cal = pd.DataFrame(calidad)
    c.guardar_tabla(cal, "calidad_saltos_encc")
    if (cal["n_faltante_en_universo"] > 0).any() or (cal["n_fuera_universo_con_dato"] > 0).any():
        print("ADVERTENCIA: hay inconsistencias de salto, ver calidad_saltos_encc.csv")

    trans = pd.DataFrame(log, columns=["variable", "decision", "casos_afectados"])
    c.guardar_tabla(trans, "transformaciones_encc")

    # --- Diccionario semántico ------------------------------------------------------------
    c.DICCIONARIO.parent.mkdir(parents=True, exist_ok=True)
    diccionario(o).to_csv(c.DICCIONARIO, index=False)

    # Tamaño efectivo de muestra (Kish) por la dispersión de los ponderadores
    w = o["ponderador"]
    n_ef = w.sum() ** 2 / (w ** 2).sum()
    c.actualizar_resumen("muestra", {
        "n": len(o), "columnas_originales": raw.shape[1], "localidades": int(o["localidad"].nunique()),
        "regiones": int(o["region"].nunique()), "poblacion_expandida": float(o["expansor"].sum()),
        "n_efectivo_kish": round(float(n_ef), 1), "deff_ponderacion": round(len(o) / n_ef, 2),
        "ponderador_min": float(w.min()), "ponderador_max": float(w.max()),
    })
    print(f"Base analítica: {o.shape} → {c.ENCC_LIMPIA.relative_to(c.RAIZ)}")
    print(f"n efectivo (Kish) = {n_ef:.0f} (efecto de diseño por ponderación ≈ {len(o)/n_ef:.2f})")
    print(trans.to_string(index=False))
    print(cal.to_string(index=False))


META = {
    # variable: (origen, pregunta / definición, universo)
    "id": ("id", "Identificador de persona", "todos"),
    "ponderador": ("ponderador", "Coeficiente de corrección muestral (usar para proporciones y modelos)", "todos"),
    "expansor": ("expansor", "Coeficiente de corrección y expansión a totales de población", "todos"),
    "region": ("region", "Región geográfica (estrato del diseño muestral)", "todos"),
    "provincia": ("provincia", "Provincia", "todos"),
    "localidad": ("localidad", "Localidad (unidad primaria de muestreo)", "todos"),
    "tamanio": ("tamanio", "Tamaño de la localidad", "todos"),
    "edad": ("edad", "Edad en años", "todos"),
    "grupo_edad": ("grupos_edad", "Grupo de edad (original)", "todos"),
    "genero": ("genero", "Género declarado", "todos"),
    "es_mujer": ("genero", "1 = mujer", "todos"),
    "nse": ("niv_socioe", "Nivel socioeconómico (5 categorías)", "todos"),
    "nse_orden": ("niv_socioe", "NSE ordinal: 1 = D2E … 5 = ABC1", "todos"),
    "educacion_orden": ("soc13.1", "Máximo nivel educativo, 0 = sin estudios … 9 = posgrado", "todos (Ns/Nc = NaN)"),
    "educacion_grupo": ("soc13.1", "Nivel educativo agrupado en 5 categorías", "todos (Ns/Nc = NaN)"),
    "actividad": ("soc14.1", "Condición de actividad", "todos (Ns/Nc = NaN)"),
    "ocupado": ("soc14.1", "1 = trabaja", "todos (Ns/Nc = NaN)"),
    "cine_asistio": ("cine1", "CINE 1: ¿Fue al cine en el último año? (1 = Sí). Variable objetivo.", "todos"),
    "cine_motivo_no_asistir": ("cine2", "CINE 2: motivo principal por el que no fue", "no asistió"),
    "cine_frecuencia": ("cine3", "CINE 3: frecuencia de asistencia", "asistió"),
    "cine_veces": ("cine4", "CINE 4: cantidad de veces que asistió en el año", "asistió (Ns/Nc = NaN)"),
    "cine_veces_peliculas_arg": ("cine5", "CINE 5: veces que vio películas argentinas", "asistió (Ns/Nc = NaN)"),
    "vj_jugo": ("vj1", "VJ 1: ¿Jugó videojuegos en el último año? (1 = Sí)", "todos"),
    "vj_frecuencia_orden": ("vj2", "VJ 2: frecuencia de juego, 0 = no juega … 4 = casi todos los días", "todos (0 estructural)"),
    "vj_juegos_comprados": ("vj6", "VJ 6: videojuegos comprados en el año", "todos (0 estructural; Ns/Nc = NaN)"),
    "vj_n_dispositivos": ("vj3_*", "Cantidad de dispositivos de juego declarados", "todos"),
    "vj_n_generos": ("vj5_*", "Cantidad de géneros de videojuego declarados (sin 'Otro')", "todos"),
    "segmento": ("vj1, vj3_*", "pc_consola = jugó en consola, PC de escritorio o notebook; solo_movil = jugó solo en celular/tablet; no_juega", "todos (1 jugador sin dispositivo = NaN)"),
    "segmento_sin_notebook": ("vj1, vj3_*", "Sensibilidad: pc_consola = consola o PC de escritorio; otros_jugadores = resto de jugadores", "todos"),
    "tv_mira": ("tv1", "TV 1: ¿Miró televisión? (1 = Sí)", "todos"),
    "stream_usa_plataformas": ("tv15_*", "1 = miró películas/series en plataformas (respondió el bloque TV 11–16)", "todos"),
    "stream_pago_frecuencia_orden": ("tv13.1", "TV 13.1: frecuencia en plataformas pagas, 0 = nunca … 4 = diaria", "todos (0 estructural; Ns/Nc = NaN)"),
    "stream_gratis_frecuencia_orden": ("tv13.2", "TV 13.2: frecuencia en plataformas gratuitas, 0 = nunca … 4 = diaria", "todos (0 estructural; Ns/Nc = NaN)"),
    "stream_n_generos": ("tv15_*", "Cantidad de géneros vistos en plataformas", "todos"),
}
for _col, _n in CINE7.items():
    META[_n] = (_col, f"CINE 7: vio en el cine el género '{_n.removeprefix('cine_g_')}'", "asistió (NaN fuera de universo)")
for _mapa, _preg in ((VJ3, "VJ 3: jugó en"), (VJ4, "VJ 4: jugó"), (VJ5, "VJ 5: jugó género")):
    for _col, _n in _mapa.items():
        META[_n] = (_col, f"{_preg} '{_n.split('_', 2)[-1]}'", "todos (0 estructural)")
for _col, _n in TV15.items():
    META[_n] = (_col, f"TV 15: vio en plataformas el género '{_n.removeprefix('stream_g_')}'", "todos (0 estructural)")


def diccionario(o: pd.DataFrame) -> pd.DataFrame:
    faltan = set(o.columns) - set(META)
    if faltan:
        raise ValueError(f"Variables sin documentar en el diccionario: {sorted(faltan)}")
    filas = []
    for col in o.columns:
        origen, definicion, universo = META[col]
        s = o[col]
        if pd.api.types.is_numeric_dtype(s) and s.nunique() > 12:
            valores = f"{s.min():g} – {s.max():g} (mediana {s.median():g})"
        else:
            valores = "; ".join(f"{k}: {v}" for k, v in s.value_counts().sort_index().items())
        filas.append({"variable": col, "columna_original": origen, "definicion": definicion, "universo": universo,
                      "tipo": str(s.dtype), "n_validos": int(s.notna().sum()), "n_nan": int(s.isna().sum()),
                      "valores": valores})
    return pd.DataFrame(filas)


if __name__ == "__main__":
    main()
