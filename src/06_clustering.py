#!/usr/bin/env python3
"""Paso 06 — Segmentación no supervisada (análisis secundario).

Se agrupa por comportamiento de consumo audiovisual y de juego (no por demografía, que se describe después).
Se elige k comparando silueta y estabilidad (ARI entre réplicas bootstrap), no por continuidad con versiones
anteriores. Los tamaños de grupo se reportan ponderados.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

import comun as c

VARIABLES = ["cine_asistio", "cine_veces_log", "vj_frecuencia_orden", "vj_n_dispositivos", "vj_n_generos",
             "stream_pago_frecuencia_orden", "stream_gratis_frecuencia_orden", "stream_n_generos", "tv_mira"]


def preparar(df):
    X = df.copy()
    veces = X["cine_veces"].where(X["cine_asistio"] == 1, 0)
    veces = veces.fillna(X.loc[X["cine_asistio"] == 1, "cine_veces"].median())  # 11 Ns/Nc entre asistentes
    X["cine_veces_log"] = np.log1p(veces)
    for col in ("stream_pago_frecuencia_orden", "stream_gratis_frecuencia_orden"):
        X[col] = X[col].fillna(X[col].median())  # 36 Ns/Nc en total
    return StandardScaler().fit_transform(X[VARIABLES])


def main():
    df = c.cargar_encc()
    Z = preparar(df)
    w = df["ponderador"].to_numpy()
    rng = np.random.default_rng(c.SEMILLA)

    filas = []
    for k in range(2, 9):
        km = KMeans(k, n_init=20, random_state=c.SEMILLA).fit(Z, sample_weight=w)
        sil = silhouette_score(Z, km.labels_, sample_size=2000, random_state=c.SEMILLA)
        aris = []
        for _ in range(20):
            idx = rng.choice(len(Z), len(Z), replace=True)
            km_b = KMeans(k, n_init=5, random_state=int(rng.integers(1e9))).fit(Z[idx], sample_weight=w[idx])
            aris.append(adjusted_rand_score(km.labels_, km_b.predict(Z)))
        filas.append({"k": k, "silueta": sil, "ari_media": float(np.mean(aris)), "ari_p10": float(np.percentile(aris, 10)),
                      "inercia": km.inertia_})
    sel = pd.DataFrame(filas)
    c.guardar_tabla(sel, "clustering_seleccion_k")

    # Regla (fijada tras observar la curva): si la silueta tiene un máximo interior, se usa ese k; si el máximo está en
    # el borde de la grilla, no hay un número "natural" de grupos y se reporta el k más estable (mayor ARI).
    k_sil = int(sel.loc[sel["silueta"].idxmax(), "k"])
    maximo_interior = sel["k"].min() < k_sil < sel["k"].max()
    k = k_sil if maximo_interior else int(sel.loc[sel["ari_media"].idxmax(), "k"])
    km = KMeans(k, n_init=50, random_state=c.SEMILLA).fit(Z, sample_weight=w)
    df["cluster"] = km.labels_

    perfiles = []
    for g, sub in df.groupby("cluster"):
        ww = sub["ponderador"]
        av = lambda s: float(np.average(s.fillna(0), weights=ww))
        perfiles.append({
            "cluster": int(g), "n": len(sub), "pct_poblacion": float(ww.sum() / w.sum()),
            "asistencia_cine": av(sub["cine_asistio"]), "juega": av(sub["vj_jugo"]),
            "pc_consola": av(sub["segmento"].eq("pc_consola").astype(float)),
            "usa_plataformas": av(sub["stream_usa_plataformas"]), "generos_streaming": av(sub["stream_n_generos"]),
            "edad_media": av(sub["edad"]), "pct_abc1_c2": av(sub["nse"].isin(["ABC1", "C2"]).astype(float)),
        })
    perfiles = pd.DataFrame(perfiles).sort_values("asistencia_cine", ascending=False)
    c.guardar_tabla(perfiles, "clustering_perfiles")
    df[["id", "cluster"]].to_csv(c.PROC / "encc_clusters.csv", index=False)

    r = sel.set_index("k").loc[k]
    c.actualizar_resumen("clustering", {"k": k, "silueta": float(r["silueta"]), "ari_media": float(r["ari_media"]),
                                        "silueta_max": float(sel["silueta"].max()), "silueta_maximo_interior": bool(maximo_interior),
                                        "ari_k4": float(sel.set_index("k").loc[4, "ari_media"]),
                                        "ari_p10_k4": float(sel.set_index("k").loc[4, "ari_p10"])})
    print(sel.round(3).to_string(index=False))
    print(f"k elegido = {k}")
    print(perfiles.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
