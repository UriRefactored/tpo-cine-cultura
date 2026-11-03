# Cine & Gaming Analytics: Asistencia a Salas y Universo Gamer en Argentina
**Universidad Argentina de la Empresa (UADE)**  
**Materia:** Ciencia de Datos — Trabajo Práctico Obligatorio  
**Docente:** Santiago Martín  

---

## 🎯 Objetivo e Hipótesis del Proyecto

> **Hipótesis Validada con la Cátedra:**  
> *“Los jugadores de consola/PC van más al cine y prefieren Acción/Aventura, Ciencia ficción y Terror; una campaña de películas de universo gaming dirigida a ese segmento y a esos géneros rinde más que una dirigida a jugadores en general.”*

* **Pregunta de Negocio:** ¿A qué segmento de jugadores y con qué géneros cinematográficos conviene apuntar las campañas de marketing de una distribuidora o exhibidora en Argentina?
* **Audiencia del Proyecto:** Gerencia Comercial y Técnica. Enfocado en decisiones de inversión, ahorro publicitario y retorno de taquilla.
* **Fuentes de Datos Integradas:**
  1. **ENCC 2022-2023 (SInCA):** Encuesta representativa nacional de 3.380 individuos con factores de expansión y ponderación muestral.
  2. **Estrenos Comerciales INCAA (2022-2023):** 73.17 millones de entradas en 899 títulos en salas de cine.
  3. **The Movie Database (TMDB API):** Enriquecimiento de franquicias, adaptaciones de videojuegos y presupuestos.

---

## 🚀 Guía de Inicio Rápido (Para correr en cualquier compu)

Seguí estos pasos para clonar y levantar el proyecto en tu máquina en menos de 2 minutos:

### 1. Clonar el repositorio
Abrí tu terminal y ejecutá:
```bash
git clone <URL_DE_ESTE_REPOSITORIO>
cd <CARPETA_DEL_REPOSITORIO>
```

### 2. (Opcional recomendado) Crear entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate       # En Mac / Linux
# venv\Scripts\activate        # En Windows PowerShell
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Abrir la Aplicación Interactiva (Entregable 6)
```bash
streamlit run app.py
```
*(Si no te abre automáticamente, ingresá en tu navegador a: **`http://localhost:8501`**)*.

---

## 💻 ¿Qué hace la Aplicación Funcional (`app.py`)?

La app cuenta con 4 módulos interactivos pensados para la defensa oral de 15 minutos:

1. **💼 Simulador de Campañas (Gerencia Comercial):** Permite simular el lanzamiento de una película (género, presupuesto en ARS y target gamer) para estimar público alcanzable, venta de entradas, recaudación proyectada, ROI publicitario y Costo por Espectador Adquirido (CAC).
2. **🎯 Validación de la Hipótesis:** Gráficos de penetración y la tabla de **Regresión Logística con controles de Edad y NSE** que comprueban que la hipótesis se sostiene.
3. **🍿 Mercado y Taquilla (INCAA):** Explorador de los estrenos de cartelera argentina y análisis de las 5 películas de franquicias gaming (*Super Mario Bros*, *Sonic 2*, *FNAF*, *Uncharted*, *Gran Turismo*) que vendieron 6.18 millones de entradas.
4. **👥 Segmentación de Audiencias (Clusters):** Visualización de los 4 arquetipos culturales identificados con K-Means.

---

## 📂 Estructura del Repositorio

```text
├── README.md                               <-- Este archivo
├── requirements.txt                        <-- Dependencias de Python
├── app.py                                  <-- Aplicación interactiva Streamlit (Entregable 6)
│
├── 📁 Fuentes Originales y Datos Crudos:
│   ├── base-datos-encc-2022-2023.csv       <-- Microdatos oficiales ENCC (SInCA), 3.380 encuestados
│   ├── cuestionario-encc-2022-2023.pdf     <-- Cuestionario oficial y manual de saltos
│   └── incaa_estrenos_comerciales.csv      <-- 899 estrenos de salas comerciales limpios del INCAA
│
├── 🐍 Scripts del Pipeline (Ejecutables en orden de reproducción):
│   ├── 00_limpiar_incaa_raw.py             <-- Limpieza del export crudo de Tableau del INCAA
│   ├── 01_enriquecer_incaa_tmdb.py         <-- Cruce de taquilla INCAA con API de TMDB
│   ├── 02_limpiar_encc.py                  <-- Limpieza y resolución de nulos estructurales de la ENCC
│   ├── 03_vincular_encc_incaa.py           <-- Cruce cuantitativo de oferta (salas) vs demanda (encuesta)
│   ├── 04_probar_hipotesis_regresion.py    <-- Modelos de Regresión Logística con controles de Edad y NSE
│   └── 05_modelos_ml_y_clustering.py       <-- Random Forest (ROC-AUC 0.80) y K-Means (k=4)
│
├── 📊 Datasets Procesados y Enriquecidos:
│   ├── incaa_peliculas_enriquecidas.csv    <-- 899 estrenos comerciales con 10 géneros y tags gaming
│   ├── encc_encuesta_limpia_ml.csv         <-- 3.380 encuestados, 86 columnas numéricas listas para ML
│   ├── diccionario_variables_encc.json     <-- Diccionario con tipos, rangos y medias de variables
│   ├── cruce_demanda_oferta_generos.csv    <-- Comparativa de % de preferencia vs % de taquilla real
│   ├── cruce_gamers_vs_cine.csv            <-- Métricas de cine en gamers vs no gamers
│   ├── resultado_hipotesis_descriptivos.csv<-- Descriptivos ponderados: Core vs Mobile vs No Gamer
│   ├── resultado_hipotesis_regresiones.csv <-- Tabla de Odds Ratios controlando por Edad y NSE
│   └── encc_segmentos_clusters.csv         <-- Base ENCC con la asignación de arquetipos culturales (k=4)
│
└── 📘 repaso/
    └── fundamentos_teoricos_y_defensa.md   <-- Guía de estudio para la defensa: justificación de cada modelo y respuestas a preguntas del profesor
```

---

## 📊 Datasets del Proyecto: Origen, Linaje, Transformaciones y Uso

El proyecto integra dos fuentes oficiales de datos de Argentina (oferta y demanda) y las enriquece con la base internacional de The Movie Database (TMDB):

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 1. DATOS CRUDOS / FUENTES                              │
│                                                                                        │
│  [Peliculas_inca_cs_datos.csv]                [base-datos-encc-2022-2023.csv]          │
│  (Export crudo Tableau INCAA)                  (Microdatos ENCC SInCA, 3.380 indiv.)   │
│              │                                                │                        │
│     00_limpiar_incaa_raw.py                           02_limpiar_encc.py               │
│              ▼                                                ▼                        │
│  [incaa_estrenos_comerciales.csv]             [encc_encuesta_limpia_ml.csv]            │
│  (899 estrenos comerciales limpios)           (86 variables numéricas, sin nulos)      │
│              │                                                │                        │
│     01_enriquecer_incaa_tmdb.py                               │                        │
│              ▼                                                │                        │
│  [incaa_peliculas_enriquecidas.csv]                           │                        │
│  (Adaptaciones VJ, géneros, presupuesto)                      │                        │
└───────────────────────┬───────────────────────────────────────┬────────────────────────┘
                        │                                       │
                        ▼                                       ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              2. CRUCE, HIPÓTESIS Y MODELOS                             │
│                                                                                        │
│   03_vincular_encc_incaa.py ──────► [cruce_demanda_oferta_generos.csv]                 │
│                                ──────► [cruce_gamers_vs_cine.csv]                      │
│                                                                                        │
│   04_probar_hipotesis_regresion.py ─► [resultado_hipotesis_regresiones.csv] (Odds Ratios)│
│                                    ─► [resultado_hipotesis_descriptivos.csv]           │
│                                                                                        │
│   05_modelos_ml_y_clustering.py ───► [encc_segmentos_clusters.csv] (K-Means k=4)      │
│                                ───► Random Forest (ROC-AUC 0.80, Accuracy 73.3%)      │
└───────────────────────────────────────────────────┬────────────────────────────────────┘
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         3. APLICACIÓN INTERACTIVA (STREAMLIT)                          │
│                                                                                        │
│                                      [app.py]                                          │
│         • Simulador Comercial de Inversión y Retorno en Taquilla                       │
│         • Validación de Hipótesis (Regresión Logística multivariada)                   │
│         • Explorador de Cartelera y Adaptaciones Gaming INCAA                          │
│         • Segmentación de Arquetipos Culturales                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 💡 Aclaración sobre `Peliculas_inca_cs_datos.csv` vs `incaa_estrenos_comerciales.csv`
* **¿Qué era `Peliculas_inca_cs_datos.csv`?**  
  Fue el nombre original del archivo exportado directamente desde el tablero de Tableau de la Gerencia de Fiscalización del INCAA (*"Cantidad de espectadores por película estrenada"*). Venía en formato de texto tabulado con codificación UTF-16, separadores de miles estadounidenses (`3,562,856`) y fechas en formato `M/D/YYYY`.
* **¿Por cuál fue transformado y reemplazado?**  
  1. El script `00_limpiar_incaa_raw.py` procesó ese archivo crudo, filtró eventos y muestras no comerciales, normalizó números y fechas y generó **`incaa_estrenos_comerciales.csv`** (899 estrenos de salas comerciales).  
  2. Luego, el script `01_enriquecer_incaa_tmdb.py` tomó esa base y consultó la API de TMDB para clasificar los 10 géneros e identificar adaptaciones de videojuegos, generando el dataset enriquecido definitivo: **`incaa_peliculas_enriquecidas.csv`**.
* En el repositorio y en todos los scripts se utiliza directamente **`incaa_estrenos_comerciales.csv`** como fuente base y **`incaa_peliculas_enriquecidas.csv`** como dataset final enriquecido, garantizando total reproducibilidad.

---

### 📋 Detalle de Datasets y su Uso en el Proyecto

#### A. Fuentes Originales y Datos Crudos
1. **`base-datos-encc-2022-2023.csv`** (8.4 MB | 3.380 filas × 548 columnas):
   * **Origen:** Sistema de Información Cultural de la Argentina (SInCA) - Secretaría de Cultura de la Nación.
   * **Contenido:** Microdatos completos a nivel individuo representativos de la población argentina urbana de 13 años y más. Contiene factores de expansión (`ponderador`), módulos de cine, hábitos digitales, plataformas de streaming y uso de videojuegos.
   * **Uso:** Archivo de entrada para `02_limpiar_encc.py`.
2. **`cuestionario-encc-2022-2023.pdf`** (670 KB):
   * **Origen:** Documento metodológico oficial del SInCA.
   * **Uso:** Consulta de reglas de ruteo y saltos de preguntas del cuestionario (fundamental para justificar los nulos estructurales).
3. **`incaa_estrenos_comerciales.csv`** (142 KB | 899 filas × 16 columnas):
   * **Origen:** Tablero oficial de fiscalización del INCAA (estrenos 2022 y 2023).
   * **Contenido:** Código de película, título, fecha y mes de estreno, origen (nacional vs extranjero), entradas vendidas y recaudación en ARS.
   * **Uso:** Archivo de entrada para `01_enriquecer_incaa_tmdb.py` y análisis de taquilla base.

#### B. Datasets Limpios y Enriquecidos para Modelado
4. **`incaa_peliculas_enriquecidas.csv`** (309 KB | 899 filas × 50 columnas):
   * **Origen:** Generado por `01_enriquecer_incaa_tmdb.py` a partir de `incaa_estrenos_comerciales.csv` cruzado con la API v3 de TMDB.
   * **Contenido:** Variables de catálogo enriquecidas: 10 géneros cinematográficos mapeados a las preguntas de la ENCC (`g_accion_aventura`, `g_ciencia_ficcion`, `g_terror`, etc.), flag de franquicia de videojuegos (`es_adaptacion_videojuego`), presupuesto (`presupuesto_usd`), recaudación mundial (`recaudacion_mundial_usd`), rating y popularidad.
   * **Uso:** Insumo principal de oferta para `03_vincular_encc_incaa.py`, `04_probar_hipotesis_regresion.py` y la pestaña de Mercado en `app.py`.
5. **`encc_encuesta_limpia_ml.csv`** (660 KB | 3.380 filas × 86 columnas):
   * **Origen:** Generado por `02_limpiar_encc.py` a partir de `base-datos-encc-2022-2023.csv`.
   * **Contenido:** Base 100% numérica, sin valores nulos. Los nulos estructurales (personas que no asisten al cine o no juegan videojuegos) fueron imputados en 0 en lugar de eliminar filas. Incluye variables de segmentación gamer (`vj_disp_consola`, `vj_disp_pc_escritorio`, `vj_frecuencia_anual_est`), hábitos de streaming, nivel educativo ordenado y nivel socioeconómico (`nse_orden`).
   * **Uso:** Insumo de demanda para `03_vincular_encc_incaa.py`, `04_probar_hipotesis_regresion.py`, entrenamiento de Random Forest en `05_modelos_ml_y_clustering.py` y el simulador de `app.py`.
6. **`diccionario_variables_encc.json`** (8.8 KB):
   * **Origen:** Generado automáticamente por `02_limpiar_encc.py`.
   * **Contenido:** Metadatos de cada una de las 86 variables (tipo de dato, valor mínimo, valor máximo y promedio muestral).

#### C. Datasets de Validación de Hipótesis y Resultados
7. **`cruce_demanda_oferta_generos.csv`** (10 filas × 6 columnas):
   * **Origen:** Generado por `03_vincular_encc_incaa.py`.
   * **Contenido:** Comparación entre el porcentaje de la población que declara preferir cada género en la ENCC y el porcentaje de entradas reales vendidas en salas de cine según el INCAA, con el ratio de saturación taquilla vs demanda.
8. **`cruce_gamers_vs_cine.csv`** (2 filas × 6 columnas):
   * **Origen:** Generado por `03_vincular_encc_incaa.py`.
   * **Contenido:** Resumen comparativo de penetración cinematográfica y preferencia de géneros entre jugadores de videojuegos y no jugadores.
9. **`resultado_hipotesis_descriptivos.csv`** (3 filas × 10 columnas):
   * **Origen:** Generado por `04_probar_hipotesis_regresion.py`.
   * **Contenido:** Métricas descriptivas ponderadas divididas en los tres grupos de la hipótesis: Gamer Core (18.1% de la población, edad media 26.3), Gamer Casual (14.7%, edad media 33.0) y No Gamer (67.2%, edad media 47.8).
10. **`resultado_hipotesis_regresiones.csv`** (5 filas × 6 columnas):
    * **Origen:** Generado por `04_probar_hipotesis_regresion.py`.
    * **Contenido:** Resultados econométricos de las 5 Regresiones Logísticas multivariadas (Odds Ratios con controles simultáneos de Edad y NSE) demostrando que la hipótesis se sostiene de forma independiente y estadísticamente significativa.

#### D. Datasets de Segmentación y Machine Learning
11. **`encc_segmentos_clusters.csv`** (667 KB | 3.380 filas × 87 columnas):
    * **Origen:** Generado por `05_modelos_ml_y_clustering.py`.
    * **Contenido:** Base limpia de la ENCC con la columna adicional `cluster_id` generada por el algoritmo K-Means ($k=4$), clasificando a cada individuo en un arquetipo cultural para segmentación comercial.

---

## 📈 Hallazgos Clave para la Defensa Oral (15 Minutos)

1. **El jugador Core de Consola / PC va el doble al cine:** Su tasa de asistencia anual es del **62.2%**, frente al **45.0%** del jugador casual de celular y al **27.0%** del no jugador.
2. **Preferencia marcada por 3 géneros:** Los jugadores Core consumen entre 3 y 5 veces más **Acción / Aventura (40.2%)**, **Ciencia Ficción (28.8%)** y **Terror (16.5%)**.
3. **El control por Edad y NSE confirma la Hipótesis:** Al estimar modelos de Regresión Logística multivariados, el efecto **no desaparece**: a misma edad y mismo nivel socioeconómico, ser Gamer Core multiplica por **2.22** las probabilidades de ir al cine, por **2.68** las de ver Acción, por **2.50** las de Ciencia Ficción y por **2.12** las de Terror.
4. **Respuesta a la Gerencia Comercial:** No conviene pautar hacia "gamers en general". El presupuesto rinde hasta un 38% más concentrándolo en canales específicos de PC/Consola (Steam, Twitch, Discord, YouTube Gaming) para estrenos de Acción, Sci-Fi y Terror comunitario.

---

## 👥 Integrantes del Grupo y Roles (A completar)
* Integrante 1: Dominio del Negocio & Problemática
* Integrante 2: Arquitectura de Datos & ETL
* Integrante 3: Análisis Exploratorio de Datos (EDA)
* Integrante 4: Técnicas de Minería & Modelos Estadísticos
* Integrante 5: Visualización & Storytelling
* Integrante 6: Demostración en vivo de la Aplicación Funcional
