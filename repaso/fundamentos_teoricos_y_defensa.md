# Guía para la defensa

Las cifras citadas salen de `outputs/` (ver README). Si se vuelve a correr el pipeline, los números son idénticos
(semilla fija).

## 1. El mensaje en 30 segundos

1. Quienes juegan en PC/consola van más al cine (62% vs. 27% de quienes no juegan).
2. Comparando personas parecidas en edad, NSE, género, educación, actividad, región y tamaño de localidad, la
   diferencia se achica pero se mantiene: **+16,5 puntos porcentuales** (IC 95%: 9,9 a 23,1).
3. **No** encontramos diferencias en los géneros que ven en el cine una vez que se mide correctamente.
4. Para **predecir** quién va al cine, saber si alguien juega no agrega nada a la demografía; el consumo de streaming sí.

## 2. Por qué cambiaron las conclusiones respecto de la primera versión

| Antes | Problema | Ahora |
|---|---|---|
| "Prefieren Acción/Sci-Fi/Terror 3–5 veces más" | Se medía sobre toda la población: quien no va al cine "no ve terror". La diferencia repetía la de asistencia. | Solo entre asistentes, con ajuste y corrección de Holm: ninguna diferencia significativa. |
| `es_ocupado` | Buscaba "trabaj" y también marcaba "No trabaja" (1.389 errores). | Mapeo explícito de las 5 categorías. |
| Etiquetas de géneros de videojuego | Desplazadas un lugar respecto del código de variable. | Corregidas por código (V328–V339). |
| Métricas del Random Forest | Precisión/recall escritas a mano en el código. | Todas calculadas, con IC por bootstrap. |
| "p < 0,001" | No se calculaba ningún p-valor (sklearn regulariza y no da errores estándar). | Errores estándar con diseño muestral; p-valores calculados. |
| ">75 millones de entradas en 3 géneros" | Superaba el total: una película tiene varios géneros. | Participación por género, aclarando la superposición. |
| FNAF/Mario como evidencia | Se estrenaron después de la encuesta. | Cronología explícita. |
| Simulador de ROI/CAC | CPM y conversiones supuestos, no medidos. | Retirado. |

## 3. Preguntas probables

**"Los gamers son más jóvenes y los jóvenes van más al cine, ¿no es solo edad?"**
Es la primera explicación alternativa que probamos. Sin ajustar, la diferencia es de 35 pp; ajustando edad (con una
curva flexible, no lineal) y NSE baja a 18 pp; con todos los controles, 16,5 pp. La edad explica más de la mitad de
la brecha, pero no toda. Además, en el gráfico por tramos de edad la línea de PC/consola queda arriba en cada tramo.

**"¿Entonces jugar hace que la gente vaya al cine?"**
No podemos decir eso. Es una encuesta de un solo momento. Puede haber una tercera variable no medida, como el
interés general por el entretenimiento o el ingreso del hogar, que explique las dos cosas. Hablamos de asociación.

**"¿Por qué ponderan y qué es eso del diseño muestral?"**
La ENCC no es una muestra aleatoria simple. Selecciona localidades dentro de cada región y después personas dentro
de las localidades, así que cada persona representa a una cantidad distinta de gente (`ponderador`). Además, las
personas de una misma localidad se parecen entre sí. Si ignoráramos eso, los intervalos serían demasiado optimistas.
Calculamos la varianza a partir de las localidades dentro de cada región; es el mismo método que usa el paquete
`survey` de R. Lo validamos contra statsmodels.

**"¿Qué es un odds ratio y por qué también muestran puntos porcentuales?"**
El OR compara chances (p/(1−p)), no probabilidades. Un OR de 2,3 no significa "2,3 veces más probable". Por eso
reportamos también la diferencia en puntos porcentuales: si todos jugaran en PC/consola, la asistencia estimada
sería 47,9%; si nadie jugara, 31,4%.

**"¿Por qué corrigieron por comparaciones múltiples?"**
Probamos 10 géneros. Con un umbral de 5%, por azar es esperable que alguno "dé significativo". Holm controla la
probabilidad de al menos un falso positivo en la familia. Sin corregir, Comedia tenía p = 0,043 (y a favor de los
no jugadores); corregido, nada.

**"El modelo tiene AUC 0,76. ¿Es bueno?"**
Es moderado y honesto. Se mide en un 20% de datos que no se usó para nada antes. Lo importante no es el número en sí
sino la comparación: con demografía sola, 0,72; sumando gaming, 0,72; sumando streaming, 0,76. El IC de la mejora
por gaming incluye el cero; el de streaming no.

**"¿Por qué no usaron el Random Forest, si es más potente?"**
Lo usamos y lo comparamos. Con estas variables (mayormente binarias y ordinales) y unas 2.700 personas de
entrenamiento, la regresión logística rinde igual o mejor y es interpretable. Un modelo más complejo no siempre gana.

**"¿Cómo evitaron el *leakage*?"**
Excluimos todas las preguntas del bloque de cine, que solo existen si la persona fue. La imputación y el escalado se
aprenden dentro de cada partición. El umbral de clasificación se elige en entrenamiento. El test se usa una sola vez.

**"¿Por qué el clustering está en el apéndice?"**
Probamos de 2 a 8 grupos. La calidad de separación no tiene un máximo claro y los grupos reproducen combinaciones de
"va al cine / juega / usa plataformas". No descubren nada que no se vea con una tabla. El k = 4 de la primera versión
era además el menos estable (en el peor 10% de las réplicas, la asignación de grupos cambia mucho más que con cualquier otro k).

**"¿Cómo conectan la ENCC con el INCAA?"**
Solo como contexto agregado. No hay forma de saber quién compró cada entrada. Comparamos la proporción de asistentes
que dice haber visto cada género con la participación de ese género en las entradas de 2022, el período que cubre la
encuesta. Son medidas distintas, y lo aclaramos en el gráfico.

**"¿Qué le recomendarían a una distribuidora?"**
Que la afinidad PC/consola–cine es real, pero para estimar público el consumo de streaming y la demografía dicen más
que el gaming. No tenemos datos para afirmar que una campaña dirigida a gamers rinda más; eso requeriría un
experimento o datos de campañas.

## 4. Glosario mínimo

- **IC 95%**: rango de valores compatibles con los datos; si se repitiera la encuesta muchas veces, el 95% de esos
  intervalos contendría el valor real.
- **pp (puntos porcentuales)**: diferencia absoluta entre porcentajes (62% − 27% = 35 pp).
- **ROC-AUC**: probabilidad de que el modelo ordene a una persona que fue al cine por encima de una que no fue (0,5 = azar).
- **Holm**: corrección que ajusta p-valores cuando se hacen varias pruebas a la vez.
- **Tamaño efectivo de muestra**: cuántas observaciones "valen" las 3.380 una vez considerada la desigualdad de los
  ponderadores (≈ 1.500).
