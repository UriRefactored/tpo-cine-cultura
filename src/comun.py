"""Rutas, constantes y utilidades compartidas por todos los scripts del pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]

RAW_ENCC = RAIZ / "data/raw/encc/base-datos-encc-2022-2023.csv"
RAW_INCAA = RAIZ / "data/raw/incaa/incaa_estrenos_comerciales.csv"
RAW_TMDB = RAIZ / "data/raw/tmdb/incaa_peliculas_enriquecidas_snapshot.csv"
MANIFEST = RAIZ / "docs/fuentes/manifest.json"

PROC = RAIZ / "data/processed"
ENCC_LIMPIA = PROC / "encc_analitica.csv"
DICCIONARIO = PROC / "diccionario_variables.csv"

TABLAS = RAIZ / "outputs/tablas"
FIGURAS = RAIZ / "outputs/figuras"
RESUMEN = RAIZ / "outputs/resumen.json"

SEMILLA = 20221101  # semilla única y registrada para todo procedimiento aleatorio

# Trabajo de campo ENCC 2022/23 (Metodología y manual de uso de la base): noviembre 2022 a enero 2023.
CAMPO_INICIO = pd.Timestamp("2022-11-01")
CAMPO_FIN = pd.Timestamp("2023-01-31")

SEGMENTOS = ["pc_consola", "solo_movil", "no_juega"]
ETIQUETA_SEGMENTO = {
    "pc_consola": "Juega en PC/consola",
    "solo_movil": "Juega solo en celular/tablet",
    "no_juega": "No jugó videojuegos",
}

GENEROS_CINE = [
    "accion_aventura", "ciencia_ficcion", "suspenso", "terror", "drama",
    "comedia", "romantico", "documental", "infantiles", "animacion",
]
ETIQUETA_GENERO = {
    "accion_aventura": "Acción/Aventura", "ciencia_ficcion": "Ciencia ficción", "suspenso": "Suspenso",
    "terror": "Terror", "drama": "Drama", "comedia": "Comedia", "romantico": "Romántico",
    "documental": "Documental", "infantiles": "Infantiles", "animacion": "Animación",
}


def asegurar_directorios() -> None:
    for d in (PROC, TABLAS, FIGURAS):
        d.mkdir(parents=True, exist_ok=True)


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def media_ponderada(x: pd.Series, w: pd.Series) -> float:
    m = x.notna()
    return float(np.average(x[m], weights=w[m]))


def guardar_tabla(df: pd.DataFrame, nombre: str) -> Path:
    ruta = TABLAS / f"{nombre}.csv"
    df.to_csv(ruta, index=False)
    return ruta


def actualizar_resumen(clave: str, valor) -> None:
    """Guarda cifras clave en outputs/resumen.json para que README y app no transcriban números."""
    datos = json.loads(RESUMEN.read_text(encoding="utf-8")) if RESUMEN.exists() else {}
    datos[clave] = valor
    RESUMEN.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=float), encoding="utf-8")


def cargar_encc() -> pd.DataFrame:
    if not ENCC_LIMPIA.exists():
        raise FileNotFoundError(f"Falta {ENCC_LIMPIA}. Ejecutá antes: python run_all.py")
    return pd.read_csv(ENCC_LIMPIA)
