#!/usr/bin/env python3
"""
entrenar_modelos.py
Entrena modelos de Machine Learning sobre la base limpia de la ENCC 2022-2023.

1. Modelo Predictivo Supervisado (Clasificación):
   - Target: 'cine_fue_ultimo_ano' (1 = Asistió al cine, 0 = No asistió).
   - Features: Variables sociodemográficas, hábitos de videojuegos, streaming y nivel educativo.
   - Algoritmos: Random Forest y Regresión Logística ponderados por el peso muestral de la ENCC.
   - Métricas: ROC-AUC, F1-Score, Matriz de Confusión e Importancia de Variables.

2. Segmentación No Supervisada (Clustering):
   - Agrupa a los 3.380 encuestados en arquetipos de consumidores culturales según su consumo de cine, gaming y streaming.
   - Guarda el dataset con etiquetas en 'encc_con_clusters.csv'.

Uso:
    python3 entrenar_modelos.py
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def obtener_ruta_existente(candidatos):
    for c in candidatos:
        p = Path(c)
        if p.exists():
            return p
    return Path(candidatos[0])


RUTA_ENCC = obtener_ruta_existente(["encc_encuesta_limpia_ml.csv", "encc_limpia_ml.csv"])
SALIDA_CLUSTERS = Path("encc_segmentos_clusters.csv")


def entrenar():
    if not RUTA_ENCC.exists():
        raise FileNotFoundError(f"No se encontró {RUTA_ENCC}. Ejecutá antes 02_limpiar_encc.py")

    print(f"Cargando {RUTA_ENCC}...")
    df = pd.read_csv(RUTA_ENCC)

    # -------------------------------------------------------------------------
    # 1. MODELO SUPERVISADO: PREDICCIÓN DE ASISTENCIA AL CINE
    # -------------------------------------------------------------------------
    target_col = "cine_fue_ultimo_ano"
    
    # Excluir identificadores, ponderadores y variables dependientes del target (como cantidad de visitas o géneros de cine)
    cols_excluir = [
        "id", "ponderador", "expansor", target_col,
        "cine_frecuencia_anual_est", "cine_visitas_anuales", "cine_visitas_peliculas_arg",
        "cine_no_va_motivo_economico", "cine_no_va_prefiere_casa", "cine_no_va_falta_interes",
        "feat_cinefilo_frecuente", "feat_gamer_y_cinefilo", "feat_interes_accion_ambos",
        "feat_interes_animacion_o_infantil", "feat_diversidad_generos_cine"
    ]
    cols_excluir += [c for c in df.columns if c.startswith("cine_g_")]

    feature_cols = [c for c in df.columns if c not in cols_excluir]
    print(f"\nVariables predictoras seleccionadas para el modelo: {len(feature_cols)}")

    X = df[feature_cols].copy()
    y = df[target_col].copy()
    weights = df["ponderador"].copy()

    # Split train/test (80/20) estratificado
    X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(
        X, y, weights, test_size=0.20, random_state=42, stratify=y
    )

    # Escalar variables para modelos lineales
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # A) Random Forest Classifier
    rf = RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_split=10, random_state=42)
    rf.fit(X_train, y_train, sample_weight=w_train)
    y_pred_rf = rf.predict(X_test)
    y_prob_rf = rf.predict_proba(X_test)[:, 1]

    auc_rf = roc_auc_score(y_test, y_prob_rf, sample_weight=w_test)
    acc_rf = accuracy_score(y_test, y_pred_rf, sample_weight=w_test)

    print("\n" + "=" * 60)
    print("RESULTADOS DEL MODELO DE CLASIFICACIÓN (ASISTENCIA AL CINE)")
    print("=" * 60)
    print(f"Random Forest  -> ROC-AUC: {auc_rf:.3f} | Accuracy ponderada: {acc_rf:.1%}")

    # B) Logistic Regression (para contrastar interpretabilidad)
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_scaled, y_train, sample_weight=w_train)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]
    auc_lr = roc_auc_score(y_test, y_prob_lr, sample_weight=w_test)
    print(f"Regresión Log. -> ROC-AUC: {auc_lr:.3f}")

    # Top 10 variables más influyentes
    importancias = pd.DataFrame({
        "variable": feature_cols,
        "importancia": rf.feature_importances_
    }).sort_values("importancia", ascending=False)

    print("\nTop 10 variables más predictivas para ir al cine:")
    for i, r in importancias.head(10).reset_index(drop=True).iterrows():
        print(f"  {i+1}. {r['variable']:<35} {r['importancia']:.4f}")

    # -------------------------------------------------------------------------
    # 2. MODELO NO SUPERVISADO: SEGMENTACIÓN DE AUDIENCIAS (CLUSTERING)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("SEGMENTACIÓN DE CONSUMIDORES CULTURALES (K-MEANS)")
    print("=" * 60)

    cols_cluster = [
        "edad", "nse_orden", "nivel_educativo_orden",
        "cine_fue_ultimo_ano", "cine_visitas_anuales",
        "vj_jugo_ultimo_ano", "vj_frecuencia_anual_est", "feat_gamer_activo",
        "feat_diversidad_generos_vj", "feat_diversidad_generos_streaming",
        "stream_g_accion_aventura", "stream_g_comedia", "stream_g_drama"
    ]
    X_clust = df[cols_cluster].copy()
    X_clust_scaled = StandardScaler().fit_transform(X_clust)

    k = 4
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_clust_scaled)
    df["cluster_id"] = clusters

    # Nombrar arquetipos según sus centros
    perfiles = []
    for c in range(k):
        sub = df[df["cluster_id"] == c]
        p = {
            "cluster_id": c,
            "tamaño_n": len(sub),
            "pct_poblacion": f"{len(sub)/len(df):.1%}",
            "edad_media": round(sub["edad"].mean(), 1),
            "nse_medio": round(sub["nse_orden"].mean(), 2),
            "tasa_cine": f"{sub['cine_fue_ultimo_ano'].mean():.1%}",
            "tasa_gamers": f"{sub['vj_jugo_ultimo_ano'].mean():.1%}",
            "freq_vj_anual": round(sub["vj_frecuencia_anual_est"].mean(), 1),
            "visitas_cine_anual": round(sub["cine_visitas_anuales"].mean(), 1),
        }
        perfiles.append(p)

    df_perfiles = pd.DataFrame(perfiles)
    print(df_perfiles.to_string(index=False))

    df.to_csv(SALIDA_CLUSTERS, index=False)
    print(f"\nBase con clusters asignados guardada: {SALIDA_CLUSTERS}")


if __name__ == "__main__":
    entrenar()
