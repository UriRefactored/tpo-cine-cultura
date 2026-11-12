# Plan de trabajo — entrega del 12/11/2026

Contexto: una sola persona trabajando, un día disponible. Ejes de evaluación: (1) fuentes y datos, (2) transformación, minería y análisis, (3) visualización. Objetivo: **excelencia en (1) y (2)**; (3) correcta, honesta y alimentada por resultados generados. La presentación se trabaja después.

Pregunta principal (aprobada por el docente junto con el dataset): ¿qué relación existe entre la plataforma de juego y la asistencia al cine en la población de la ENCC 2022/23, y qué agrega el gaming frente a las variables sociodemográficas?

Universo: población de 13 años o más en localidades urbanas de más de 30.000 habitantes. No generalizar a "todos los argentinos".

## Principios

- Ninguna cifra se escribe a mano: todo número del README, de la app y de las diapositivas sale de `outputs/`.
- Los resultados se reportan aunque no favorezcan la hipótesis original.
- La importancia de variables y los odds ratios se interpretan como asociación, no como causalidad.

## Bloque A — Fuentes y datos (eje 1)

1. Estructura: `data/raw/` (ENCC oficial, INCAA comercial, snapshot TMDB), `data/processed/`, `outputs/`, `docs/fuentes/`. Eliminar duplicados en la raíz (CSV y PDF idénticos por hash).
2. `manifest.json` con URL, fecha y SHA-256 de cada insumo. Frontera de reproducibilidad explícita: el export crudo de Tableau del INCAA no está disponible; `incaa_estrenos_comerciales.csv` es el insumo más temprano. El enriquecimiento TMDB se conserva como snapshot y no requiere llamadas a la API para reproducir los análisis.
3. Corregir `02_limpiar_encc.py`:
   - `es_ocupado` (error confirmado: 1.389 casos mal clasificados).
   - Reemplazar los valores por defecto silenciosos (educación Ns/Nc → 4; frecuencias faltantes → mediana; 99/999) por indicadores de dato desconocido.
   - Validaciones que fallen si aparece una categoría no mapeada.
4. Diccionario semántico: pregunta del cuestionario, universo (saltos), codificación original, transformación y motivo.
5. Reporte de calidad: saltos estructurales vs no respuesta, cobertura TMDB por títulos y por entradas, cronología de estrenos frente al trabajo de campo (nov-2022 a ene-2023).

## Bloque B — Transformación, minería y análisis (eje 2)

1. **Inferencia (reescribir 04)**: regresión logística ponderada sin regularización (statsmodels).
   - Errores estándar por conglomerado de localidad (UPM de primera etapa, estratos = región). Se documenta como aproximación: el radio censal no figura en la base.
   - Modelo crudo y modelo ajustado: edad con splines, NSE categórico, género, educación, ocupación, región y tamaño de localidad.
   - Probabilidades ajustadas y diferencias absolutas en puntos porcentuales, además de odds ratios. Contrastes core vs no jugador, móvil vs no jugador y core vs móvil.
2. **Géneros**: analizados solo entre quienes asistieron al cine (consumo condicionado, no "preferencia"), con corrección de Holm por la familia de 10 géneros.
3. **Sensibilidad**: sin ponderar; core sin notebook; tratamiento de no respuesta.
4. **Predicción (reescribir 05)**:
   - Test final del 20% con semilla fija, sin usarlo para elegir modelos. Validación cruzada en entrenamiento, con preprocesamiento dentro del pipeline.
   - Bloques de variables: demografía → +gaming → +streaming.
   - Modelos: baseline, regresión logística y Random Forest.
   - Métricas: ROC-AUC, PR-AUC, precisión, recall, F1, matriz de confusión y calibración, con IC bootstrap para AUC y para la diferencia entre bloques. Importancia por permutación.
5. **Clustering**: comparar k = 2–8 por silueta y estabilidad (ARI entre semillas), con porcentajes ponderados. Pasa a apéndice si no aporta.
6. **INCAA**: participación de cada género en las entradas (aclarando que un título puede tener varios géneros), cobertura del match y cronología de las adaptaciones de videojuegos (posteriores a la encuesta).
7. Un solo comando reproduce todo desde la raíz (`python run_all.py`); dependencias fijadas en `requirements.txt`.

## Bloque C — Visualización (eje 3)

1. `app.py` lee exclusivamente de `outputs/`. Recorrido: universo y calidad → diferencias entre públicos → asociaciones ajustadas (forest plot con IC) → valor predictivo (AUC por bloque, ROC, calibración) → mercado INCAA → límites.
2. Mostrar denominadores, n muestral e incertidumbre; advertir subgrupos chicos.
3. Exportar PNG estáticos como respaldo para las diapositivas y para una demo sin red.

## Bloque D — Documentación

README (hallazgos reales, ejecución, linaje), guía de defensa reescrita, LEEME integrado al README.

## Estado (12/11/2026)

- [x] A — Fuentes: manifest con SHA-256, auditoría automática, limpieza estricta, auditoría de saltos, registro de transformaciones, diccionario. Hallazgo adicional: etiquetas de VJ5 desplazadas.
- [x] B — Inferencia con diseño, géneros con Holm, sensibilidad (8 variantes), predicción por bloques con test reservado y bootstrap, clustering con estabilidad, mercado INCAA.
- [x] C — App Streamlit reescrita (lee solo de `outputs/`), 13 figuras PNG exportadas.
- [x] D — README y guía de defensa reescritos.
- [x] Diapositivas generadas en `presentacion/` (16 diapositivas). Pendiente: revisión visual en PowerPoint.
- [ ] Completar integrantes en el README.

## Orden y tiempos estimados

A (2 h) → B (4 h) → C (2 h) → D (1 h). Si falta tiempo, se recorta en C (la app queda mínima pero correcta) antes que en A o B.
