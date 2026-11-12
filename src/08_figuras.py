#!/usr/bin/env python3
"""Paso 08 — Exporta todas las figuras a PNG (outputs/figuras/) para las diapositivas y una demo sin red."""

import comun as c
from graficos import TODAS


def main():
    c.asegurar_directorios()
    for nombre, fn in TODAS.items():
        fig = fn()
        fig.write_image(c.FIGURAS / f"{nombre}.png", width=1400, height=fig.layout.height or 500, scale=2)
        print(f"  {nombre}.png")


if __name__ == "__main__":
    main()
