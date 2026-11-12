"""Figuras del proyecto. Una sola fuente para la app (Streamlit) y para los PNG de las diapositivas.

Todas las funciones leen exclusivamente de outputs/tablas/ (ningún número se escribe a mano).
Colores: paleta categórica validada (slot 1 azul, slot 2 naranja) para los dos segmentos de jugadores y gris
neutro para el grupo de referencia; tinta de texto separada del color de las series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import comun as c

AZUL, NARANJA, AQUA, VIOLETA = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
GRIS = "#898781"
TINTA, TINTA_2, GRILLA, EJE, SUPERFICIE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
COLOR_SEG = {"pc_consola": AZUL, "solo_movil": NARANJA, "no_juega": GRIS}
ETQ_SEG = c.ETIQUETA_SEGMENTO
NOMBRE_BLOQUE = {"1_demografia": "Demografía", "2_demo_segmento": "+ segmento de juego",
                 "3_demo_gaming": "+ gaming completo", "4_demo_gaming_streaming": "+ streaming"}
NOMBRE_MODELO = {"logistica": "Regresión logística", "random_forest": "Random Forest", "baseline": "Baseline"}
FUENTE_ENCC = "Fuente: ENCC 2022/23 (SInCA). Estimaciones ponderadas; IC 95% con diseño muestral (estrato región, UPM localidad)."


def tabla(nombre: str) -> pd.DataFrame:
    return pd.read_csv(c.TABLAS / f"{nombre}.csv")


def con_leyenda(fig: go.Figure) -> bool:
    return sum(1 for t in fig.data if t.showlegend is not False and t.name) >= 2


def estilo(fig: go.Figure, titulo: str, subtitulo: str = "", fuente: str = FUENTE_ENCC, alto: int = 480) -> go.Figure:
    fig.update_layout(
        title={"text": f"<b>{titulo}</b>" + (f"<br><span style='font-size:13px;color:{TINTA_2}'>{subtitulo}</span>" if subtitulo else ""),
               "x": 0, "xanchor": "left", "y": 1, "yref": "container", "yanchor": "top", "pad": {"t": 24},
               "font": {"size": 19, "color": TINTA}},
        font={"family": "system-ui, -apple-system, Segoe UI, sans-serif", "size": 14, "color": TINTA_2},
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE, height=alto,
        margin={"l": 70, "r": 30, "t": (90 if subtitulo else 60) + (50 if con_leyenda(fig) else 0), "b": 105},
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 0, "font": {"color": TINTA_2}},
        hoverlabel={"bgcolor": "white", "font": {"color": TINTA}},
    )
    fig.update_xaxes(gridcolor=GRILLA, linecolor=EJE, zeroline=False, ticks="")
    fig.update_yaxes(gridcolor=GRILLA, linecolor=EJE, zeroline=False, ticks="")
    if fuente:
        fig.add_annotation(text=fuente, xref="paper", yref="paper", x=0, y=0, yanchor="top", yshift=-72,
                           showarrow=False, xanchor="left", font={"size": 11, "color": GRIS})
    fig.update_traces(cliponaxis=False, selector={"type": "scatter"})
    return fig


def pct(x):
    return f"{100 * x:.1f}%"


# ---------------------------------------------------------------------- universo
def poblacion_segmentos() -> go.Figure:
    d = tabla("descriptivos_segmentos")
    d = d[d["segmento"] != "total"]
    fig = go.Figure()
    for _, r in d.iterrows():
        fig.add_bar(y=[ETQ_SEG[r.segmento]], x=[r.pct_poblacion], orientation="h", marker_color=COLOR_SEG[r.segmento],
                    name=ETQ_SEG[r.segmento], showlegend=False, text=[f"{pct(r.pct_poblacion)}  ·  edad media {r.edad_media:.0f}  ·  n = {r.n:,}".replace(",", ".")],
                    textposition="outside", cliponaxis=False,
                    hovertemplate=f"{ETQ_SEG[r.segmento]}<br>%{{x:.1%}} de la población<br>IC 95%: {pct(r.pct_poblacion_ic_inf)}–{pct(r.pct_poblacion_ic_sup)}<extra></extra>")
    fig.update_xaxes(tickformat=".0%", range=[0, 1.05])
    fig.update_yaxes(autorange="reversed")
    return estilo(fig, "¿Quiénes juegan y en qué?", "Distribución de la población de 13+ años en localidades de más de 30.000 habitantes", alto=340)


# ---------------------------------------------------------------------- P1/P2 asistencia
def asistencia_observada_vs_ajustada() -> go.Figure:
    d = tabla("descriptivos_segmentos").set_index("segmento")
    a = tabla("asistencia_probabilidades_ajustadas").set_index("segmento")
    fig = go.Figure()
    y = [ETQ_SEG[s] for s in c.SEGMENTOS]
    fig.add_scatter(x=[d.loc[s, "asistencia"] for s in c.SEGMENTOS], y=y, mode="markers", name="Observada (cruda)",
                    marker={"size": 13, "color": GRIS, "symbol": "circle-open", "line": {"width": 2.5}},
                    error_x={"type": "data", "symmetric": False, "color": GRIS, "thickness": 2, "width": 0,
                             "array": [d.loc[s, "asistencia_ic_sup"] - d.loc[s, "asistencia"] for s in c.SEGMENTOS],
                             "arrayminus": [d.loc[s, "asistencia"] - d.loc[s, "asistencia_ic_inf"] for s in c.SEGMENTOS]},
                    hovertemplate="%{y}<br>Observada: %{x:.1%}<extra></extra>")
    fig.add_scatter(x=[a.loc[s, "prob_ajustada"] for s in c.SEGMENTOS], y=y, mode="markers+text", name="Ajustada por demografía",
                    marker={"size": 14, "color": AZUL}, text=[pct(a.loc[s, "prob_ajustada"]) for s in c.SEGMENTOS],
                    textposition="top center", textfont={"color": TINTA},
                    error_x={"type": "data", "symmetric": False, "color": AZUL, "thickness": 2, "width": 0,
                             "array": [a.loc[s, "ic_sup"] - a.loc[s, "prob_ajustada"] for s in c.SEGMENTOS],
                             "arrayminus": [a.loc[s, "prob_ajustada"] - a.loc[s, "ic_inf"] for s in c.SEGMENTOS]},
                    hovertemplate="%{y}<br>Ajustada: %{x:.1%}<extra></extra>")
    fig.update_xaxes(tickformat=".0%", range=[0, 0.8], title="Fue al cine en el último año")
    fig.update_yaxes(autorange="reversed")
    return estilo(fig, "La brecha se achica al ajustar, pero no desaparece",
                  "Probabilidad de haber ido al cine: observada vs. ajustada por edad, NSE, género, educación, actividad, región y tamaño de localidad", alto=420)


def asistencia_por_edad() -> go.Figure:
    d = tabla("asistencia_por_edad_segmento")
    fig = go.Figure()
    for s in c.SEGMENTOS:
        g = d[d["segmento"] == s]
        fig.add_scatter(x=g["tramo_edad"], y=g["asistencia"], mode="lines+markers", name=ETQ_SEG[s],
                        line={"color": COLOR_SEG[s], "width": 2},
                        marker={"size": 10, "color": [SUPERFICIE if m else COLOR_SEG[s] for m in g["muestra_chica"]],
                                "line": {"color": COLOR_SEG[s], "width": 2}},
                        customdata=np.c_[g["n"], g["ic_inf"], g["ic_sup"]],
                        hovertemplate=f"{ETQ_SEG[s]}<br>%{{x}} años: %{{y:.1%}}<br>IC 95%: %{{customdata[1]:.1%}}–%{{customdata[2]:.1%}}<br>n = %{{customdata[0]}}<extra></extra>")
    fig.update_yaxes(tickformat=".0%", range=[0, 0.9], title="Fue al cine en el último año")
    fig.update_xaxes(title="Tramo de edad")
    return estilo(fig, "A igual edad, quien juega en PC/consola va más al cine",
                  "Asistencia por tramo de edad. Marcador hueco = menos de 50 casos (estimación imprecisa)")


def forest_asistencia() -> go.Figure:
    d = tabla("asistencia_contrastes")
    orden_esp = {"crudo": "Sin ajustar", "edad_nse": "Edad + NSE", "completo": "Ajuste completo"}
    etq_con = {"pc_consola vs no_juega": "PC/consola vs. no juega", "solo_movil vs no_juega": "Solo móvil vs. no juega",
               "pc_consola vs solo_movil": "PC/consola vs. solo móvil"}
    col_con = {"pc_consola vs no_juega": AZUL, "solo_movil vs no_juega": NARANJA, "pc_consola vs solo_movil": VIOLETA}
    fig = go.Figure()
    for con, etq in etq_con.items():
        g = d[d["contraste"] == con]
        y = [orden_esp[e] for e in g["especificacion"]]
        fig.add_scatter(x=g["or"], y=y, mode="markers", name=etq, marker={"size": 12, "color": col_con[con]},
                        error_x={"type": "data", "symmetric": False, "array": g["or_ic_sup"] - g["or"],
                                 "arrayminus": g["or"] - g["or_ic_inf"], "color": col_con[con], "thickness": 2, "width": 0},
                        offsetgroup=con, orientation="h",
                        customdata=np.c_[g["or_ic_inf"], g["or_ic_sup"], g["dif_pp"], g["p_valor"]],
                        hovertemplate=f"{etq} · %{{y}}<br>OR %{{x:.2f}} (IC %{{customdata[0]:.2f}}–%{{customdata[1]:.2f}})<br>Diferencia ajustada: %{{customdata[2]:+.1f}} pp<br>p = %{{customdata[3]:.4f}}<extra></extra>")
    fig.add_vline(x=1, line_color=EJE, line_width=1.5)
    fig.update_xaxes(type="log", title="Odds ratio de haber ido al cine (escala log; 1 = sin diferencia)", tickvals=[1, 1.5, 2, 3, 4, 6])
    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=list(orden_esp.values()))
    fig.update_layout(scattermode="group")
    return estilo(fig, "La asociación sobrevive al ajuste", "Odds ratios con IC 95% según la especificación del modelo")


def sensibilidad() -> go.Figure:
    d = tabla("asistencia_sensibilidad")
    fig = go.Figure(go.Scatter(x=d["or"], y=d["variante"], mode="markers", marker={"size": 11, "color": AZUL},
                               error_x={"type": "data", "symmetric": False, "array": d["or_ic_sup"] - d["or"],
                                        "arrayminus": d["or"] - d["or_ic_inf"], "color": AZUL, "thickness": 2, "width": 0},
                               customdata=np.c_[d["dif_pp"], d["n"]],
                               hovertemplate="%{y}<br>OR %{x:.2f}<br>Diferencia ajustada %{customdata[0]:+.1f} pp<br>n = %{customdata[1]}<extra></extra>"))
    fig.add_vline(x=1, line_color=EJE, line_width=1.5)
    fig.update_xaxes(type="log", tickvals=[1, 1.5, 2, 3, 4], range=[np.log10(0.9), np.log10(4.2)], title="Odds ratio PC/consola vs. no juega (escala log)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin={"l": 420})
    return estilo(fig, "Robusto a las decisiones de análisis", "Mismo contraste bajo ocho variantes de ponderación, varianza, especificación y definición de segmento", alto=460)


# ---------------------------------------------------------------------- P3 géneros
def generos_diferencias() -> go.Figure:
    d = tabla("generos_contrastes").sort_values("dif_pp")
    sig = d["significativo_holm_5pct"]
    fig = go.Figure(go.Scatter(
        x=d["dif_pp"], y=d["etiqueta"], mode="markers", marker={"size": 12, "color": np.where(sig, AZUL, GRIS)},
        error_x={"type": "data", "symmetric": False, "array": d["dif_ic_sup"] - d["dif_pp"], "arrayminus": d["dif_pp"] - d["dif_ic_inf"],
                 "color": GRIS, "thickness": 2, "width": 0},
        customdata=np.c_[d["p_valor"], d["p_holm"], d["casos"]],
        hovertemplate="%{y}<br>Diferencia ajustada: %{x:+.1f} pp<br>p = %{customdata[0]:.3f} · p Holm = %{customdata[1]:.3f}<br>casos = %{customdata[2]}<extra></extra>"))
    fig.add_vline(x=0, line_color=EJE, line_width=1.5)
    fig.update_xaxes(title="Diferencia en puntos porcentuales (PC/consola − no juega), entre quienes fueron al cine", ticksuffix=" pp")
    n_sig = int(sig.sum())
    titulo = "Ningún género difiere tras corregir por comparaciones múltiples" if n_sig == 0 else f"{n_sig} género(s) difieren tras la corrección de Holm"
    return estilo(fig, titulo, "Diferencias ajustadas por edad, NSE, género, educación y región, con IC 95%. Gris = no significativo (Holm, 5%)", alto=500)


def generos_poblacion_vs_asistentes() -> go.Figure:
    d = tabla("generos_descriptivos")
    d = d[d["genero"].isin(["accion_aventura", "ciencia_ficcion", "terror"])]
    fig = go.Figure()
    for medida, nombre, simbolo in [("pct_en_toda_la_poblacion", "Sobre toda la población (medición anterior)", "circle-open"),
                                    ("pct_entre_asistentes", "Solo entre quienes fueron al cine", "circle")]:
        for s in ("pc_consola", "no_juega"):
            g = d[d["segmento"] == s]
            fig.add_scatter(x=g["etiqueta"], y=g[medida], mode="markers", name=f"{ETQ_SEG[s]} · {nombre}",
                            marker={"size": 13, "color": COLOR_SEG[s], "symbol": simbolo, "line": {"width": 2.5, "color": COLOR_SEG[s]}},
                            offsetgroup=f"{medida}{s}", hovertemplate=f"{ETQ_SEG[s]}<br>%{{x}}: %{{y:.1%}}<br>{nombre}<extra></extra>")
    fig.update_layout(scattermode="group", legend={"orientation": "v", "y": 1, "x": 1.02, "xanchor": "left", "yanchor": "top"})
    fig.update_yaxes(tickformat=".0%", title="Vio el género en el cine")
    return estilo(fig, "Por qué cambió la conclusión sobre géneros",
                  "Medido sobre toda la población, la diferencia refleja sobre todo que unos van más al cine que otros", alto=460)


# ---------------------------------------------------------------------- predicción
def auc_por_bloque() -> go.Figure:
    d = tabla("prediccion_test")
    base = d[d["modelo"] == "baseline"]["roc_auc"].iloc[0]
    d = d[d["modelo"] != "baseline"]
    fig = go.Figure()
    for m, col in (("logistica", AZUL), ("random_forest", NARANJA)):
        g = d[d["modelo"] == m]
        fig.add_scatter(x=[NOMBRE_BLOQUE[b] for b in g["bloque"]], y=g["roc_auc"], mode="markers+lines", name=NOMBRE_MODELO[m],
                        line={"color": col, "width": 2}, marker={"size": 11, "color": col},
                        error_y={"type": "data", "symmetric": False, "array": g["auc_ic_sup"] - g["roc_auc"],
                                 "arrayminus": g["roc_auc"] - g["auc_ic_inf"], "color": col, "thickness": 1.5, "width": 0},
                        offsetgroup=m, hovertemplate="%{x}<br>AUC test %{y:.3f}<extra>" + NOMBRE_MODELO[m] + "</extra>")
    fig.add_hline(y=base, line_color=EJE, line_width=1.5, annotation_text="azar (baseline)", annotation_font_color=GRIS)
    fig.update_layout(scattermode="group")
    fig.update_yaxes(range=[0.45, 0.85], title="ROC-AUC en test (ponderado)")
    return estilo(fig, "El gaming no mejora la predicción; el streaming sí",
                  "Bloques de variables acumulativos. IC 95% por bootstrap de localidades sobre el test (n = 676)",
                  fuente="Fuente: ENCC 2022/23. Métricas ponderadas en el 20% de test, que no se usó para elegir modelos ni variables.", alto=460)


def curvas_roc() -> go.Figure:
    d = tabla("prediccion_curvas_roc")
    fig = go.Figure()
    for b, col in (("1_demografia", GRIS), ("3_demo_gaming", NARANJA), ("4_demo_gaming_streaming", AZUL)):
        g = d[(d["modelo"] == "logistica") & (d["bloque"] == b)]
        fig.add_scatter(x=g["fpr"], y=g["tpr"], mode="lines", name=NOMBRE_BLOQUE[b], line={"color": col, "width": 2},
                        hovertemplate="FPR %{x:.2f} · TPR %{y:.2f}<extra>" + NOMBRE_BLOQUE[b] + "</extra>")
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line={"color": EJE, "width": 1}, showlegend=False, hoverinfo="skip")
    fig.update_xaxes(title="Tasa de falsos positivos", range=[0, 1])
    fig.update_yaxes(title="Tasa de verdaderos positivos", range=[0, 1.02])
    return estilo(fig, "Curvas ROC (regresión logística, test)", fuente="Fuente: ENCC 2022/23. Test final (20%), ponderado.", alto=520)


def calibracion() -> go.Figure:
    d = tabla("prediccion_calibracion")
    g = d[(d["modelo"] == "logistica") & (d["bloque"] == "4_demo_gaming_streaming")]
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", line={"color": EJE, "width": 1}, name="Calibración perfecta", hoverinfo="skip")
    fig.add_scatter(x=g["prob_media_predicha"], y=g["frecuencia_observada"], mode="lines+markers", name="Modelo",
                    line={"color": AZUL, "width": 2}, marker={"size": 10, "color": AZUL},
                    hovertemplate="Predicha %{x:.2f} · Observada %{y:.2f}<extra></extra>")
    fig.update_xaxes(title="Probabilidad predicha (octiles)", range=[0, 1])
    fig.update_yaxes(title="Proporción observada", range=[0, 1])
    return estilo(fig, "Calibración del modelo completo", "Regresión logística con demografía + gaming + streaming, en test (sin ponderar)", fuente="Fuente: ENCC 2022/23. Test final (20%).", alto=480)


def importancia() -> go.Figure:
    d = tabla("prediccion_importancia_permutacion").head(12).iloc[::-1]
    col = {"demografia": GRIS, "gaming": NARANJA, "streaming": AZUL}
    fig = go.Figure()
    for b, nombre in (("demografia", "Demografía"), ("gaming", "Gaming"), ("streaming", "Streaming")):
        g = d[d["bloque"] == b]
        fig.add_bar(x=g["caida_auc_media"], y=g["variable"], orientation="h", name=nombre, marker_color=col[b],
                    error_x={"type": "data", "array": g["caida_auc_desvio"], "color": EJE, "thickness": 1.5, "width": 0},
                    hovertemplate="%{y}<br>Caída de AUC al permutar: %{x:.4f}<extra>" + nombre + "</extra>")
    fig.update_layout(barmode="overlay", bargap=0.35, margin={"l": 240})
    fig.update_yaxes(categoryorder="array", categoryarray=list(d["variable"]))
    fig.update_xaxes(title="Caída media del AUC al permutar la variable (test, 30 repeticiones)")
    return estilo(fig, "Qué variables usa el modelo", "Importancia por permutación (asociación predictiva, no causalidad)", fuente="Fuente: ENCC 2022/23. Regresión logística completa, test final.", alto=520)


# ---------------------------------------------------------------------- mercado
def encc_vs_incaa() -> go.Figure:
    d = tabla("encc_vs_incaa_generos").sort_values("pct_entradas_2022")
    fig = go.Figure()
    for _, r in d.iterrows():
        fig.add_scatter(x=[r.pct_asistentes_que_vieron, r.pct_entradas_2022], y=[r.etiqueta] * 2, mode="lines",
                        line={"color": GRILLA, "width": 3}, showlegend=False, hoverinfo="skip")
    fig.add_scatter(x=d["pct_asistentes_que_vieron"], y=d["etiqueta"], mode="markers", name="% de asistentes que lo vio (ENCC)",
                    marker={"size": 12, "color": AZUL}, hovertemplate="%{y}<br>ENCC: %{x:.1%}<extra></extra>")
    fig.add_scatter(x=d["pct_entradas_2022"], y=d["etiqueta"], mode="markers", name="% de entradas de estrenos 2022 (INCAA)",
                    marker={"size": 12, "color": NARANJA, "symbol": "diamond"}, hovertemplate="%{y}<br>INCAA 2022: %{x:.1%}<extra></extra>")
    fig.update_xaxes(tickformat=".0%", title="Porcentaje (un título o una persona puede sumar a varios géneros)")
    return estilo(fig, "Lo que la gente dice que vio y lo que se vendió",
                  "Dos medidas distintas: personas (ENCC) y entradas de títulos con match TMDB confiable (INCAA, estrenos 2022)",
                  fuente="Fuentes: ENCC 2022/23; INCAA estrenos comerciales 2022 enriquecidos con TMDB (97% de las entradas con match confiable).", alto=500)


def titulo_corto(t: str) -> str:
    import string
    t = t.split(":")[0].replace(" LA PELICULA", "").rstrip(".")
    return string.capwords(t.lower())


def cronologia_videojuegos() -> go.Figure:
    d = tabla("incaa_adaptaciones_videojuegos")
    d["fecha_estreno"] = pd.to_datetime(d["fecha_estreno"])
    antes = d["respecto_campo_encc"].eq("antes del trabajo de campo")
    fig = go.Figure()
    fig.add_vrect(x0=c.CAMPO_INICIO, x1=c.CAMPO_FIN, fillcolor=GRILLA, opacity=0.8, line_width=0,
                  annotation_text="Trabajo de campo ENCC", annotation_position="top left", annotation_font_color=TINTA_2)
    fig.add_bar(x=d["fecha_estreno"], y=d["entradas"], marker_color=np.where(antes, AZUL, GRIS), width=1000 * 3600 * 24 * 25,
                text=d["titulo"].map(titulo_corto), textposition="outside", cliponaxis=False,
                textfont={"size": 13, "color": TINTA}, constraintext="none",
                hovertemplate="%{text}<br>%{x|%d/%m/%Y}<br>%{y:,.0f} entradas<extra></extra>", showlegend=False)
    fig.update_yaxes(title="Entradas vendidas", tickformat=",.0f", range=[0, d["entradas"].max() * 1.25])
    fig.update_xaxes(range=[pd.Timestamp("2021-12-01"), pd.Timestamp("2024-02-15")])
    return estilo(fig, "Solo 2 de las 5 adaptaciones de videojuegos son anteriores a la encuesta",
                  "Azul = estrenada antes del trabajo de campo; gris = posterior (no pudo influir en las respuestas)",
                  fuente="Fuente: INCAA, estrenos comerciales 2022–2023; marca de adaptación según TMDB.", alto=460)


# ---------------------------------------------------------------------- apéndice
def clustering_k() -> go.Figure:
    from plotly.subplots import make_subplots
    d = tabla("clustering_seleccion_k")
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Silueta (separación)", "Estabilidad (ARI bootstrap)"), horizontal_spacing=0.12)
    fig.add_scatter(x=d["k"], y=d["silueta"], mode="lines+markers", line={"color": AZUL, "width": 2}, marker={"size": 9},
                    showlegend=False, hovertemplate="k = %{x}<br>silueta %{y:.3f}<extra></extra>", row=1, col=1)
    fig.add_scatter(x=d["k"], y=d["ari_media"], mode="lines+markers", line={"color": AZUL, "width": 2}, marker={"size": 9},
                    showlegend=False, hovertemplate="k = %{x}<br>ARI medio %{y:.3f}<extra></extra>", row=1, col=2)
    fig.update_xaxes(title="k", dtick=1)
    return estilo(fig, "Clustering: no aparece un número natural de grupos",
                  f"La silueta no tiene un máximo interior (el más alto es k = {int(d.loc[d['silueta'].idxmax(), 'k'])}, el borde); k = 4, la versión anterior, es la opción menos estable",
                  fuente="Fuente: ENCC 2022/23. K-means ponderado sobre 9 variables de consumo estandarizadas; ARI de 20 réplicas bootstrap.", alto=400)


TODAS = {
    "01_poblacion_segmentos": poblacion_segmentos,
    "02_asistencia_observada_vs_ajustada": asistencia_observada_vs_ajustada,
    "03_asistencia_por_edad": asistencia_por_edad,
    "04_forest_asistencia": forest_asistencia,
    "05_sensibilidad": sensibilidad,
    "06_generos_poblacion_vs_asistentes": generos_poblacion_vs_asistentes,
    "07_generos_diferencias": generos_diferencias,
    "08_auc_por_bloque": auc_por_bloque,
    "09_curvas_roc": curvas_roc,
    "10_calibracion": calibracion,
    "11_importancia": importancia,
    "12_encc_vs_incaa": encc_vs_incaa,
    "13_cronologia_videojuegos": cronologia_videojuegos,
}
