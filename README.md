# Cine y videojuegos en Argentina

**Trabajo Práctico Obligatorio — Ciencia de Datos (UADE)**

> ¿Quienes juegan videojuegos en PC o consola van más al cine que quienes juegan solo en el celular o no juegan?
> ¿Esa diferencia se sostiene al comparar personas de la misma edad y nivel socioeconómico?
> ¿Y qué agrega saber si alguien juega, cuando ya conocemos su perfil demográfico?

Fuentes: **Encuesta Nacional de Consumos Culturales 2022/23** (microdatos oficiales, 3.380 personas) + **estrenos
comerciales INCAA 2022–2023** (899 películas, 74,5 millones de entradas) enriquecidos con **TMDB**.

---

## Resultados principales

Las cifras salen de `outputs/` (generadas por `run_all.py`; las clave están en `outputs/resumen.json`).
Universo: personas de 13 años o más en localidades urbanas de más de 30.000 habitantes.

| Pregunta | Resultado | Evidencia |
|---|---|---|
| ¿Quienes juegan en PC/consola van más al cine? | **Sí.** 62% fue al cine en el último año, contra 45% de quienes juegan solo en el celular y 27% de quienes no juegan. | `descriptivos_segmentos.csv` |
| ¿Se sostiene a igual edad, NSE, género, educación, actividad, región y tamaño de localidad? | **Sí, más chica.** La diferencia ajustada PC/consola vs. no juega es de **+16,5 pp** (IC 95%: 9,9 a 23,1); OR 2,29 (1,66–3,14). Quien juega solo en el celular también va más (+8,4 pp). En 8 variantes de sensibilidad el OR queda entre 2,23 y 2,56. | `asistencia_contrastes.csv`, `asistencia_sensibilidad.csv` |
| Entre quienes fueron al cine, ¿difieren los géneros que vieron? | **No se puede afirmar.** Ningún género difiere tras corregir por 10 comparaciones (Holm). Las diferencias "3 a 5 veces" de la versión anterior medían, sobre toda la población, que unos van más al cine que otros. | `generos_contrastes.csv` |
| ¿El gaming mejora la predicción de quién va al cine? | **No.** Agregar variables de gaming a la demografía no cambia el AUC (−0,006; IC incluye 0). Agregar consumo de streaming sí: +0,048 (IC 0,009–0,080). La regresión logística iguala o supera al Random Forest. | `prediccion_test.csv`, `prediccion_diferencias_auc.csv` |
| ¿Cuánto pesan las adaptaciones de videojuegos en la taquilla? | 5 títulos, 8,3% de las entradas 2022–2023. Solo 2 (Uncharted, Sonic 2) se estrenaron **antes** de la encuesta; Mario, Gran Turismo y FNAF son posteriores y no pudieron influir en las respuestas. | `incaa_adaptaciones_videojuegos.csv` |

**Lectura conjunta.** Jugar en PC/consola está asociado a ir más al cine, y la asociación no se explica solo por la
edad. Pero, para *predecir* asistencia, esa información es en gran parte redundante con la edad y la educación. La
hipótesis inicial ("prefieren Acción, Ciencia ficción y Terror") no tiene respaldo una vez que la medición se hace
correctamente. Todo lo anterior es asociación: la encuesta es transversal y no permite inferir causalidad.

---

## Cómo reproducir

Requiere Python 3.12 (probado en macOS).

```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run_all.py                    # todo el pipeline, ≈ 3 minutos
streamlit run app.py                 # tablero interactivo en http://localhost:8501
open outputs/historia.html           # relato visual (Windows: start outputs\historia.html)
```

`run_all.py` verifica primero el SHA-256 de cada fuente contra `docs/fuentes/manifest.json` y se detiene si algo no
coincide. Todo procedimiento aleatorio usa la semilla `20221101`.

---

## Estructura

```text
data/raw/encc/        Microdatos oficiales ENCC 2022/23 (sin editar)
data/raw/incaa/       Estrenos comerciales INCAA 2022–2023 (insumo más temprano disponible, ver abajo)
data/raw/tmdb/        Snapshot del enriquecimiento TMDB (no se vuelve a consultar la API)
data/processed/       Base analítica ENCC + diccionario de variables
docs/                 Informe académico oficial (Informe_TPO_Cine_y_Videojuegos.pdf)
docs/fuentes/         Cuestionario, metodología y diseño muestral oficiales + manifest.json (URL, fecha, SHA-256)
src/
  comun.py            Rutas, semilla, constantes
  encuesta.py         Estimación con diseño muestral (linealización de Taylor; logística con varianza sándwich)
  graficos.py         Todas las figuras (una sola fuente para la app y los PNG)
  00_, 01_            Limpieza del export crudo INCAA y consulta TMDB (documentados; no se re-ejecutan)
  02_auditar_fuentes  Hashes y controles estructurales
  03_limpiar_encc     Limpieza, auditoría de saltos, registro de transformaciones, diccionario
  04_inferencia       Descriptivos, modelos de asistencia, sensibilidad, géneros con Holm
  05_prediccion       Bloques de variables, CV, test reservado, bootstrap, permutación
  07_mercado_incaa    Cobertura TMDB, géneros en taquilla, cronología de adaptaciones
  08_figuras          Exporta outputs/figuras/*.png
  09_historia         Genera outputs/historia.html desde src/historia_plantilla.html
outputs/tablas/       Todas las tablas de resultados (CSV)
outputs/figuras/      PNG listos para diapositivas
outputs/resumen.json  Cifras clave consumidas por la app
outputs/historia.html Relato visual (storytelling) autocontenido; funciona sin internet
app.py                Demo Streamlit (lee solo de outputs/)
presentacion/         Diapositivas (.pptx) generadas desde outputs/:
                        python presentacion/datos_presentacion.py
                        cd presentacion && npm install && node construir.js
repaso/               Guía para la defensa oral
```

---

## Datos y transformaciones

### Fuentes y frontera de reproducibilidad

| Fuente | Estado | Verificación |
|---|---|---|
| ENCC 2022/23 (SInCA) | Original oficial descargado el 2026-11-02 | SHA-256 en el manifest; 3.380 × 548; IDs únicos |
| Cuestionario, metodología, diseño muestral | PDF oficiales | SHA-256 |
| INCAA estrenos comerciales | **Derivado.** El export crudo de Tableau (`Peliculas_inca_cs_datos.csv`) no está disponible; `src/00_limpiar_incaa_raw.py` documenta cómo se generó. La fecha de corte de los acumulados de entradas no está documentada. | SHA-256; códigos únicos |
| TMDB | Snapshot. La API no se vuelve a consultar. | Títulos y entradas coinciden con el archivo INCAA |

### Decisiones de limpieza (ENCC)

Todas están registradas, con cantidad de casos afectados, en `outputs/tablas/transformaciones_encc.csv`.

- **Mapeos estrictos.** Cada etiqueta original se mapea explícitamente; una etiqueta no prevista hace fallar el script.
- **Salto estructural vs. no respuesta.** `calidad_saltos_encc.csv` verifica, pregunta por pregunta, que solo hay
  datos dentro del universo definido por el cuestionario (cero inconsistencias).
  - Quien no jugó tiene 0 en dispositivos y géneros de juego. Es un cero verdadero, no una imputación.
  - Los géneros vistos en el cine solo existen para quien fue al cine. Fuera de ese universo quedan vacíos (antes se completaban con 0).
  - Ns/Nc queda vacío, sin imputación oculta.
- **Correcciones respecto de la versión anterior:**
  - `ocupado`: buscar la subcadena "trabaj" marcaba como ocupadas también las respuestas "No trabaja…". Había 1.389 casos mal clasificados.
  - Géneros de videojuego (VJ 5): la base trae 12 columnas para los códigos V328–V339, y el cuestionario publicado omite dos.
    La versión anterior desplazaba las etiquetas un lugar (llamaba "novela visual" a Puzzle). Se corrigió por código de variable.
    Evidencia: el 100% de quienes escribieron "¿Cuál?" tiene marcada la columna 12 ("Otro").
  - Educación Ns/Nc ya no se imputa como "secundario completo".
- **Segmentos.**
  - `pc_consola`: jugó en consola, PC de escritorio o notebook.
  - `solo_movil`: jugó solo en celular o tablet.
  - `no_juega`.
  - Un jugador sin dispositivo declarado queda sin segmento.
- **Diccionario semántico** (`data/processed/diccionario_variables.csv`): pregunta de origen, universo, codificación y
  valores observados para cada variable.

---

## Métodos

### Inferencia con diseño muestral (`src/encuesta.py`, `src/04_inferencia.py`)

- **Diseño ENCC:** estratificado por región; primera etapa = localidades. Siguen radios censales, hogares y una
  persona por hogar con cuotas de sexo y edad.
- **Varianza:** linealización de Taylor con estrato = región y UPM = localidad (43 grados de libertad), el mismo
  estimador que `svyglm` en R. CABA tiene una sola localidad; allí se usan las personas como unidades de varianza.
  La base no trae radios censales, así que la aproximación está documentada.
- **Ponderación:** `ponderador` para proporciones y modelos; `expansor` solo para totales de población. El tamaño
  efectivo de muestra por ponderación es ≈ 1.500.
- **Regresión logística ponderada sin regularización.** Se validó contra statsmodels: coeficientes idénticos, y los
  errores estándar difieren solo en el factor de corrección de muestra finita.
- **Especificaciones fijadas antes de estimar:**
  - Cruda.
  - Edad + NSE: spline de edad y NSE categórico.
  - Completa: se suman género, educación, actividad, región y tamaño de localidad.
- **Resultados:** odds ratios y probabilidades ajustadas por estandarización marginal, con diferencias en puntos
  porcentuales.
- **Géneros:** solo entre quienes fueron al cine; familia de 10 contrastes con corrección de Holm.
- **Sensibilidad:** sin ponderar; varianza sin estratos o sin diseño; especificación original; solo 13–49 años;
  ponderadores recortados; segmento sin notebook.

### Minería predictiva (`src/05_prediccion.py`)

- **Objetivo:** asistencia al cine en el último año. Se excluye todo el bloque de cine para evitar *leakage*.
- **Partición:** 80/20 estratificada. El test se usa una sola vez, al final.
- **Selección:** validación cruzada estratificada 5 × 3 en entrenamiento. Imputación, escalado y one-hot se ajustan
  dentro de cada partición (Pipeline).
- **Bloques acumulativos:** demografía → + segmento → + gaming completo → + streaming.
- **Modelos:** baseline, regresión logística y Random Forest.
- **Métricas ponderadas:** ROC-AUC, PR-AUC, Brier, precisión, recall, especificidad, F1 y matriz de confusión
  (umbral elegido en entrenamiento), más calibración.
- **Incertidumbre:** bootstrap por localidad (2.000 réplicas), también para las diferencias de AUC entre bloques.
- **Importancia por permutación** en test (asociación predictiva, no causalidad).
- **Reproducibilidad:** configuración, hiperparámetros elegidos y versiones en `outputs/prediccion_config.json`;
  predicciones del test en `outputs/tablas/`.

---

## Límites

- **Asociación, no causalidad.** Puede haber variables no medidas, como el ingreso del hogar o el interés general
  por el entretenimiento.
- **Diseño muestral aproximado.** No hay radios censales y CABA tiene una sola UPM.
- **Pocos jugadores de PC/consola mayores de 50** (35 casos).
- **Género "visto" según la ENCC ≠ género de catálogo de TMDB.** Las participaciones por género en taquilla suman más
  de 100% porque un título tiene varios géneros.
- **INCAA:** export crudo no disponible y fecha de corte de entradas no documentada.
- **Predicción retrospectiva.** No mide respuesta a campañas ni retorno publicitario. Por eso se retiró el
  simulador de ROI de la versión anterior: sus supuestos (CPM, conversión) no estaban medidos.

---

## Integrantes

_A completar._
