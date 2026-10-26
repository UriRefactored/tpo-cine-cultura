# Fundamentos Teóricos, Decisiones Metodológicas y Guía para la Defensa
**Materia:** Ciencia de Datos — UADE  
**Docente:** Santiago Martín  
**Proyecto:** "Cine & Gaming en Argentina: Análisis de Demanda y Oferta para Distribución y Exhibición"

---

## 1. El Problema de Negocio y la Hipótesis

### Hipótesis Validada con la Cátedra
> *“Los jugadores de consola/PC van más al cine y prefieren Acción/Aventura, Ciencia ficción y Terror; una campaña de películas de universo gaming dirigida a ese segmento y a esos géneros rinde más que una dirigida a jugadores en general.”*

### Las 3 Preguntas de la Diapositiva 4
1. **¿Qué proponemos resolver?**  
   Optimizar la asignación presupuestaria publicitaria de distribuidoras y exhibidoras de cine en Argentina. Tradicionalmente, las campañas de películas de videojuegos (ej. *Mario*, *Uncharted*, *Sonic*, *FNAF*) se pautan de manera indiferenciada hacia "gamers" en general o hacia público joven genérico. Demostramos empíricamente que los jugadores de smartphone/tablet tienen un comportamiento cinematográfico pasivo, mientras que los **jugadores Core (PC/Consola)** tienen una tasa de asistencia de **62.2%** y una preferencia 3x superior por Acción, Sci-Fi y Terror.
2. **¿Para quién?**  
   La **Gerencia Comercial y de Marketing** (distribuidoras como Warner, Sony, UIP, Disney y cadenas como Hoyts/Cinemark, Cinépolis, Showcase).
3. **¿Cómo entrega valor?**  
   **Ahorro de plata y mejora de ROI:** Evita el desperdicio publicitario en audiencias casuales masivas y concentra la pauta en canales de nicho gamer de alta conversión (Twitch, Discord, Steam, YouTube Gaming, eventos esports), reduciendo el Costo por Espectador Adquirido (CAC).

---

## 2. Decisiones de Ingeniería de Datos (ETL)

### A. Integración Multifuente (Heterogeneidad de Datos)
El trabajo combina **tres fuentes de datos reales e independientes**:
1. **ENCC 2022-2023 (SInCA):** Base de microdatos de **demanda individual** (3.380 encuestados con factores de expansión y ponderación poblacional).
2. **Estrenos Comerciales INCAA (2022-2023):** Base oficial de **oferta de mercado** (73.17 millones de entradas y 899 películas comerciales).
3. **The Movie Database (TMDB API):** Enriquecimiento programático vía requests REST con caché hash local (`tmdb_cache.json`) para clasificar franquicias, presupuestos, palabras clave de videojuegos y mapeo de géneros.

### B. Tratamiento de Nulos Estructurales (*Structural Missings* vs *MCAR*)
* **El problema:** En encuestas complejas con saltos de cuestionario, cuando un individuo responde `cine1 == "NO"`, todas las preguntas subsecuentes de frecuencia (`cine3`, `cine4`) y géneros vistos (`cine7_*`) quedan con valores `NaN`.
* **La decisión metodológica:** En ciencia de datos, imputar estos nulos con la media/mediana o eliminar las filas (*listwise deletion*) generaría un **sesgo de selección (*survivorship bias*) catastrófico**, falseando la penetración real del cine en el país. 
* **La solución:** Se identificaron como **ceros estructurales**: quien no fue al cine vio 0 películas de acción en salas. Se imputó con `0` (ausencia de consumo), preservando a los 3.380 individuos para entrenar modelos sobre el universo total de la población.

### C. Estandarización de Escalas y Encodings
* **Ordinal a Continuo:** Frecuencias de consumo expresadas en texto (*"Todas las semanas"*, *"Una vez al mes"*, etc.) fueron convertidas a días/visitas anuales equivalentes (52, 12, 3, 0), permitiendo operaciones matemáticas y distancia euclidiana en modelos.
* **One-Hot Encoding:** Variables cualitativas no jerárquicas (Región, Género, Tamaño de Aglomerado) fueron descompuestas en columnas binarias `{0, 1}` para evitar inducir un orden artificial que distorsione algoritmos lineales.

### D. Ponderadores Muestrales (`sample_weight=ponderador`)
La ENCC utiliza un diseño muestral probabilístico estratificado. Para que los modelos no sobrerrepresenten a regiones sobremuestreadas, se incorporó el `ponderador` muestral oficial en el cálculo de métricas, descriptivos y en la función de pérdida (*loss function*) de los clasificadores.

---

## 3. Justificación de los Modelos de Minería de Datos

> *"¿Cuál aplicaron y qué modelo entrenaron? Sobre todo: por qué ese y no otro."* (Diapositiva 6 y 7).

### Modelo 1: Regresión Logística Multivariada con Controles (Inferencia Causal)
* **¿Por qué se eligió?**  
  El profesor Santiago Martín estableció una condición metodológica precisa: *"Si la diferencia desaparece al controlar por edad, la hipótesis se refuta"*.  
  Los árboles de decisión o modelos de ensamble son excelentes predictores pero funcionan como "cajas negras": no aíslan el efecto marginal *ceteris paribus* de una variable específica. La Regresión Logística permite estimar el coeficiente de una variable manteniendo fijas todas las demás.
* **Mecánica del Modelo:**  
  Modela el logaritmo de los momios (*log-odds*):
  $$\ln\left(\frac{p}{1-p}\right) = \beta_0 + \beta_{\text{core}} X_{\text{core}} + \beta_{\text{mobile}} X_{\text{mobile}} + \beta_{\text{edad}} X_{\text{edad}} + \beta_{\text{nse}} X_{\text{nse}}$$
* **Interpretación de Odds Ratios ($e^\beta$):**  
  * **Asistencia al cine:** $\text{OR}_{\text{core}} = 2.22$ ($p < 0.001$). A misma edad y mismo nivel socioeconómico, un jugador core tiene **2.22 veces más probabilidades de ir al cine** que un no jugador.
  * **Acción/Aventura:** $\text{OR}_{\text{core}} = 2.68$.
  * **Ciencia Ficción:** $\text{OR}_{\text{core}} = 2.50$.
  * **Terror:** $\text{OR}_{\text{core}} = 2.12$.
* **Conclusión académica:** **La hipótesis NO se refuta.** El efecto del gaming en consola/PC es propio, robusto e independiente de la juventud o el poder adquisitivo.

### Modelo 2: Random Forest Classifier (Modelado Predictivo de Audiencia)
* **¿Por qué se eligió?**  
  Para predecir la asistencia general al cine capturando interacciones no lineales y relaciones complejas entre variables (por ejemplo, personas de cierta edad con consumo intensivo de streaming y afinidad por géneros específicos).
* **Parámetros aplicados:** 150 estimadores (*trees*), `max_depth=8` (para evitar sobreajuste / *overfitting*), y partición estratificada 80/20.
* **Resultados:** **ROC-AUC = 0.795**, **Accuracy ponderada = 73.3%**.
* **Feature Importance (Reducción de Impureza de Gini):** Demostró que la *diversidad de géneros en streaming* (0.114) y la *diversidad de juegos jugados* (0.046) se encuentran entre los predictores más fuertes de asistencia a salas, validando la tesis de un público audiovisual omnívoro.

### Modelo 3: K-Means Clustering (Segmentación No Supervisada de Audiencias)
* **¿Por qué se eligió?**  
  Permite descubrir agrupamientos naturales de consumidores sin forzar etiquetas preexistentes.
* **Preprocesamiento:** Se aplicó `StandardScaler` (normalización $Z$-score) para equiparar la escala entre variables de frecuencia continua y variables binarias, evitando distorsiones de distancia euclidiana.
* **Arquetipos identificados ($k=4$):**
  * **Cluster 2 ("Gamer y Cinéfilo Joven" - 21.4% de los argentinos):** 100% jugadores de videojuegos activos (205 días al año), 53% va a salas de cine y tienen el mayor apetito por estrenos de impacto visual y comunitario.

---

## 4. Herramientas y Stack Tecnológico

| Capa | Tecnología | Justificación |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.9 | Estándar de la industria para ciencia de datos y reproducibilidad. |
| **Manipulación** | Pandas & NumPy | Procesamiento vectorizado eficiente sobre 548 columnas y 3.380 registros. |
| **Machine Learning** | Scikit-Learn | Implementación de Regresión Logística, Random Forest, K-Means, métricas (ROC-AUC, F1) y pipelines de preprocesamiento. |
| **Visualización** | Plotly Express & Graph Objects | Gráficos vectoriales e interactivos que permiten inspeccionar valores al pasar el cursor y que *"se leen desde el fondo del aula"*. |
| **Aplicación Funcional** | Streamlit | Framework de aplicaciones ejecutivas en Python, permitiendo sliders, simulaciones en vivo y visualizaciones sin latencia. |

---

## 5. Preguntas Típicas del Docente y Cómo Responderlas

### P1: *"¿Por qué dicen que la hipótesis se confirma si los gamers son más jóvenes y los jóvenes van más al cine?"*
> **Respuesta:** *"Justamente para evitar esa trampa metodológica aplicamos una Regresión Logística multivariada introduciendo la Edad y el Nivel Socioeconómico como variables de control. Si el fenómeno fuera puramente etario, el coeficiente de Gamer Core se hubiera reducido a cero (Odds Ratio cercano a 1.0). Sin embargo, el Odds Ratio se mantuvo en 2.22 ($p < 0.001$), lo que demuestra que a idéntica edad y nivel económico, jugar en PC/consola confiere una afinidad cultural independiente y estadísticamente significativa con la asistencia a salas."*

### P2: *"¿Por qué dividieron entre Gamer Core (PC/Consola) y Gamer Casual (Celular)?"*
> **Respuesta:** *"Porque el mercado del gaming es heterogéneo. La persona que juega Candy Crush en el colectivo tiene hábitos culturales pasivos similares al no jugador (45% de asistencia al cine y baja afinidad por géneros narrativos). En cambio, el usuario de PC/Consola invierte tiempo, hardware y dinero en experiencias inmersivas, lo que se traduce en un 62.2% de asistencia al cine y un 40% de preferencia por Acción y Aventura. Tratar a todos como 'gamers' diluye el presupuesto publicitario."*

### P3: *"¿Cómo se conecta esto con la taquilla real del INCAA?"*
> **Respuesta:** *"La ENCC nos muestra la demanda declarada, pero el INCAA nos muestra la plata real que se pagó en boleterías. Comprobamos que las 5 películas de franquicias de videojuegos vendieron 6.18 millones de entradas (el 8.4% de toda la taquilla argentina), y que los 3 géneros preferidos por los gamers core (Acción, Ciencia Ficción y Terror) concentraron más de 75 millones de entradas acumuladas. El caso de 'Five Nights at Freddy's' (1.2M de entradas) es el ejemplo perfecto de cómo el cruce entre Gaming y Terror llena salas en Argentina."*
