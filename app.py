#!/usr/bin/env python3
"""Demo interactiva del análisis. Todas las cifras se leen de outputs/ (generado por run_all.py).

    streamlit run app.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import comun as c  # noqa: E402
import graficos as g  # noqa: E402
from encuesta import Diseno, proporcion  # noqa: E402

st.set_page_config(page_title="Cine y videojuegos · ENCC 2022/23", page_icon="🎬", layout="wide")

if not c.RESUMEN.exists():
    st.error("Faltan los resultados. Ejecutá primero:  python run_all.py")
    st.stop()

R = json.loads(c.RESUMEN.read_text(encoding="utf-8"))
A = R["asistencia"]


def pct(x, d=1):
    return f"{100 * x:.{d}f}%".replace(".", ",")


def num(x):
    return f"{x:,.0f}".replace(",", ".")


def grafico(fn):
    st.plotly_chart(fn(), width="stretch", config={"displaylogo": False})


def tabla(nombre, **kw):
    df = g.tabla(nombre)
    st.dataframe(df, width="stretch", hide_index=True, **kw)
    st.download_button(f"Descargar {nombre}.csv", df.to_csv(index=False).encode("utf-8"), f"{nombre}.csv", key=nombre)


@st.cache_data
def encc():
    return c.cargar_encc()


# ---------------------------------------------------------------------------------------------------------
st.title("Cine y videojuegos en Argentina")
st.caption("¿Quienes juegan videojuegos van más al cine? ¿Qué agrega el gaming frente a la demografía? · "
           "ENCC 2022/23 (SInCA) + estrenos INCAA 2022–2023 enriquecidos con TMDB")

k1, k2, k3, k4 = st.columns(4)
d = A["descriptiva"]
k1.metric("Asistencia al cine — PC/consola", pct(d["pc_consola"]["asistencia"]),
          help=f"IC 95%: {pct(d['pc_consola']['asistencia_ic_inf'])}–{pct(d['pc_consola']['asistencia_ic_sup'])} · n = {d['pc_consola']['n']}")
k2.metric("Asistencia — no juega", pct(d["no_juega"]["asistencia"]),
          help=f"IC 95%: {pct(d['no_juega']['asistencia_ic_inf'])}–{pct(d['no_juega']['asistencia_ic_sup'])} · n = {d['no_juega']['n']}")
cp = A["contrastes_completo"]["pc_consola vs no_juega"]
k3.metric("Diferencia ajustada", f"+{cp['dif_pp']:.1f} pp".replace(".", ","),
          help=f"IC 95%: {cp['dif_ic_inf']:.1f} a {cp['dif_ic_sup']:.1f} pp · OR {cp['or']:.2f}")
d_gam = R["prediccion"]["auc_test"]["logistica|3_demo_gaming"][0] - R["prediccion"]["auc_test"]["logistica|1_demografia"][0]
k4.metric("Aporte del gaming a la predicción (AUC)", f"{d_gam:+.3f}".replace(".", ","),
          help="Diferencia de ROC-AUC en test entre demografía + gaming y solo demografía (regresión logística).")

tabs = st.tabs(["1 · Datos y universo", "2 · Asistencia", "3 · Géneros", "4 · Predicción", "5 · Mercado", "6 · Límites"])

# ---------------------------------------------------------------------------------------------------------
with tabs[0]:
    m = R["muestra"]
    st.subheader("Universo y fuentes")
    st.markdown(
        f"- **ENCC 2022/23**: {num(m['n'])} personas de 13 años o más en localidades urbanas de más de 30.000 habitantes "
        f"({m['localidades']} localidades, {m['regiones']} regiones). Representa a {num(m['poblacion_expandida'])} personas. "
        f"Trabajo de campo: noviembre 2022 – enero 2023.\n"
        f"- Los ponderadores van de {m['ponderador_min']:.2f} a {m['ponderador_max']:.1f}: el **tamaño efectivo de muestra es ≈ {num(m['n_efectivo_kish'])}** "
        f"(efecto de diseño por ponderación {m['deff_ponderacion']:.2f}). Por eso todas las estimaciones llevan intervalos con el diseño muestral.\n"
        f"- **INCAA**: {num(R['mercado']['estrenos'])} estrenos comerciales 2022–2023, {num(R['mercado']['entradas_total'])} entradas; "
        f"el {pct(R['mercado']['pct_entradas_match_confiable'])} de las entradas tiene un match TMDB confiable.")
    grafico(g.poblacion_segmentos)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Integridad de las fuentes** (hash SHA-256 y controles estructurales)")
        tabla("auditoria_fuentes")
    with c2:
        st.markdown("**Saltos del cuestionario y no respuesta**: cada pregunta solo tiene datos en su universo")
        tabla("calidad_saltos_encc")
    st.markdown("**Decisiones de transformación y casos afectados**")
    tabla("transformaciones_encc")
    with st.expander("Diccionario de variables"):
        st.dataframe(pd.read_csv(c.DICCIONARIO), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------------------------------------
with tabs[1]:
    st.subheader("¿Quienes juegan van más al cine?")
    grafico(g.asistencia_por_edad)
    grafico(g.asistencia_observada_vs_ajustada)
    c1, c2 = st.columns(2)
    with c1:
        grafico(g.forest_asistencia)
    with c2:
        grafico(g.sensibilidad)
    lo, hi = A["sensibilidad_or_rango"]
    st.info(f"Ajustando por edad, NSE, género, educación, actividad, región y tamaño de localidad, quien juega en PC/consola tiene "
            f"{cp['dif_pp']:.1f} puntos porcentuales más de probabilidad de haber ido al cine que quien no juega "
            f"(IC 95%: {cp['dif_ic_inf']:.1f} a {cp['dif_ic_sup']:.1f}). En ocho variantes del análisis el odds ratio queda entre "
            f"{lo:.2f} y {hi:.2f}. Es una **asociación**: la encuesta no permite afirmar que jugar cause ir al cine.")

    st.markdown("#### Explorador: asistencia por segmento dentro de un subgrupo")
    df = encc()
    df = df[df["segmento"].notna()]
    corte = st.selectbox("Cortar por", ["region", "nse", "genero", "tamanio", "educacion_grupo"],
                         format_func={"region": "Región", "nse": "Nivel socioeconómico", "genero": "Género",
                                      "tamanio": "Tamaño de localidad", "educacion_grupo": "Nivel educativo"}.get)
    niveles = sorted(df[corte].dropna().unique())
    nivel = st.selectbox("Subgrupo", niveles)
    dis = Diseno.desde(df)
    filas = []
    for s in c.SEGMENTOS:
        r = proporcion(df["cine_asistio"], dis, ((df[corte] == nivel) & (df["segmento"] == s)).to_numpy())
        filas.append({"Segmento": c.ETIQUETA_SEGMENTO[s], "Fue al cine": pct(r["estimacion"]),
                      "IC 95%": f"{pct(r['ic_inf'])} – {pct(r['ic_sup'])}", "n muestral": r["n"],
                      "Advertencia": "muestra chica (< 50): impreciso" if r["n"] < 50 else ""})
    st.dataframe(pd.DataFrame(filas), width="stretch", hide_index=True)
    st.caption("Estimación ponderada con IC por diseño muestral, sin ajuste por otras variables.")

# ---------------------------------------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Entre quienes fueron al cine, ¿qué géneros vieron?")
    grafico(g.generos_poblacion_vs_asistentes)
    grafico(g.generos_diferencias)
    sig = R["generos"]["significativos_holm"]
    st.warning(
        f"Sobre {num(R['generos']['n_asistentes'])} asistentes, **ningún género** muestra una diferencia significativa entre quienes juegan en "
        f"PC/consola y quienes no juegan después de corregir por 10 comparaciones (Holm)." if not sig else
        f"Géneros con diferencia significativa tras Holm: {', '.join(sig)}.")
    tabla("generos_contrastes")

# ---------------------------------------------------------------------------------------------------------
with tabs[3]:
    st.subheader("¿Cuánto ayuda el gaming a predecir quién va al cine?")
    p = R["prediccion"]
    st.markdown(f"Entrenamiento {num(p['n_train'])} · test {num(p['n_test'])} (reservado, usado una sola vez). "
                "Validación cruzada 5 × 3 para elegir hiperparámetros; métricas ponderadas por el diseño. "
                "Se predice **asistencia pasada**: no es un modelo de respuesta a campañas.")
    grafico(g.auc_por_bloque)
    c1, c2 = st.columns(2)
    with c1:
        grafico(g.curvas_roc)
    with c2:
        grafico(g.calibracion)
    grafico(g.importancia)
    st.markdown("**Métricas completas en test** (umbral elegido en entrenamiento maximizando F1)")
    tabla("prediccion_test")
    st.markdown("**Diferencias de AUC con IC 95% (bootstrap por localidad)**")
    tabla("prediccion_diferencias_auc")

# ---------------------------------------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Contexto de mercado (agregado, no individual)")
    mk = R["mercado"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas de estrenos comerciales 2022–2023", num(mk["entradas_total"]))
    c2.metric("Adaptaciones de videojuegos", f"{mk['adaptaciones_vj']} títulos", help=f"{num(mk['entradas_vj'])} entradas")
    c3.metric("Participación de esas adaptaciones", pct(mk["pct_entradas_vj"]))
    grafico(g.cronologia_videojuegos)
    grafico(g.encc_vs_incaa)
    st.caption(f"Las participaciones por género suman {pct(mk['suma_pct_generos_2022_2023'], 0)} porque TMDB asigna varios géneros por película.")
    with st.expander("Cobertura del enriquecimiento TMDB"):
        tabla("incaa_cobertura_tmdb")
    with st.expander("Top 10 de estrenos por año"):
        tabla("incaa_top10_por_anio")

# ---------------------------------------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Límites")
    st.markdown(
        "- **Asociación, no causalidad.** Encuesta transversal; puede haber variables no medidas (p. ej. ingreso del hogar, interés "
        "general por el entretenimiento) que expliquen parte de la diferencia.\n"
        "- **Diseño muestral aproximado.** Se usan estrato = región y UPM = localidad; la base no trae radios censales. CABA tiene una "
        "única localidad y allí se usan las personas como unidades de varianza.\n"
        "- **Pocos jugadores de PC/consola mayores de 50** (35 casos): la comparación en esas edades es imprecisa.\n"
        "- **Géneros declarados vs. catálogo.** La ENCC registra cómo la persona clasifica lo que vio; TMDB, el catálogo. No son la misma medida.\n"
        "- **INCAA.** El export crudo de Tableau no está disponible y no está documentada la fecha de corte de los acumulados de entradas.\n"
        "- **Predicción retrospectiva.** Clasifica asistencia ya ocurrida; no estima respuesta a publicidad ni retorno de campañas.")
