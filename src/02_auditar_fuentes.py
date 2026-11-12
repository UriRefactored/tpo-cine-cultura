#!/usr/bin/env python3
"""Paso 02 — Auditoría de integridad de las fuentes.

Verifica que cada insumo coincida con el SHA-256 registrado en docs/fuentes/manifest.json y
corre controles estructurales básicos. Si algo no coincide, el pipeline se detiene.

Salida: outputs/tablas/auditoria_fuentes.csv
"""

import json

import pandas as pd

import comun as c


def chequeo(nombre: str, ok: bool, detalle: str) -> dict:
    return {"control": nombre, "resultado": "OK" if ok else "FALLA", "detalle": detalle}


def main() -> None:
    c.asegurar_directorios()
    filas = []

    manifest = json.loads(c.MANIFEST.read_text(encoding="utf-8"))
    for item in manifest:
        ruta = c.RAIZ / item["path"]
        if not ruta.exists():
            filas.append(chequeo(f"existe {item['path']}", False, "archivo ausente"))
            continue
        h = c.sha256(ruta)
        filas.append(chequeo(f"sha256 {item['path']}", h == item["sha256"], h))

    encc = pd.read_csv(c.RAW_ENCC, low_memory=False)
    filas += [
        chequeo("ENCC dimensiones", encc.shape == (3380, 548), f"{encc.shape[0]} filas x {encc.shape[1]} columnas"),
        chequeo("ENCC id único", encc["id"].is_unique, f"{encc['id'].nunique()} ids distintos"),
        chequeo("ENCC ponderador > 0", bool((encc["ponderador"] > 0).all()), f"rango {encc['ponderador'].min():.3f}–{encc['ponderador'].max():.3f}"),
        chequeo("ENCC expansor > 0", bool((encc["expansor"] > 0).all()), f"suma expansor = {encc['expansor'].sum():,.0f} personas"),
        chequeo("ENCC edad 13+", bool(encc["edad"].min() >= 13), f"rango {encc['edad'].min()}–{encc['edad'].max()}"),
        chequeo("ENCC localidades (UPM)", encc["localidad"].notna().all(), f"{encc['localidad'].nunique()} localidades en {encc['region'].nunique()} regiones"),
    ]

    incaa = pd.read_csv(c.RAW_INCAA)
    tmdb = pd.read_csv(c.RAW_TMDB)
    base = incaa.set_index("codigo")[["titulo", "entradas"]]
    snap = tmdb.set_index("codigo")[["titulo", "entradas"]]
    filas += [
        chequeo("INCAA código único", incaa["codigo"].is_unique, f"{len(incaa)} estrenos"),
        chequeo("INCAA solo estrenos comerciales", bool(incaa["es_estreno_comercial"].all()), "nacionales y extranjeros; sin festivales ni muestras"),
        chequeo("TMDB snapshot = INCAA (títulos y entradas)", base.sort_index().equals(snap.sort_index()), f"{len(tmdb)} filas en snapshot"),
    ]

    df = pd.DataFrame(filas)
    c.guardar_tabla(df, "auditoria_fuentes")
    print(df.to_string(index=False))
    if (df["resultado"] == "FALLA").any():
        raise SystemExit("Auditoría de fuentes con fallas: revisar outputs/tablas/auditoria_fuentes.csv")


if __name__ == "__main__":
    main()
