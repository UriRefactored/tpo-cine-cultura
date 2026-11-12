#!/usr/bin/env python3
"""Paso 05 — Minería predictiva: ¿cuánto aporta el gaming a la predicción de la asistencia al cine?

Diseño (fijado antes de mirar el test):
- Objetivo: cine_asistio (asistencia retrospectiva en el último año). Se excluyen todas las variables del
  bloque cine (frecuencia, veces, géneros, motivos) porque dependen del objetivo.
- Partición: 80% entrenamiento / 20% test final, estratificada, semilla registrada. El test se usa una sola
  vez, al final, para todos los modelos.
- Selección: validación cruzada estratificada repetida (5 × 3) en entrenamiento. Imputación, escalado y
  one-hot se aprenden dentro de cada partición (Pipeline).
- Bloques de variables anidados: demografía → + segmento de juego → + gaming completo → + streaming.
- Modelos: baseline (prevalencia), regresión logística (L2, C elegido por CV) y Random Forest (hojas mínimas y
  variables por división elegidas por CV).
- Métricas ponderadas con `ponderador` (representan a la población, no a la muestra). Umbral de
  clasificación elegido en entrenamiento (F1 máximo sobre predicciones fuera de partición).
- Incertidumbre: bootstrap por conglomerado (localidad) sobre el test, 2.000 réplicas, también para la
  diferencia de AUC entre bloques (bootstrap pareado).
"""

import itertools
import json
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import comun as c

OBJETIVO = "cine_asistio"
DEMO_NUM = ["edad", "es_mujer", "educacion_orden", "nse_orden"]
DEMO_CAT = ["actividad", "region", "tamanio"]
SEGMENTO = ["seg_pc_consola", "seg_solo_movil"]
GAMING = ["vj_jugo", "vj_frecuencia_orden", "vj_juegos_comprados", "vj_n_dispositivos", "vj_n_generos"]
STREAM = ["tv_mira", "stream_usa_plataformas", "stream_pago_frecuencia_orden", "stream_gratis_frecuencia_orden",
          "stream_n_generos"]

GRILLAS = {
    "logistica": [{"modelo__C": C} for C in (0.01, 0.1, 1.0)],
    "random_forest": [{"modelo__min_samples_leaf": h, "modelo__max_features": f}
                      for h, f in itertools.product((5, 20), ("sqrt", 0.5))],
}


def bloques(df):
    vj = [col for col in df.columns if col.startswith(("vj_disp_", "vj_con_", "vj_g_"))]
    st = [col for col in df.columns if col.startswith("stream_g_")]
    return {
        "1_demografia": (DEMO_NUM, DEMO_CAT),
        "2_demo_segmento": (DEMO_NUM + SEGMENTO, DEMO_CAT),
        "3_demo_gaming": (DEMO_NUM + SEGMENTO + GAMING + vj, DEMO_CAT),
        "4_demo_gaming_streaming": (DEMO_NUM + SEGMENTO + GAMING + vj + STREAM + st, DEMO_CAT),
    }


def pipeline(num, cat, tipo):
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("esc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", drop="first"))]), cat),
    ])
    if tipo == "logistica":
        modelo = LogisticRegression(max_iter=5000)
    elif tipo == "random_forest":
        modelo = RandomForestClassifier(n_estimators=400, n_jobs=-1, random_state=c.SEMILLA)
    else:
        modelo = DummyClassifier(strategy="prior")
    return Pipeline([("pre", pre), ("modelo", modelo)])


def ajustar(pipe, X, y, w):
    return pipe.fit(X, y, modelo__sample_weight=w)


def seleccionar(num, cat, tipo, X, y, w):
    """Devuelve (mejores params, AUC CV media, desvío, predicciones OOF con los mejores params)."""
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=c.SEMILLA)
    mejor = None
    for params in GRILLAS.get(tipo, [{}]):
        aucs = []
        for tr, va in cv.split(X, y):
            p = ajustar(pipeline(num, cat, tipo).set_params(**params), X.iloc[tr], y.iloc[tr], w.iloc[tr])
            aucs.append(roc_auc_score(y.iloc[va], p.predict_proba(X.iloc[va])[:, 1], sample_weight=w.iloc[va]))
        if mejor is None or np.mean(aucs) > mejor[1]:
            mejor = (params, float(np.mean(aucs)), float(np.std(aucs)))
    oof = np.zeros(len(y))
    for tr, va in StratifiedKFold(5, shuffle=True, random_state=c.SEMILLA).split(X, y):
        p = ajustar(pipeline(num, cat, tipo).set_params(**mejor[0]), X.iloc[tr], y.iloc[tr], w.iloc[tr])
        oof[va] = p.predict_proba(X.iloc[va])[:, 1]
    return (*mejor, oof)


def umbral_f1(y, prob, w):
    grid = np.linspace(0.05, 0.95, 91)
    f1 = [f1_score(y, prob >= t, sample_weight=w, zero_division=0) for t in grid]
    return float(grid[int(np.argmax(f1))])


def metricas(y, prob, w, umbral):
    pred = (prob >= umbral).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {
        "roc_auc": roc_auc_score(y, prob, sample_weight=w),
        "pr_auc": average_precision_score(y, prob, sample_weight=w),
        "brier": brier_score_loss(y, prob, sample_weight=w),
        "umbral": umbral,
        "precision": precision_score(y, pred, sample_weight=w, zero_division=0),
        "recall": recall_score(y, pred, sample_weight=w),
        "especificidad": recall_score(1 - y, 1 - pred, sample_weight=w),
        "f1": f1_score(y, pred, sample_weight=w),
        "exactitud": float(np.average(pred == y, weights=w)),
        "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn),
    }


def bootstrap_cluster(y, w, grupos, probs: dict, pares, reps=2000):
    rng = np.random.default_rng(c.SEMILLA)
    ids = np.unique(grupos)
    idx_por_grupo = {g: np.flatnonzero(grupos == g) for g in ids}
    res = {k: [] for k in probs} | {f"{a} − {b}": [] for a, b in pares}
    for _ in range(reps):
        idx = np.concatenate([idx_por_grupo[g] for g in rng.choice(ids, len(ids), replace=True)])
        if y[idx].min() == y[idx].max():
            continue
        aucs = {k: roc_auc_score(y[idx], p[idx], sample_weight=w[idx]) for k, p in probs.items()}
        for k, v in aucs.items():
            res[k].append(v)
        for a, b in pares:
            res[f"{a} − {b}"].append(aucs[a] - aucs[b])
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in res.items()}


def main():
    df = c.cargar_encc()
    df = df[df["segmento"].notna()].reset_index(drop=True)
    df["seg_pc_consola"] = (df["segmento"] == "pc_consola").astype(int)
    df["seg_solo_movil"] = (df["segmento"] == "solo_movil").astype(int)
    B = bloques(df)

    tr_idx, te_idx = train_test_split(np.arange(len(df)), test_size=0.2, stratify=df[OBJETIVO], random_state=c.SEMILLA)
    tr, te = df.iloc[tr_idx], df.iloc[te_idx]
    ytr, yte = tr[OBJETIVO], te[OBJETIVO].to_numpy()
    wtr, wte = tr["ponderador"], te["ponderador"].to_numpy()

    filas_cv, filas_test, probs_test, config, curvas, calib = [], [], {}, {}, [], []
    combinaciones = [("baseline", "1_demografia")] + [(m, b) for b in B for m in ("logistica", "random_forest")]
    for tipo, bloque in combinaciones:
        num, cat = B[bloque]
        params, auc_cv, sd_cv, oof = seleccionar(num, cat, tipo, tr[num + cat], ytr, wtr)
        umbral = umbral_f1(ytr.to_numpy(), oof, wtr.to_numpy()) if tipo != "baseline" else 0.5
        final = ajustar(pipeline(num, cat, tipo).set_params(**params), tr[num + cat], ytr, wtr)
        prob = final.predict_proba(te[num + cat])[:, 1]
        clave = f"{tipo}|{bloque}"
        probs_test[clave] = prob
        config[clave] = {"params": params, "umbral": umbral, "n_variables": len(num) + len(cat), "variables": num + cat}
        filas_cv.append({"modelo": tipo, "bloque": bloque, "auc_cv_media": auc_cv, "auc_cv_desvio": sd_cv, "params": json.dumps(params)})
        filas_test.append({"modelo": tipo, "bloque": bloque, **metricas(yte, prob, wte, umbral)})
        fpr, tpr, _ = roc_curve(yte, prob, sample_weight=wte)
        curvas.append(pd.DataFrame({"modelo": tipo, "bloque": bloque, "fpr": fpr, "tpr": tpr}))
        if tipo != "baseline":
            frac, media = calibration_curve(yte, prob, n_bins=8, strategy="quantile")
            calib.append(pd.DataFrame({"modelo": tipo, "bloque": bloque, "prob_media_predicha": media, "frecuencia_observada": frac}))
        print(f"{clave:<40} CV AUC {auc_cv:.3f} ± {sd_cv:.3f} | test AUC {filas_test[-1]['roc_auc']:.3f}")
        if tipo == "logistica" and bloque == "4_demo_gaming_streaming":
            modelo_logit_completo = final

    test = pd.DataFrame(filas_test)
    nombres_bloque = list(B)
    pares = [(f"{m}|{b2}", f"{m}|{b1}") for m in ("logistica", "random_forest") for b1, b2 in zip(nombres_bloque, nombres_bloque[1:])]
    pares += [(f"{m}|3_demo_gaming", f"{m}|1_demografia") for m in ("logistica", "random_forest")]
    pares += [(f"{m}|4_demo_gaming_streaming", f"{m}|1_demografia") for m in ("logistica", "random_forest")]
    pares += [(f"random_forest|{b}", f"logistica|{b}") for b in nombres_bloque]
    ic = bootstrap_cluster(yte, wte, te["localidad"].to_numpy(), probs_test, pares)
    test["auc_ic_inf"] = [ic[f"{m}|{b}"][0] for m, b in zip(test["modelo"], test["bloque"])]
    test["auc_ic_sup"] = [ic[f"{m}|{b}"][1] for m, b in zip(test["modelo"], test["bloque"])]
    difs = []
    for a, b in pares:
        auc_a = roc_auc_score(yte, probs_test[a], sample_weight=wte)
        auc_b = roc_auc_score(yte, probs_test[b], sample_weight=wte)
        difs.append({"comparacion": f"{a} − {b}", "dif_auc": auc_a - auc_b, "ic_inf": ic[f"{a} − {b}"][0], "ic_sup": ic[f"{a} − {b}"][1]})
    difs = pd.DataFrame(difs)

    c.guardar_tabla(pd.DataFrame(filas_cv), "prediccion_cv")
    c.guardar_tabla(test, "prediccion_test")
    c.guardar_tabla(difs, "prediccion_diferencias_auc")
    c.guardar_tabla(pd.concat(curvas), "prediccion_curvas_roc")
    c.guardar_tabla(pd.concat(calib), "prediccion_calibracion")
    pred = pd.DataFrame({"id": te["id"].to_numpy(), "localidad": te["localidad"].to_numpy(), "ponderador": wte, "y": yte})
    for k, p in probs_test.items():
        pred[k] = p
    pred.to_csv(c.TABLAS / "prediccion_test_probabilidades.csv", index=False)

    # Importancia por permutación (en test, AUC ponderado) para el modelo logístico más completo
    num, cat = B["4_demo_gaming_streaming"]
    imp = permutation_importance(modelo_logit_completo, te[num + cat], yte, sample_weight=wte, scoring="roc_auc",
                                 n_repeats=30, random_state=c.SEMILLA, n_jobs=-1)
    imp = pd.DataFrame({"variable": num + cat, "caida_auc_media": imp.importances_mean, "caida_auc_desvio": imp.importances_std})
    imp["bloque"] = np.select([imp["variable"].isin(DEMO_NUM + DEMO_CAT), imp["variable"].isin(SEGMENTO) | imp["variable"].str.startswith("vj_")],
                              ["demografia", "gaming"], "streaming")
    imp = imp.sort_values("caida_auc_media", ascending=False)
    c.guardar_tabla(imp, "prediccion_importancia_permutacion")

    config["_global"] = {"semilla": c.SEMILLA, "n_train": len(tr), "n_test": len(te), "prevalencia_train_pond": float(np.average(ytr, weights=wtr)),
                         "cv": "RepeatedStratifiedKFold(5 x 3)", "bootstrap": "2000 réplicas por localidad", "grillas": GRILLAS,
                         "python": platform.python_version(), "sklearn": sklearn.__version__}
    (c.TABLAS.parent / "prediccion_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    t = test.set_index(["modelo", "bloque"])
    c.actualizar_resumen("prediccion", {
        "n_train": len(tr), "n_test": len(te),
        "auc_test": {f"{m}|{b}": [float(r.roc_auc), float(r.auc_ic_inf), float(r.auc_ic_sup)] for (m, b), r in t.iterrows()},
        "dif_auc": {r.comparacion: [float(r.dif_auc), float(r.ic_inf), float(r.ic_sup)] for r in difs.itertuples()},
        "top_importancia": imp.head(8)[["variable", "caida_auc_media"]].values.tolist(),
    })
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print(test.round(3).to_string(index=False))
    print(difs.round(3).to_string(index=False))
    print(imp.head(12).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
