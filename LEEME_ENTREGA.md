# Carpeta de Entrega: TPO Ciencia de Datos (UADE)
**Docente:** Santiago Martín  
**Dominio:** Industria Cinematográfica y Universo Gaming en Argentina  

---

## 📁 1. Estructura de Datasets y Linaje

Todos los datasets fueron procesados, validados y cuentan con nombres autodescriptivos.

> **💡 Nota sobre `Peliculas_inca_cs_datos.csv`:**  
> Dicho nombre correspondía al archivo exportado originalmente desde la plataforma Tableau del INCAA. Fue procesado y normalizado mediante `00_limpiar_incaa_raw.py` para generar **`incaa_estrenos_comerciales.csv`** (899 estrenos de salas), y posteriormente enriquecido con la API de TMDB en **`incaa_peliculas_enriquecidas.csv`**. Ambas versiones limpias se encuentran en el repositorio.

| Tipo | Archivo | Filas | Columnas | Descripción |
| :--- | :--- | :---: | :---: | :--- |
| **Fuente Raw** | `base-datos-encc-2022-2023.csv` | 3.380 | 548 | Microdatos oficiales de la Encuesta Nacional de Consumos Culturales (SInCA). |
| **Fuente Raw** | `incaa_estrenos_comerciales.csv` | 899 | 16 | Base oficial limpia de estrenos en salas de cine del INCAA (2022-2023). |
| **Documento** | `cuestionario-encc-2022-2023.pdf` | - | - | Cuestionario metodológico oficial de la encuesta con reglas de saltos. |
| **Enriquecido** | `incaa_peliculas_enriquecidas.csv` | 899 | 50 | Base INCAA enriquecida con TMDB: géneros ENCC, adaptaciones de videojuegos (`es_adaptacion_videojuego`) y taquilla. |
| **Limpio ML** | `encc_encuesta_limpia_ml.csv` | 3.380 | 86 | Encuesta ENCC limpia, 100% numérica, sin valores nulos (nulos estructurales resueltos) y codificaciones listas para ML. |
| **Diccionario** | `diccionario_variables_encc.json` | - | - | Diccionario de datos con el tipo, rango (mínimo, máximo) y media de cada variable de la encuesta limpia. |
| **Cruce** | `cruce_demanda_oferta_generos.csv` | 10 | 6 | Tabla comparativa de la demanda declarada en la población (ENCC) frente a las entradas vendidas en salas comerciales (INCAA). |
| **Cruce** | `cruce_gamers_vs_cine.csv` | 2 | 6 | Métricas comparativas de penetración cinematográfica y consumo de Acción/Animación entre jugadores de videojuegos y no jugadores. |
| **Hipótesis** | `resultado_hipotesis_descriptivos.csv` | 3 | 10 | Estadísticas ponderadas divididas por los tres segmentos de la hipótesis: Gamer Core (Consola/PC), Gamer Casual (Móvil) y No Gamer. |
| **Hipótesis** | `resultado_hipotesis_regresiones.csv` | 5 | 6 | Modelos de Regresión Logística multivariada con Odds Ratios controlando por Edad y Nivel Socioeconómico (NSE). |
| **Métricas ML** | `resultado_metricas_clasificacion.csv` | 5 | 6 | Métricas completas de clasificación supervisada del Random Forest (Precision, Recall, F1, Accuracy, ROC-AUC). |
| **Clusters** | `encc_segmentos_clusters.csv` | 3.380 | 87 | Base de la ENCC con la columna `cluster_id` asignada por el algoritmo K-Means (4 arquetipos culturales). |

---

## ⚙️ 2. Scripts del Pipeline de Datos (Ejecutables en orden)

Los scripts están ordenados numéricamente para reproducir todo el flujo desde cero:

```bash
# 1. Enriquecimiento de estrenos INCAA con la API de TMDB
python3 01_enriquecer_incaa_tmdb.py

# 2. Limpieza y codificación de la ENCC (resolución de saltos de cuestionario)
python3 02_limpiar_encc.py

# 3. Cruce de demanda cultural vs taquilla real
python3 03_vincular_encc_incaa.py

# 4. Prueba estadística formal de la hipótesis (Regresión Logística con controles)
python3 04_probar_hipotesis_regresion.py

# 5. Modelado supervisado (Random Forest) y no supervisado (K-Means)
python3 05_modelos_ml_y_clustering.py
```

---

## 🎬 3. Aplicación Funcional (Entregable 6 Obligatorio)

La aplicación interactiva para la Gerencia Comercial y Técnica está desarrollada en **Streamlit + Plotly**.

### Cómo iniciar la aplicación:
```bash
python3 -m streamlit run app.py
```
Se abrirá automáticamente en tu navegador en: **`http://localhost:8501`**.

### Módulos de la Aplicación:
1. **💼 Simulador de Campañas:** Permite seleccionar género, presupuesto publicitario en ARS y estrategia de segmentación, proyectando en tiempo real las entradas vendidas, recaudación, ROI y Costo de Adquisición de Espectador (CAC).
2. **🎯 Validación de la Hipótesis:** Gráficos interactivos de penetración y la tabla de Odds Ratios controlando por Edad y NSE.
3. **🍿 Mercado y Taquilla (INCAA):** Explorador de las 5 adaptaciones de videojuegos y comparativa de oferta vs demanda.
4. **👥 Segmentación de Audiencias (Clusters):** Visualización de los 4 arquetipos de consumidores culturales argentinos.
