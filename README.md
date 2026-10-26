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
├── app.py                                  <-- Aplicación interactiva Streamlit
│
├── 🐍 Scripts del Pipeline (Ejecutables en orden):
│   ├── 01_enriquecer_incaa_tmdb.py         <-- Cruce de taquilla INCAA con API de TMDB
│   ├── 02_limpiar_encc.py                  <-- Limpieza y resolución de nulos estructurales de la ENCC
│   ├── 03_vincular_encc_incaa.py           <-- Cruce cuantitativo de oferta (salas) vs demanda (encuesta)
│   ├── 04_probar_hipotesis_regresion.py    <-- Modelos de Regresión Logística con controles de Edad y NSE
│   └── 05_modelos_ml_y_clustering.py       <-- Random Forest (ROC-AUC 0.80) y K-Means (k=4)
│
├── 📊 Datasets Procesados y Limpios:
│   ├── incaa_peliculas_enriquecidas.csv    <-- 899 estrenos comerciales con géneros y tags gaming
│   ├── encc_encuesta_limpia_ml.csv         <-- 3.380 encuestados, 86 columnas numéricas listas para ML
│   ├── diccionario_variables_encc.json     <-- Diccionario con tipos y rangos de las variables
│   ├── cruce_demanda_oferta_generos.csv    <-- Comparativa de % de preferencia vs % de taquilla real
│   ├── cruce_gamers_vs_cine.csv            <-- Métricas de cine en gamers vs no gamers
│   ├── resultado_hipotesis_descriptivos.csv<-- Descriptivos ponderados: Core vs Mobile vs No Gamer
│   ├── resultado_hipotesis_regresiones.csv <-- Tabla de Odds Ratios controlando por Edad y NSE
│   └── encc_segmentos_clusters.csv         <-- Base ENCC con la asignación de arquetipos culturales
│
└── 📘 repaso/
    └── fundamentos_teoricos_y_defensa.md   <-- Guía de estudio para la defensa: justificación de cada modelo y respuestas a preguntas del profesor
```

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
