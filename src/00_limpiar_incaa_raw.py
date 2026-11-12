#!/usr/bin/env python3
# ESTADO: documentado, no forma parte de run_all.py. Su entrada (export crudo de Tableau del INCAA,
# Peliculas_inca_cs_datos.csv) no está disponible; su salida es data/raw/incaa/incaa_estrenos_comerciales.csv.
"""
Limpieza del export del tablero "Cantidad de espectadores por película estrenada" (INCAA).

Uso (Colab o local):
    python limpiar_incaa.py data/raw/incaa/*.csv --salida data/clean/

Acepta uno o varios archivos (por ejemplo, uno por año) y los une.
No agrega géneros: eso se hace en un paso aparte.

Qué hace
- Lee el archivo tal como lo exporta Tableau (UTF-16, separado por tabulaciones).
  También acepta UTF-8 y separador coma o punto y coma.
- Convierte números con coma de miles (3,562,856) y fechas mes/día/año (8/15/2022).
- Normaliza títulos y agrega marcas de calidad. No borra filas: las marca.
- Genera dos CSV: todas las filas y solo estrenos comerciales.
"""
import argparse
import csv
import io
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

# Nombres canónicos de columna (la clave es el nombre normalizado: minúsculas, sin acentos ni símbolos)
COLUMNAS = {
    "codigo": "codigo",
    "titulo": "titulo",
    "fecha estreno": "fecha_estreno_raw",
    "origen pelicula": "origen",
    "entradas": "entradas",
    "recaudacion": "recaudacion",
}

TIPO_ORIGEN = {
    "nacionales": "nacional",
    "extranjeras": "extranjera",
    "festivales, muestras y otros": "evento",
}

# Umbrales de la marca de precio atípico: cociente contra la mediana del año
PRECIO_MIN_RATIO = 0.2
PRECIO_MAX_RATIO = 5.0


def sin_acentos(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def normalizar_columna(nombre: str) -> str:
    n = sin_acentos(str(nombre)).lower()
    n = re.sub(r"\(.*?\)", " ", n)          # quita "($)" y similares
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def normalizar_titulo(titulo: str) -> str:
    t = sin_acentos(titulo).lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def leer_archivo(ruta: Path) -> pd.DataFrame:
    crudo = ruta.read_bytes()
    texto = None
    for enc in ("utf-16", "utf-8-sig", "latin-1"):
        try:
            texto = crudo.decode(enc)
            break
        except UnicodeError:
            continue
    if texto is None:
        raise ValueError(f"No pude decodificar {ruta}")
    muestra = texto[:5000]
    try:
        sep = csv.Sniffer().sniff(muestra, delimiters="\t,;").delimiter
    except csv.Error:
        sep = "\t"
    df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [normalizar_columna(c) for c in df.columns]
    faltan = [c for c in COLUMNAS if c not in df.columns]
    if faltan:
        raise ValueError(f"{ruta.name}: faltan columnas {faltan}. Encontré {list(df.columns)}")
    df = df.rename(columns=COLUMNAS)[list(COLUMNAS.values())]
    df["archivo_origen"] = ruta.name
    return df


def parsear_numero(valor: str) -> float:
    """Acepta 3,562,856 (EE.UU.), 3.562.856 (AR) y 1234.5. Devuelve NaN si no entiende."""
    s = str(valor).strip().replace(" ", "")
    if s == "":
        return np.nan
    if re.fullmatch(r"-?\d+", s):
        return float(s)
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        return float(s.replace(",", ""))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", s):
        return float(s.replace(".", "").replace(",", "."))
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return np.nan


def parsear_fechas(serie: pd.Series) -> pd.Series:
    """Mes/día/año (formato del tablero). Si alguna falla, prueba día/mes/año."""
    f = pd.to_datetime(serie, format="%m/%d/%Y", errors="coerce")
    falla = f.isna()
    if falla.any():
        alt = pd.to_datetime(serie[falla], format="%d/%m/%Y", errors="coerce")
        f.loc[falla] = alt
    return f


def limpiar(df: pd.DataFrame, log: list) -> pd.DataFrame:
    n0 = len(df)
    for c in ("codigo", "titulo", "origen"):
        df[c] = df[c].str.strip().str.replace(r"\s+", " ", regex=True)

    # Duplicados exactos de código: se queda la última aparición (export más reciente)
    dup = df.duplicated("codigo", keep="last")
    if dup.any():
        log.append(f"Códigos duplicados eliminados: {int(dup.sum())}")
        df = df[~dup].copy()

    df["entradas"] = df["entradas"].map(parsear_numero)
    df["recaudacion_pesos"] = df["recaudacion"].map(parsear_numero)
    df["fecha_estreno"] = parsear_fechas(df["fecha_estreno_raw"])

    malas = df[["entradas", "recaudacion_pesos", "fecha_estreno"]].isna().any(axis=1)
    if malas.any():
        log.append(f"Filas con número o fecha ilegible (se descartan): {int(malas.sum())}")
        df = df[~malas].copy()

    df["entradas"] = df["entradas"].astype("int64")
    df["recaudacion_pesos"] = df["recaudacion_pesos"].round(2)
    if (df["recaudacion_pesos"] % 1 == 0).all():
        df["recaudacion_pesos"] = df["recaudacion_pesos"].astype("int64")

    df["anio_estreno"] = df["fecha_estreno"].dt.year.astype("int64")
    df["mes_estreno"] = df["fecha_estreno"].dt.month.astype("int64")
    df["tipo_origen"] = df["origen"].str.lower().map(TIPO_ORIGEN)
    desconocidos = df["tipo_origen"].isna()
    if desconocidos.any():
        valores = sorted(df.loc[desconocidos, "origen"].unique())
        log.append(f"ATENCIÓN: orígenes sin mapear (quedan como 'otro'): {valores}")
        df.loc[desconocidos, "tipo_origen"] = "otro"
    df["es_estreno_comercial"] = df["tipo_origen"].isin(["nacional", "extranjera"])
    df["titulo_norm"] = df["titulo"].map(normalizar_titulo)

    # Marcas de calidad (no se borra nada)
    df["recaudacion_cero"] = (df["entradas"] > 0) & (df["recaudacion_pesos"] == 0)
    df["precio_medio_entrada"] = np.where(
        df["recaudacion_pesos"] > 0, (df["recaudacion_pesos"] / df["entradas"]).round(2), np.nan
    )
    com = df["es_estreno_comercial"] & df["precio_medio_entrada"].notna()
    mediana = df[com].groupby("anio_estreno")["precio_medio_entrada"].median()
    ratio = df["precio_medio_entrada"] / df["anio_estreno"].map(mediana)
    df["precio_atipico"] = df["es_estreno_comercial"] & ((ratio < PRECIO_MIN_RATIO) | (ratio > PRECIO_MAX_RATIO))

    en_comercial = set(df.loc[df["es_estreno_comercial"], "titulo_norm"])
    en_evento = set(df.loc[~df["es_estreno_comercial"], "titulo_norm"])
    ambos = en_comercial & en_evento
    df["titulo_repetido_en_otro_origen"] = df["titulo_norm"].isin(ambos)

    log.append(f"Filas leídas: {n0} | filas limpias: {len(df)}")
    columnas = [
        "codigo", "titulo", "titulo_norm", "fecha_estreno", "anio_estreno", "mes_estreno",
        "origen", "tipo_origen", "es_estreno_comercial", "entradas", "recaudacion_pesos",
        "precio_medio_entrada", "recaudacion_cero", "precio_atipico",
        "titulo_repetido_en_otro_origen", "archivo_origen",
    ]
    df = df[columnas].sort_values(["anio_estreno", "entradas"], ascending=[True, False])
    df["fecha_estreno"] = df["fecha_estreno"].dt.strftime("%Y-%m-%d")
    return df.reset_index(drop=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivos", nargs="+", help="CSV exportados del tablero del INCAA")
    ap.add_argument("--salida", default=".", help="carpeta de salida")
    args = ap.parse_args(argv)

    log = []
    partes = [leer_archivo(Path(a)) for a in args.archivos]
    limpio = limpiar(pd.concat(partes, ignore_index=True), log)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    limpio.to_csv(salida / "incaa_limpio.csv", index=False, encoding="utf-8")
    comercial = limpio[limpio["es_estreno_comercial"]]
    comercial.to_csv(salida / "incaa_estrenos_comerciales.csv", index=False, encoding="utf-8")

    log.append(f"Estrenos comerciales: {len(comercial)} | eventos y muestras: {len(limpio) - len(comercial)}")
    for anio, g in comercial.groupby("anio_estreno"):
        log.append(f"  {anio}: {len(g)} estrenos, {int(g['entradas'].sum()):,} entradas")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
