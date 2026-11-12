#!/usr/bin/env python3
"""Reproduce todo el análisis desde las fuentes en data/raw/.

    python run_all.py              # pipeline completo (≈ 3 minutos)
    python run_all.py --rapido     # omite el paso predictivo (el más lento)

Los pasos 00 (limpieza del export crudo del INCAA) y 01 (consulta a la API de TMDB) no se ejecutan: el export
crudo no está disponible y el enriquecimiento se conserva como snapshot versionado (ver docs/fuentes/manifest.json).
"""

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PASOS = [
    "02_auditar_fuentes.py",
    "03_limpiar_encc.py",
    "04_inferencia.py",
    "05_prediccion.py",
    "06_clustering.py",
    "07_mercado_incaa.py",
    "08_figuras.py",
    "09_historia.py",
]


def main() -> None:
    rapido = "--rapido" in sys.argv
    resumen = RAIZ / "outputs/resumen.json"
    if not rapido and resumen.exists():
        resumen.unlink()  # se regenera completo para que no queden cifras de corridas anteriores
    for paso in PASOS:
        if rapido and paso.startswith("05_"):
            print(f"── omitido {paso}")
            continue
        print(f"\n══ {paso} " + "═" * (60 - len(paso)))
        t0 = time.time()
        subprocess.run([sys.executable, str(RAIZ / "src" / paso)], check=True, cwd=RAIZ)
        print(f"── {paso} OK ({time.time() - t0:.0f} s)")
    print("\nListo. Tablas en outputs/tablas/, figuras en outputs/figuras/, cifras clave en outputs/resumen.json")


if __name__ == "__main__":
    main()
