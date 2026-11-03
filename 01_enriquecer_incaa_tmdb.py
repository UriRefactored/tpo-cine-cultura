#!/usr/bin/env python3
"""
Agrega género y otros datos de TMDB a la tabla de estrenos del INCAA.

Uso:
    export TMDB_API_KEY="5eae05476e1028652e043f3730a4185a"          # Windows PowerShell: $env:TMDB_API_KEY="tu_clave"
    python enriquecer_generos_tmdb.py incaa_estrenos_comerciales.csv --salida data/clean/

Primera prueba, solo con las 20 películas más vistas:
    python enriquecer_generos_tmdb.py incaa_estrenos_comerciales.csv --limite 20

Entrada: el CSV que genera limpiar_incaa.py (sirve incaa_limpio.csv o incaa_estrenos_comerciales.csv).
Salidas (en --salida):
    incaa_con_genero.csv   tabla completa con las columnas nuevas (tmdb_*, g_*, es_adaptacion_videojuego...)
    tmdb_revisar.csv       películas dudosas o sin resultado, con candidatos alternativos
    tmdb_cache.json        respuestas guardadas: si se corta, al volver a correr no repite los pedidos

Corrección manual: completá la columna tmdb_id_corregido de tmdb_revisar.csv, guardalo como
overrides_tmdb.csv y volvé a correr con --overrides overrides_tmdb.csv (usa -1 para "sin match").

Este producto usa la API de TMDB pero no está avalado ni certificado por TMDB.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import warnings
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

# Suprimir advertencia de OpenSSL/LibreSSL en macOS con Python 3.9
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

API = "https://api.themoviedb.org/3"
DEFAULT_TMDB_KEY = "5eae05476e1028652e043f3730a4185a"
IDIOMA = "es-AR"
PAUSA = 0.05  # segundos entre pedidos

# Géneros de la ENCC (pregunta CINE 7) <- ids de género de TMDB. Es una correspondencia aproximada:
# la ENCC pregunta cómo percibe la persona la película; TMDB la clasifica por catálogo.
GENEROS_ENCC = {
    "accion_aventura": {28, 12},        # Action, Adventure
    "ciencia_ficcion": {878},           # Science Fiction
    "suspenso": {53, 9648, 80},         # Thriller, Mystery, Crime
    "terror": {27},                     # Horror
    "drama": {18},                      # Drama
    "comedia": {35},                    # Comedy
    "romantico": {10749},               # Romance
    "documental": {99},                 # Documentary
    "infantiles": {10751},              # Family
    "animacion": {16},                  # Animation
}

NUMERALES = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}
RANGO = {"alta": 3, "media": 2, "baja": 1}

# Casos de control (títulos que deberían salir marcados como adaptación de videojuego).
# Es una lista manual para revisar a ojo, no se usa para marcar nada.
CASOS_CONTROL = ["MARIO", "FREDDY", "SONIC", "UNCHARTED", "GRAN TURISMO"]


# ----------------------------------------------------------------------------- utilidades de texto
def norm(texto) -> str:
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(NUMERALES.get(t, t) for t in s.split())


def variantes(titulo: str) -> list:
    """Hasta 4 formas de buscar el mismo título (completo, sin paréntesis, partes)."""
    t = re.sub(r"\s+", " ", str(titulo)).strip()
    out = [t]
    sin_par = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", " ", t)).strip(" -:")
    if sin_par and sin_par != t:
        out.append(sin_par)
    out += [m.strip() for m in re.findall(r"\(([^)]{3,})\)", t)]
    if ":" in sin_par or " - " in sin_par:
        out += [p.strip() for p in re.split(r":| - ", sin_par) if len(p.strip()) >= 4]
    vistos, res = set(), []
    for v in out:
        k = norm(v)
        if k and k not in vistos:
            vistos.add(k)
            res.append(v)
    return res[:4]


# ----------------------------------------------------------------------------- cliente TMDB
class Tmdb:
    """Cliente mínimo con caché en disco. Acepta clave v3 (32 caracteres) o token v4 ("eyJ...")."""

    def __init__(self, clave: str, ruta_cache: Path):
        import requests  # import perezoso: así se puede probar sin red

        self.requests = requests
        self.sesion = requests.Session()
        self.headers = {"accept": "application/json"}
        self.base_params = {}
        if clave.startswith("eyJ") or len(clave) > 60:
            self.headers["Authorization"] = f"Bearer {clave}"
        else:
            self.base_params["api_key"] = clave
        self.ruta_cache = ruta_cache
        self.cache = json.loads(ruta_cache.read_text(encoding="utf-8")) if ruta_cache.exists() else {}
        self.nuevos = 0
        self.pedidos = 0

    def guardar_cache(self):
        tmp = self.ruta_cache.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.ruta_cache)

    def get(self, path: str, **params):
        clave = json.dumps([path, sorted(params.items())], ensure_ascii=False)
        if clave in self.cache:
            return self.cache[clave]
        intentos = 0
        while True:
            intentos += 1
            try:
                time.sleep(PAUSA)
                r = self.sesion.get(API + path, params={**self.base_params, **params},
                                    headers=self.headers, timeout=20)
            except self.requests.RequestException as e:
                if intentos >= 4:
                    raise SystemExit(f"Sin conexión con TMDB tras 4 intentos: {e}")
                time.sleep(2 * intentos)
                continue
            self.pedidos += 1
            if r.status_code == 200:
                datos = r.json()
                self.cache[clave] = datos
                self.nuevos += 1
                if self.nuevos % 25 == 0:
                    self.guardar_cache()
                return datos
            if r.status_code == 401:
                raise SystemExit("TMDB rechazó la clave (401). Revisá TMDB_API_KEY: puede ser la clave v3 o el token v4.")
            if r.status_code == 404:
                self.cache[clave] = {}
                return {}
            if r.status_code == 429 or r.status_code >= 500:
                if intentos >= 5:
                    raise SystemExit(f"TMDB respondió {r.status_code} varias veces seguidas. Probá más tarde.")
                time.sleep(float(r.headers.get("Retry-After", 2 * intentos)))
                continue
            raise SystemExit(f"Respuesta inesperada de TMDB: {r.status_code} {r.text[:200]}")


# ----------------------------------------------------------------------------- búsqueda y puntaje
ARTICULOS_INICIALES = re.compile(r"^(the|el|la|los|las|un|una|a|an)\s+")


def sin_art(texto: str) -> str:
    return ARTICULOS_INICIALES.sub("", texto).strip()


def similitud(vars_norm, cand) -> float:
    mejor = 0.0
    for v, peso in vars_norm:
        v_sa = sin_art(v)
        for campo in ("title", "original_title"):
            c = norm(cand.get(campo) or "")
            if c:
                c_sa = sin_art(c)
                if v == c:
                    r = 1.0
                elif v_sa and v_sa == c_sa:
                    r = 0.98  # Coincidencia idéntica quitando artículo (ej: "batman" y "the batman")
                else:
                    r = SequenceMatcher(None, v, c).ratio()
                mejor = max(mejor, r * peso)
    return mejor


def dif_anio(cand, anio):
    rd = (cand.get("release_date") or "")[:4]
    return int(rd) - anio if rd.isdigit() else None


def clasificar(sim, dy):
    if sim >= 0.90 and dy in (-1, 0):
        return "alta"
    if sim >= 0.82 and dy in (-1, 0, 1):
        return "media"
    if sim >= 0.75:
        return "baja"
    return None


def elegir(cands, vars_norm, anio):
    evaluados = []
    for c in cands.values():
        sim = similitud(vars_norm, c)
        conf = clasificar(sim, dif_anio(c, anio))
        if conf:
            evaluados.append({"cand": c, "sim": sim, "confianza": conf})
    evaluados.sort(key=lambda e: (RANGO[e["confianza"]], round(e["sim"], 3), e["cand"].get("popularity") or 0),
                   reverse=True)
    return evaluados


def buscar(tmdb, titulo, anio, tipo_origen="", entradas=0, min_entradas_relevancia=50000):
    """Devuelve (evaluados, crudos). crudos = primeros resultados de TMDB para el título completo (para diagnosticar)."""
    vs = variantes(titulo)
    vars_norm = [(norm(v), 1.0 if i == 0 else 0.92) for i, v in enumerate(vs)]
    cands, rel, crudos, evaluados = {}, {}, [], []
    pasos = [(vs[0], None), (vs[0], anio), (vs[0], anio - 1)] + [(v, None) for v in vs[1:]]
    for i, (q, y) in enumerate(pasos):
        params = dict(query=q, include_adult="false", language=IDIOMA, page=1)
        if y:
            params["primary_release_year"] = y
        resultados = (tmdb.get("/search/movie", **params) or {}).get("results", [])
        if i == 0:
            crudos = resultados[:3]
        if y:  # candidatos del año correcto, en el orden de relevancia de TMDB
            for c in resultados[:5]:
                if dif_anio(c, anio) in (-1, 0):
                    rel.setdefault(c["id"], c)
        for c in resultados:
            cands.setdefault(c["id"], c)
        evaluados = elegir(cands, vars_norm, anio)
        if evaluados and evaluados[0]["confianza"] == "alta":
            break
    # Respaldo: el título argentino suele diferir del que muestra TMDB (p. ej. "Sonido de libertad" / "Sound of Freedom").
    # TMDB igual encuentra la película por sus traducciones, así que para estrenos extranjeros grandes se acepta
    # la más popular del año correcto entre los primeros resultados. Queda como confianza "media" y con nota.
    if (not evaluados or evaluados[0]["confianza"] == "baja") and tipo_origen == "extranjera" \
            and entradas >= min_entradas_relevancia:
        populares = [c for c in rel.values() if (c.get("vote_count") or 0) >= 200]
        if populares:
            c = max(populares, key=lambda x: x.get("popularity") or 0)
            ev = {"cand": c, "sim": similitud(vars_norm, c), "confianza": "media",
                  "nota": "título distinto en TMDB; elegida por relevancia, año y popularidad"}
            evaluados = [ev] + [e for e in evaluados if e["cand"]["id"] != c["id"]]
    return evaluados, crudos


def texto_candidato(e):
    c = e["cand"]
    return f"{c['id']}: {c.get('title')} ({(c.get('release_date') or '?')[:4]}) sim={e['sim']:.2f}"


def texto_crudo(c):
    return f"{c.get('id')}: {c.get('title')} / {c.get('original_title')} ({(c.get('release_date') or '?')[:4]}) pop={c.get('popularity')}"


def registro_desde_detalle(det, sim, confianza, nota=""):
    genres = det.get("genres") or []
    ids = {g["id"] for g in genres}
    kws = [k["name"].lower() for k in (det.get("keywords") or {}).get("keywords", [])]
    adaptacion = any(k == "based on video game" for k in kws)
    kw_juego = [k for k in kws if "video game" in k or "videogame" in k]
    paises = [p["iso_3166_1"] for p in det.get("production_countries") or []]
    reg = {
        "tmdb_id": det.get("id"),
        "imdb_id": (det.get("external_ids") or {}).get("imdb_id") or det.get("imdb_id"),
        "titulo_tmdb": det.get("title"),
        "titulo_original_tmdb": det.get("original_title"),
        "fecha_estreno_mundial": det.get("release_date"),
        "idioma_original": det.get("original_language"),
        "paises_produccion": "|".join(paises),
        "generos_tmdb": "|".join(g["name"] for g in genres),
        "generos_tmdb_ids": "|".join(str(g["id"]) for g in genres),
        "duracion_min": det.get("runtime"),
        "popularidad_tmdb": det.get("popularity"),
        "voto_promedio_tmdb": det.get("vote_average"),
        "votos_tmdb": det.get("vote_count"),
        "presupuesto_usd": det.get("budget"),
        "recaudacion_mundial_usd": det.get("revenue"),
        "saga_tmdb": (det.get("belongs_to_collection") or {}).get("name"),
        "es_adaptacion_videojuego": bool(adaptacion),
        "tema_videojuego": bool(kw_juego) and not adaptacion,
        "keywords_videojuego": "|".join(kw_juego),
        "tmdb_similitud": round(sim, 3) if sim is not None else None,
        "tmdb_confianza": confianza,
        "tmdb_nota": nota,
    }
    for nombre, tmdb_ids in GENEROS_ENCC.items():
        reg[f"g_{nombre}"] = int(bool(ids & tmdb_ids))
    reg["g_sin_mapeo"] = int(bool(ids) and not any(reg[f"g_{n}"] for n in GENEROS_ENCC))
    return reg, paises


# ----------------------------------------------------------------------------- proceso principal
def detalles(tmdb, tid):
    return tmdb.get(f"/movie/{tid}", language=IDIOMA, append_to_response="keywords,external_ids") or {}


def cargar_overrides(ruta):
    if not ruta:
        return {}
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    col = "tmdb_id_corregido" if "tmdb_id_corregido" in df.columns else "tmdb_id"
    return {str(r["codigo"]).strip(): str(r[col]).strip() for _, r in df.iterrows() if str(r[col]).strip()}


def enriquecer(df, tmdb, min_entradas=1000, overrides=None, limite=None, verbose=True, min_entradas_relevancia=50000):
    overrides = overrides or {}
    elegibles = df[df["es_estreno_comercial"] & (df["entradas"] >= min_entradas)].sort_values("entradas", ascending=False)
    if limite:
        elegibles = elegibles.head(limite)
    filas = []
    for n, (_, r) in enumerate(elegibles.iterrows(), 1):
        codigo = str(r["codigo"])
        anio = int(r["anio_estreno"])
        alternativas, estado = "", "ok"
        if codigo in overrides:
            if overrides[codigo] == "-1":
                filas.append({"codigo": codigo, "tmdb_estado": "descartado_manual"})
                continue
            det = detalles(tmdb, int(float(overrides[codigo])))
            reg, _ = registro_desde_detalle(det, None, "manual", "corregido a mano")
            estado = "manual"
        else:
            evaluados, crudos = buscar(tmdb, r["titulo"], anio, r["tipo_origen"], int(r["entradas"]), min_entradas_relevancia)
            crudos_txt = " || ".join(texto_crudo(c) for c in crudos)
            if not evaluados:
                filas.append({"codigo": codigo, "tmdb_estado": "sin_resultados", "tmdb_candidatos": "TMDB devolvió: " + crudos_txt})
                continue
            mejor = evaluados[0]
            det = detalles(tmdb, mejor["cand"]["id"])
            conf, nota = mejor["confianza"], mejor.get("nota", "")
            reg, paises = registro_desde_detalle(det, mejor["sim"], conf, nota)
            if r["tipo_origen"] == "nacional" and paises and "AR" not in paises and conf in ("alta", "media"):
                conf = "baja"
                nota = (nota + " | " if nota else "") + "película nacional sin AR en países de producción"
                reg["tmdb_confianza"], reg["tmdb_nota"] = conf, nota
            alternativas = " || ".join(texto_candidato(e) for e in evaluados[:3])
            if conf != "alta" and crudos_txt:
                alternativas += " || TMDB devolvió: " + crudos_txt
        reg.update({"codigo": codigo, "tmdb_estado": estado, "tmdb_candidatos": alternativas})
        filas.append(reg)
        if verbose and n % 25 == 0:
            print(f"  {n}/{len(elegibles)} películas procesadas ({tmdb.pedidos} pedidos)", flush=True)
    res = pd.DataFrame(filas) if filas else pd.DataFrame(columns=["codigo", "tmdb_estado"])
    out = df.merge(res, on="codigo", how="left")
    out["tmdb_estado"] = out["tmdb_estado"].fillna("no_buscado")
    enteras = ["tmdb_id", "duracion_min", "votos_tmdb", "presupuesto_usd", "recaudacion_mundial_usd", "g_sin_mapeo"]
    enteras += [f"g_{n}" for n in GENEROS_ENCC]
    for c in enteras:
        if c in out:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    for c in ("es_adaptacion_videojuego", "tema_videojuego"):
        if c in out:
            out[c] = out[c].astype("boolean")
    return out


def resumen(out, min_entradas):
    com = out[out["es_estreno_comercial"]]
    objetivo = com[com["entradas"] >= min_entradas]
    buscadas = objetivo[objetivo["tmdb_estado"] != "no_buscado"]
    lineas = [f"Estrenos comerciales: {len(com)} | con >= {min_entradas} entradas: {len(objetivo)} | buscadas en esta corrida: {len(buscadas)}"]
    if len(buscadas) < len(objetivo):
        lineas.append(f"   (sin buscar: {len(objetivo) - len(buscadas)}, por --limite)")
    lineas.append("Estado: " + str(buscadas["tmdb_estado"].value_counts().to_dict()))
    lineas.append("Confianza: " + str(buscadas["tmdb_confianza"].value_counts().to_dict()))
    bien = buscadas[buscadas["tmdb_confianza"].isin(["alta", "media", "manual"])]
    if len(buscadas):
        lineas.append(f"Entradas de las buscadas con confianza alta/media/manual: {bien['entradas'].sum() / buscadas['entradas'].sum():.1%}")
    dudosas = buscadas[~buscadas["tmdb_confianza"].isin(["alta", "media", "manual"])].sort_values("entradas", ascending=False)
    if len(dudosas):
        lineas.append("Las 10 dudosas o sin resultado con más entradas (van a tmdb_revisar.csv):")
        for _, r in dudosas.head(10).iterrows():
            lineas.append(f"   {r['titulo']} ({r['anio_estreno']}), {int(r['entradas']):,} entradas -> {r['tmdb_estado']} / {r['tmdb_confianza']}")
    ad = buscadas[buscadas["es_adaptacion_videojuego"].fillna(False).astype(bool)]
    lineas.append(f"Marcadas como adaptación de videojuego: {len(ad)}")
    for _, r in ad.sort_values("entradas", ascending=False).iterrows():
        lineas.append(f"   {r['titulo']} ({r['anio_estreno']}), {int(r['entradas']):,} entradas")
    lineas.append("Casos de control (deberían figurar como adaptación si fueron buscados):")
    for clave in CASOS_CONTROL:
        for _, r in com[com["titulo"].str.contains(clave, regex=False)].iterrows():
            if r["tmdb_estado"] == "no_buscado":
                lineas.append(f"   {r['titulo']}: no buscada")
            else:
                lineas.append(f"   {r['titulo']}: adaptación={bool(r['es_adaptacion_videojuego'])} (confianza {r['tmdb_confianza']})")
    return "\n".join(lineas)


def armar_revisar(out, min_entradas):
    com = out[out["es_estreno_comercial"] & (out["entradas"] >= min_entradas)].copy()
    top100 = set(com.sort_values("entradas", ascending=False).head(100)["codigo"])
    mask = (com["tmdb_estado"] == "sin_resultados") | (com["tmdb_confianza"] == "baja") | \
           ((com["tmdb_confianza"] == "media") & com["codigo"].isin(top100))
    rev = com[mask].sort_values("entradas", ascending=False)
    cols = [c for c in ["codigo", "titulo", "anio_estreno", "entradas", "tmdb_estado", "tmdb_confianza", "tmdb_id",
                        "titulo_tmdb", "fecha_estreno_mundial", "tmdb_similitud", "tmdb_nota", "tmdb_candidatos"] if c in rev]
    rev = rev[cols].copy()
    rev["tmdb_id_corregido"] = ""
    return rev


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", nargs="?", default="incaa_estrenos_comerciales.csv",
                    help="CSV limpio del INCAA (por defecto: incaa_estrenos_comerciales.csv)")
    ap.add_argument("--salida", default=".", help="carpeta de salida")
    ap.add_argument("--min-entradas", type=int, default=1000, help="solo busca películas con al menos estas entradas")
    ap.add_argument("--limite", type=int, default=None, help="procesa solo las N más vistas (para probar)")
    ap.add_argument("--min-entradas-relevancia", type=int, default=50000,
                    help="para estrenos extranjeros con al menos estas entradas, acepta la coincidencia por relevancia y año")
    ap.add_argument("--overrides", default=None, help="CSV con columnas codigo,tmdb_id_corregido")
    args = ap.parse_args(argv)

    clave = os.environ.get("TMDB_API_KEY", "").strip() or DEFAULT_TMDB_KEY
    if not clave:
        sys.exit("Falta la variable de entorno TMDB_API_KEY (clave v3 o token v4 de TMDB). Mirá el LEEME.")

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    if not Path(args.entrada).exists():
        sys.exit(f"No se encontró el archivo de entrada '{args.entrada}'. Verificá que exista en el directorio actual.")
    df = pd.read_csv(args.entrada, dtype={"codigo": str})
    requeridas = {"codigo", "titulo", "anio_estreno", "entradas", "tipo_origen", "es_estreno_comercial"}
    if requeridas - set(df.columns):
        sys.exit(f"Al CSV le faltan columnas: {sorted(requeridas - set(df.columns))}. ¿Es la salida de limpiar_incaa.py?")

    tmdb = Tmdb(clave, salida / "tmdb_cache.json")
    try:
        out = enriquecer(df, tmdb, args.min_entradas, cargar_overrides(args.overrides), args.limite,
                         min_entradas_relevancia=args.min_entradas_relevancia)
    finally:
        tmdb.guardar_cache()

    # Guardar con el nombre oficial del entregable y réplica para compatibilidad
    out.to_csv(salida / "incaa_peliculas_enriquecidas.csv", index=False, encoding="utf-8")
    out.to_csv(salida / "incaa_con_genero.csv", index=False, encoding="utf-8")
    armar_revisar(out, args.min_entradas).to_csv(salida / "tmdb_revisar.csv", index=False, encoding="utf-8")
    print(resumen(out, args.min_entradas))
    print(f"\nListo: {salida / 'incaa_peliculas_enriquecidas.csv'} y {salida / 'tmdb_revisar.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
