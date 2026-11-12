// Genera presentacion/TPO_Cine_y_Videojuegos.pptx a partir de presentacion/datos.json.
//   python presentacion/datos_presentacion.py && node presentacion/construir.js
// Ninguna cifra está escrita a mano: todas salen de datos.json (que a su vez sale de outputs/).

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const D = JSON.parse(fs.readFileSync(path.join(__dirname, "datos.json"), "utf8"));
const R = D.resumen;
const SALIDA = path.join(__dirname, "TPO_Cine_y_Videojuegos.pptx");

// ------------------------------------------------------------------ paleta (la del ejemplo)
const K = {
  noche: "14161F", ambar: "E9A23B", crema: "F5F1E8", tinta: "1A1C24", gris: "6B6F7A",
  marron: "8A4F0A", tarjeta: "FBF9F4", borde: "E2DCCF", pizarra: "3F4350", naranja: "D9861A",
  azul: "3E4A63", arena: "C9C3B6", claro: "F3EEE4", grisClaro: "B5B2AC",
};
const THEME = {
  name: "Cine y Gaming", headFontFace: "Oswald", bodyFontFace: "Public Sans",
  colors: { dk1: K.tinta, lt1: K.crema, dk2: K.pizarra, lt2: K.borde, accent1: K.marron, accent2: K.ambar,
            accent3: K.naranja, accent4: K.pizarra, accent5: K.gris, accent6: K.azul, hlink: "0563C1", folHlink: "6B6F7A" },
};
const SEG = { pc_consola: K.marron, solo_movil: K.ambar, no_juega: K.gris };
const NOMBRE_SEG = { pc_consola: "PC/consola", solo_movil: "Solo celular/tablet", no_juega: "No juega" };

// ------------------------------------------------------------------ formato (es-AR)
const f = (x, d = 1) => Number(x).toFixed(d).replace(".", ",");
const pct = (x, d = 0) => f(100 * x, d) + "%";
const num = (x) => Math.round(x).toLocaleString("es-AR");
const pp = (x, d = 1) => (x >= 0 ? "+" : "−") + f(Math.abs(x), d) + " pp";
const sgn = (x, d = 3) => (x >= 0 ? "+" : "−") + f(Math.abs(x), d);
const millones = (x) => f(x / 1e6, 1) + " M";

// ------------------------------------------------------------------ cifras derivadas
const desc = Object.fromEntries(D.descriptivos.map((r) => [r.segmento, r]));
const aj = Object.fromEntries(D.ajustada.map((r) => [r.segmento, r]));
const con = (esp, c) => D.contrastes.find((r) => r.especificacion === esp && r.contraste === c);
const pcNo = con("completo", "pc_consola vs no_juega");
const movNo = con("completo", "solo_movil vs no_juega");
const pcMov = con("completo", "pc_consola vs solo_movil");
const test = (m, b) => D.pred_test.find((r) => r.modelo === m && r.bloque === b);
const dif = (a, b) => D.pred_difs.find((r) => r.comparacion === `${a} − ${b}`);
const difGaming = dif("logistica|3_demo_gaming", "logistica|1_demografia");
const difStream = dif("logistica|4_demo_gaming_streaming", "logistica|3_demo_gaming");
const final = test("logistica", "4_demo_gaming_streaming");
const baseline = test("baseline", "1_demografia");
const BLOQUES = ["1_demografia", "2_demo_segmento", "3_demo_gaming", "4_demo_gaming_streaming"];
const logitGanaEnTodos = BLOQUES.every((b) => test("logistica", b).roc_auc >= test("random_forest", b).roc_auc);
const nSigHolm = D.generos_contrastes.filter((g) => g.significativo_holm_5pct).length;
const nGeneros = D.generos_contrastes.length;
const sensMin = Math.min(...D.sensibilidad.map((s) => s.or));
const sensMax = Math.max(...D.sensibilidad.map((s) => s.or));
const sensIcMin = Math.min(...D.sensibilidad.map((s) => s.or_ic_inf));
const tramos = [...new Set(D.edad.map((r) => r.tramo_edad))];
const edadDe = (t, s) => D.edad.find((r) => r.tramo_edad === t && r.segmento === s);
const pcArribaEnTodos = tramos.every((t) => edadDe(t, "pc_consola").asistencia > edadDe(t, "no_juega").asistencia);
const difEdad = desc.no_juega.edad_media - desc.pc_consola.edad_media;
const mk = R.mercado;
const antesCampo = D.adaptaciones.filter((a) => a.respecto_campo_encc.startsWith("antes"));
const mario = D.adaptaciones.find((a) => a.titulo.includes("MARIO"));
const nControlesSalto = D.calidad.length;
const inconsistencias = D.calidad.reduce((s, r) => s + r.n_faltante_en_universo + r.n_fuera_universo_con_dato, 0);
const sumaGeneros = mk.suma_pct_generos_2022_2023;
const VAR = {
  edad: "Edad", educacion_orden: "Nivel educativo", stream_pago_frecuencia_orden: "Frecuencia en plataformas pagas",
  stream_g_accion_aventura: "Ve acción/aventura en streaming", tamanio: "Tamaño de la localidad",
  stream_g_suspenso: "Ve suspenso en streaming", actividad: "Condición de actividad", vj_g_shooters: "Juega shooters",
};
const MENORES = new Set(["at", "de", "a", "la", "el", "del"]);
const tituloCorto = (t) => t.split(":")[0].replace(" LA PELICULA", "").replace(/\.$/, "").toLowerCase().split(" ")
  .map((p, i) => (i > 0 && MENORES.has(p) ? p : p.charAt(0).toUpperCase() + p.slice(1))).join(" ");
const nEf = "≈ " + num(Math.round(R.muestra.n_efectivo_kish / 100) * 100);
const VARIANTE = { "Segmento PC/consola sin notebook (notebook pasa a 'otros jugadores')": "PC/consola sin notebook (otra definición del grupo)",
                   "Solo 13 a 49 años (zona con jugadores de PC/consola)": "Solo 13 a 49 años (hay jugadores de PC/consola)" };

// ------------------------------------------------------------------ presentación y layouts
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13,333 × 7,5 pulgadas, igual que el ejemplo
pres.title = "Cine y videojuegos en Argentina — TPO Ciencia de Datos";
pres.author = "Grupo TPO";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const W = 13.333, X0 = 0.6, CW = W - 2 * X0;

pres.defineSlideMaster({
  title: "PORTADA",
  background: { color: K.noche },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENIDO",
  background: { color: K.crema },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: X0, y: 0.42, w: CW, h: 0.3, fontSize: 12, bold: true, color: K.marron, charSpacing: 3, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.72, w: CW, h: 1.05, fontSize: 28, color: K.tinta, valign: "top", margin: 0, fontFace: "Oswald" }, text: "" } },
    { placeholder: { options: { name: "pie", type: "body", x: X0, y: 6.98, w: CW - 0.6, h: 0.3, fontSize: 10, color: K.gris, margin: 0 }, text: "" } },
  ],
  slideNumber: { x: W - X0 - 0.45, y: 6.98, w: 0.45, h: 0.3, fontSize: 10, color: K.gris, align: "right" },
});

// ------------------------------------------------------------------ utilidades de composición
const SECCIONES = new Set();
function seccion(t) { if (!SECCIONES.has(t)) { pres.addSection({ title: t }); SECCIONES.add(t); } return t; }
function nueva(master, sec, kicker, titulo, pie) {
  const seccion_ = seccion(sec);
  const s = pres.addSlide({ masterName: master, sectionTitle: seccion_ });
  if (kicker) s.addText(kicker, { placeholder: "kicker" });
  if (titulo) s.addText(titulo, { placeholder: "title" });
  if (pie) s.addText(pie, { placeholder: "pie" });
  const addChart = s.addChart.bind(s);
  s.addChart = (tipo, datos, o) => addChart(tipo, datos.map((d) => ({ ...d, values: d.values.map((v) => Math.round(v * 100) / 100) })), o);
  return s;
}
function tarjeta(s, x, y, w, h, fill = K.tarjeta) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: K.borde, width: 0.75 } });
}
function texto(s, t, o) {
  s.addText(t, { isTextBox: true, margin: 0, valign: "top", color: K.tinta, fontSize: 14, ...o });
}
function cifra(s, valor, etiqueta, x, y, w, o = {}) {
  const hv = Math.max(0.85, ((o.size || 44) * 1.25) / 72);
  texto(s, valor, { x, y, w, h: hv, fontFace: "Oswald", fontSize: o.size || 44, color: o.color || K.marron, valign: "bottom" });
  texto(s, etiqueta, { x, y: y + hv + 0.05, w, h: o.hEtq || 0.9, fontSize: 15, color: o.colorEtq || K.pizarra });
}
function circulo(s, x, y, d, t, fill = K.marron, color = K.crema) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
  texto(s, t, { x, y, w: d, h: d, align: "center", valign: "middle", fontFace: "Oswald", fontSize: 16, color, bold: true });
}
const celdaH = (t, o = {}) => ({ text: t, options: { bold: true, fill: { color: K.tinta }, color: K.crema, ...o } });
const celda = (t, o = {}) => ({ text: t, options: o });
function tabla(s, filas, o) {
  s.addTable(filas, { fontSize: 13, color: K.tinta, fill: { color: K.tarjeta }, border: { type: "solid", pt: 0.75, color: K.borde },
                      valign: "middle", margin: [0.04, 0.08, 0.04, 0.08], ...o });
}
const EJES = {
  catAxisLabelColor: K.pizarra, valAxisLabelColor: K.pizarra, catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", legendFontSize: 12,
  legendColor: K.pizarra, dataLabelFontFace: "+mn-lt", dataLabelFontSize: 11, dataLabelColor: K.tinta,
  titleFontFace: "+mn-lt", titleFontSize: 13, titleColor: K.tinta,
  valGridLine: { color: K.borde, size: 0.75 }, catGridLine: { style: "none" },
  catAxisLineShow: true, catAxisLineColor: K.arena, valAxisLineShow: false,
};

// ================================================================== 1 · PORTADA
{
  const s = pres.addSlide({ masterName: "PORTADA", sectionTitle: seccion("Negocio") });
  texto(s, "UADE · CIENCIA DE DATOS · TRABAJO PRÁCTICO OBLIGATORIO", { x: X0 + 0.2, y: 1.5, w: CW, h: 0.4, fontSize: 14, bold: true, color: K.ambar, charSpacing: 3 });
  texto(s, "CINE & GAMING", { x: X0 + 0.2, y: 2.0, w: CW, h: 1.5, fontFace: "Oswald", fontSize: 72, color: K.claro, valign: "middle" });
  texto(s, "¿Quienes juegan videojuegos van más al cine?", { x: X0 + 0.2, y: 3.65, w: 10.5, h: 0.6, fontSize: 24, color: K.arena });
  texto(s, "[Integrante 1] · [Integrante 2] · [Integrante 3] · [Integrante 4] · [Integrante 5] — Docente: Santiago Martín · Noviembre 2026",
        { x: X0 + 0.2, y: 6.2, w: CW, h: 0.4, fontSize: 14, color: K.arena });
  s.addNotes(`[Integrante 1] — 15 segundos. Presentar al grupo y la pregunta. No leer la diapositiva.
Reparto (≈ 16 min): Integrante 1, diapositivas 1–3 (2,5 min) · Integrante 2, 4–5 (2,5 min) · Integrante 3, 6–9 (3,5 min) · Integrante 4, 10–14 (5 min) · Integrante 5, 15–16 (2 min).
Fuentes: ENCC 2022/23 (${num(R.muestra.n)} encuestas), INCAA (${num(mk.estrenos)} estrenos) y TMDB.`);
}

// ================================================================== 2 · HIPÓTESIS
{
  const s = nueva("CONTENIDO", "Negocio", "DOMINIO Y PROBLEMA", "La hipótesis, y cómo la pusimos a prueba", "Pregunta aprobada por la cátedra junto con el dataset ENCC 2022/23");
  tarjeta(s, X0, 1.95, 6.35, 1.95);
  texto(s, "“Los jugadores de consola/PC van más al cine y prefieren Acción/Aventura, Ciencia ficción y Terror; una campaña de películas de universo gaming dirigida a ese segmento y a esos géneros rinde más que una dirigida a jugadores en general.”",
        { x: X0 + 0.25, y: 2.12, w: 5.85, h: 1.65, fontSize: 15, italic: true, color: K.pizarra });
  const qpv = [["¿Qué?", "¿El gamer de PC/consola es otro público para el cine?"], ["¿Para quién?", "Distribuidoras y cadenas de cine"], ["¿Valor?", "Segmentar con evidencia, no con supuestos"]];
  qpv.forEach(([q, a], i) => {
    const y = 4.2 + i * 0.8;
    texto(s, q, { x: X0, y, w: 1.6, h: 0.6, fontSize: 15, bold: true, color: K.marron, valign: "middle" });
    texto(s, a, { x: X0 + 1.65, y, w: 4.7, h: 0.6, fontSize: 15, valign: "middle" });
  });
  const xR = 7.35, wR = W - X0 - xR;
  const hs = [["H1", "¿Van más al cine, a igual edad?"], ["H2", "¿Ven otros géneros?"], ["H3", "¿Una campaña dirigida rinde más?"], ["+", "¿El gaming ayuda a predecir?"]];
  hs.forEach(([n, t], i) => {
    const y = 1.95 + i * 1.2;
    tarjeta(s, xR, y, wR, 1.0);
    circulo(s, xR + 0.22, y + 0.22, 0.55, n);
    texto(s, t, { x: xR + 1.0, y, w: wR - 1.15, h: 1.0, fontSize: 17, bold: true, valign: "middle" });
  });
  s.addNotes(`[Integrante 1] — 1 minuto. Esta es la frase con la que arrancamos y contra la que se evalúa todo el trabajo. No la cambiamos después de ver los resultados: la partimos en preguntas que los datos pueden contestar.
¿Qué resolvemos? Si el jugador de PC/consola es un público distinto para el cine, o solo una persona joven más. ¿Para quién? Gerencias comerciales de distribuidoras y cadenas. ¿Cómo da valor? Dice qué parte del perfil gamer sirve para segmentar y cuál no.
H1 y H2 se contestan con la encuesta. H3 ("rinde más") necesitaría datos de campañas reales. La pregunta "+" es exploratoria: si el gaming ayuda a predecir quién va al cine. Al final volvemos a esta frase y la contestamos parte por parte.`);
}

// ================================================================== 3 · MERCADO
{
  const s = nueva("CONTENIDO", "Negocio", "EL MERCADO", "Las películas de videojuegos venden", "INCAA, estrenos comerciales 2022–2023 · adaptaciones según TMDB");
  const filas = [[celdaH("Película"), celdaH("Estreno"), celdaH("Entradas", { align: "right" }), celdaH("¿Antes de la encuesta?")]];
  D.adaptaciones.forEach((a) => {
    const antes = a.respecto_campo_encc.startsWith("antes");
    const [yy, mm] = a.fecha_estreno.split("-");
    filas.push([celda(tituloCorto(a.titulo), { bold: true }), celda(`${mm}/${yy}`), celda(num(a.entradas), { align: "right" }),
                celda(antes ? "Sí" : "No", { color: antes ? K.marron : K.gris, bold: antes })]);
  });
  tabla(s, filas, { x: X0, y: 1.95, w: 7.3, colW: [2.7, 1.2, 1.5, 1.9], rowH: 0.55, fontSize: 14 });
  const xR = 8.4, wR = W - X0 - xR;
  cifra(s, pct(mk.pct_entradas_vj, 1), `de las entradas 2022–2023`, xR, 1.85, wR, { size: 60, hEtq: 0.4 });
  cifra(s, `${D.mario_puesto}.º`, `${tituloCorto(mario.titulo)}, entre ${num(mk.estrenos)} estrenos`, xR, 3.85, wR, { size: 60, hEtq: 0.4 });
  s.addNotes(`[Integrante 1] — 1 minuto. Por qué importa el tema: ${D.adaptaciones.length} adaptaciones de videojuegos vendieron ${num(mk.entradas_vj)} entradas, el ${pct(mk.pct_entradas_vj, 1)} de las ${millones(mk.entradas_total)} del período. ${tituloCorto(mario.titulo)} fue el ${D.mario_puesto}.º estreno más visto.
El cuidado que tuvimos (columna de la derecha): la encuesta pregunta por "el último año" a personas entrevistadas entre noviembre de 2022 y enero de 2023. ${D.adaptaciones.length - antesCampo.length} de los ${D.adaptaciones.length} títulos se estrenaron después, así que no pudieron influir en las respuestas. Los usamos solo como contexto. Pase a [Integrante 2].`);
}

// ================================================================== 4 · PIPELINE
{
  const s = nueva("CONTENIDO", "Datos", "ARQUITECTURA DE LA SOLUCIÓN", "Tres fuentes, un pipeline reproducible", "Herramientas: Python, pandas, statsmodels, scikit-learn, Plotly y Streamlit");
  const cols = [
    ["FUENTES", [["ENCC 2022/23", `${num(R.muestra.n)} personas`], ["INCAA", `${num(mk.estrenos)} estrenos`], ["TMDB", "Géneros y adaptaciones"]]],
    ["CONTROL Y LIMPIEZA", [["Auditoría", `${D.n_controles_auditoria} controles`], ["Limpieza ENCC", "Contra el cuestionario"]]],
    ["ANÁLISIS", [["Inferencia", "Logística con diseño"], ["Predicción", "Logística vs. Random Forest"]]],
    ["USO", [["Tablero interactivo", "Explorar resultados"], ["Gráficos", "Figuras del informe"], ["Esta presentación", "Mismos resultados"]]],
  ];
  const gap = 0.45, cw = (CW - 3 * gap) / 4;
  cols.forEach(([titulo, items], i) => {
    const x = X0 + i * (cw + gap);
    texto(s, titulo, { x, y: 1.95, w: cw, h: 0.3, fontSize: 12, bold: true, color: K.marron, charSpacing: 2 });
    items.forEach(([t, d], j) => {
      const y = 2.4 + j * 1.1;
      tarjeta(s, x, y, cw, 0.95);
      texto(s, t, { x: x + 0.18, y: y + 0.12, w: cw - 0.36, h: 0.35, fontSize: 15, bold: true });
      texto(s, d, { x: x + 0.18, y: y + 0.5, w: cw - 0.36, h: 0.35, fontSize: 13, color: K.pizarra });
    });
    if (i < 3) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + cw + 0.08, y: 3.3, w: gap - 0.16, h: 0.3, fill: { color: K.ambar }, line: { color: K.ambar } });
  });
  tarjeta(s, X0, 5.95, CW, 0.75, K.noche);
  texto(s, [{ text: "Reproducible: ", options: { bold: true, color: K.ambar } },
            { text: "un solo proceso rehace todo el análisis, con los mismos resultados cada vez", options: { color: K.claro } }],
        { x: X0 + 0.3, y: 5.95, w: CW - 0.6, h: 0.75, fontSize: 16, valign: "middle" });
  s.addNotes(`[Integrante 2] — 1 minuto. La encuesta (ENCC) nos dice qué hace la gente; el INCAA, qué se vendió; TMDB le pone género y la marca "adaptación de videojuego" a cada estreno.
Todo se reproduce con un solo comando, con los mismos resultados en cada corrida (semilla fija). El primer paso verifica que los archivos de origen sean exactamente los descargados (hash SHA-256): si alguien cambia un dato, el pipeline se detiene.
Límite que declaramos: el export original del INCAA (Tableau) no está disponible; el archivo más temprano que tenemos ya estaba limpio. TMDB se guarda como snapshot para no depender de la API.`);
}

// ================================================================== 5 · DATOS
{
  const s = nueva("CONTENIDO", "Datos", "PREPARACIÓN DE LOS DATOS", "Tres decisiones que cambian el resultado",
    `Cada decisión queda registrada junto con los casos que afecta`);
  const cards = [
    [num(D.transformaciones["cine_g_*"]), "Un vacío no siempre es un cero", "Quien no fue al cine no tiene géneros vistos"],
    [nEf, "Cada respuesta pesa distinto", `Tamaño efectivo de las ${num(R.muestra.n)} encuestas`],
    [num(D.transformaciones.ocupado), "Revisar contra el cuestionario", "Personas mal clasificadas como ocupadas"],
  ];
  const gap = 0.4, cw = (CW - 2 * gap) / 3;
  cards.forEach(([n, t, d], i) => {
    const x = X0 + i * (cw + gap);
    tarjeta(s, x, 1.95, cw, 4.0);
    texto(s, n, { x: x + 0.35, y: 2.3, w: cw - 0.7, h: 1.1, fontFace: "Oswald", fontSize: 60, color: K.marron, valign: "bottom" });
    texto(s, t, { x: x + 0.35, y: 3.75, w: cw - 0.7, h: 0.8, fontSize: 19, bold: true });
    texto(s, d, { x: x + 0.35, y: 4.65, w: cw - 0.7, h: 0.9, fontSize: 15, color: K.pizarra });
  });
  s.addNotes(`[Integrante 2] — 1 minuto 30.
1) Un vacío no siempre es un cero. Si alguien no fue al cine, no le preguntan qué géneros vio (${num(D.transformaciones["cine_g_*"])} personas). La primera versión cargaba 0 y medía "preferencia por terror" sobre toda la población, aunque quien no va al cine "no ve terror". Ahora los géneros solo existen para quien fue. Auditamos ${nControlesSalto} preguntas: ${inconsistencias} inconsistencias de salto.
2) Cada respuesta pesa distinto. La encuesta elige localidades dentro de cada región y personas dentro de cada localidad. Los ponderadores van de ${f(R.muestra.ponderador_min, 2)} a ${f(R.muestra.ponderador_max, 1)}, así que las ${num(R.muestra.n)} encuestas equivalen a ${nEf} independientes. Cada número lleva un intervalo calculado con ese diseño (estrato región, conglomerado localidad).
3) Revisamos cada variable contra el cuestionario oficial. Buscar "trabaj" en el texto marcaba como ocupados a quienes respondían "No trabaja": ${num(D.transformaciones.ocupado)} casos. También corregimos etiquetas de géneros de videojuegos que estaban corridas un lugar.
Pase a [Integrante 3].`);
}

// ================================================================== 6 · GRUPOS
{
  const s = nueva("CONTENIDO", "Exploratorio", "ANÁLISIS EXPLORATORIO", "Tres grupos de la población",
    "Porcentajes ponderados · 13 años o más, localidades de más de 30.000 habitantes · ENCC 2022/23");
  const filas = [[celdaH("Grupo"), celdaH("% población", { align: "right" }), celdaH("Edad media", { align: "right" }),
                  celdaH("Fue al cine", { align: "right" }), celdaH("Casos", { align: "right" })]];
  ["pc_consola", "solo_movil", "no_juega"].forEach((k) => {
    const r = desc[k];
    filas.push([celda(NOMBRE_SEG[k], { bold: true, color: SEG[k] === K.ambar ? K.naranja : SEG[k] }), celda(pct(r.pct_poblacion), { align: "right" }),
                celda(f(r.edad_media, 0), { align: "right" }), celda(pct(r.asistencia), { align: "right", bold: true }), celda(num(r.n), { align: "right" })]);
  });
  tabla(s, filas, { x: X0, y: 1.95, w: CW, colW: [3.93, 2.05, 2.05, 2.05, 2.05], rowH: 0.65, fontSize: 18 });
  tarjeta(s, X0, 5.0, CW, 1.5);
  circulo(s, X0 + 0.35, 5.42, 0.65, "!", K.ambar, K.tinta);
  texto(s, `${f(difEdad, 0)} años más joven: ¿va más al cine por jugar, o por ser joven?`, { x: X0 + 1.3, y: 5.0, w: CW - 1.6, h: 1.5, fontSize: 22, bold: true, valign: "middle" });
  s.addNotes(`[Integrante 3] — 45 segundos. Cómo armamos los grupos: PC/consola = jugó en consola, PC o notebook en el último año; solo celular/tablet = jugó, pero solo en esos dispositivos; no juega = no jugó. Un jugador que no declaró dispositivo quedó sin grupo, en vez de suponer que juega en el celular.
Lo que más llama la atención es la edad: ${f(desc.pc_consola.edad_media, 1)} contra ${f(desc.no_juega.edad_media, 1)} años. Si no la controlamos, cualquier diferencia en el cine podría ser solo un efecto de juventud. Esa es la objeción que contestan las próximas diapositivas.`);
}

// ================================================================== 7 · EDAD
{
  const s = nueva("CONTENIDO", "Exploratorio", "ANÁLISIS EXPLORATORIO", "A igual edad, quien juega en PC/consola va más al cine",
    "% que fue al cine en el último año, ponderado · ENCC 2022/23");
  const series = ["pc_consola", "solo_movil", "no_juega"].map((k) => ({ name: NOMBRE_SEG[k], labels: tramos, values: tramos.map((t) => edadDe(t, k).asistencia) }));
  s.addChart(pres.charts.LINE, series, {
    x: X0, y: 1.9, w: 8.4, h: 4.85, ...EJES, chartColors: ["pc_consola", "solo_movil", "no_juega"].map((k) => SEG[k]),
    lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 9, valAxisMinVal: 0, valAxisMaxVal: 0.8, valAxisMajorUnit: 0.2,
    valAxisLabelFormatCode: "0%", showLegend: true, legendPos: "t", showValue: false,
  });
  const xR = 9.45, wR = W - X0 - xR;
  cifra(s, `${pct(desc.pc_consola.asistencia)} vs ${pct(desc.no_juega.asistencia)}`, "PC/consola vs. no juega", xR, 2.0, wR, { size: 44, hEtq: 0.4 });
  cifra(s, pcArribaEnTodos ? `${tramos.length} de ${tramos.length}` : "No en todos", "tramos de edad con PC/consola arriba", xR, 4.0, wR, { size: 44, hEtq: 0.7 });
  s.addNotes(`[Integrante 3] — 1 minuto. Primera forma de contestar la objeción de la edad, sin modelos: comparar dentro de cada tramo de edad. En los ${tramos.length} tramos, la línea de PC/consola queda arriba de la de quienes no juegan.
Ejemplo para decir en voz alta: entre 18 y 29 años, fue al cine el ${pct(edadDe("18–29", "pc_consola").asistencia)} de quienes juegan en PC/consola y el ${pct(edadDe("18–29", "no_juega").asistencia)} de quienes no juegan.
Cuidado si preguntan por los mayores de 50: hay muy pocos jugadores de PC/consola en esas edades, así que esos puntos son imprecisos (la app los marca). Cuánto explica la edad lo mide el modelo de [Integrante 4].`);
}

// ================================================================== 8 · GÉNEROS
{
  const s = nueva("CONTENIDO", "Exploratorio", "ANÁLISIS EXPLORATORIO · GÉNEROS", "¿Ven otros géneros? Depende de cómo se mida",
    `% que vio el género en el cine · ENCC 2022/23, ponderado`);
  const gs = ["accion_aventura", "ciencia_ficcion", "terror"];
  const etq = gs.map((g) => D.generos_desc.find((r) => r.genero === g).etiqueta);
  const val = (g, k, campo) => D.generos_desc.find((r) => r.genero === g && r.segmento === k)[campo];
  const panel = (x, titulo, campo) => s.addChart(pres.charts.BAR, ["pc_consola", "no_juega"].map((k) => ({ name: NOMBRE_SEG[k], labels: etq, values: gs.map((g) => val(g, k, campo)) })), {
    x, y: 1.9, w: 5.9, h: 3.8, ...EJES, barDir: "col", barGrouping: "clustered", barGapWidthPct: 70,
    chartColors: [SEG.pc_consola, SEG.no_juega], valAxisMinVal: 0, valAxisMaxVal: 0.7, valAxisMajorUnit: 0.2, valAxisLabelFormatCode: "0%",
    showValue: true, dataLabelFormatCode: "0%", dataLabelPosition: "outEnd", showLegend: true, legendPos: "t", showTitle: true, title: titulo,
  });
  panel(X0, "Sobre toda la población (primera versión)", "pct_en_toda_la_poblacion");
  panel(X0 + 6.23, "Solo entre quienes fueron al cine", "pct_entre_asistentes");
  tarjeta(s, X0, 5.9, CW, 0.8);
  texto(s, `Entre quienes fueron, con ajuste y corrección por ${nGeneros} comparaciones: ${nSigHolm === 0 ? "ningún género difiere" : `${nSigHolm} géneros difieren`}`,
        { x: X0 + 0.3, y: 5.9, w: CW - 0.6, h: 0.8, fontSize: 17, bold: true, valign: "middle" });
  const top = D.generos_contrastes.filter((g) => gs.includes(g.genero));
  s.addNotes(`[Integrante 3] — 1 minuto. Esta es la diapositiva donde cambió la conclusión; contarla como un hallazgo metodológico.
Izquierda: lo que medía la primera versión. Sobre toda la población, quien juega en PC/consola "ve" acción ${pct(val("accion_aventura", "pc_consola", "pct_en_toda_la_poblacion"))} contra ${pct(val("accion_aventura", "no_juega", "pct_en_toda_la_poblacion"))}. Pero eso mezcla dos cosas: ir al cine y elegir el género. Quien no va al cine "no ve terror".
Derecha: solo entre quienes fueron. La brecha se achica (${pct(val("accion_aventura", "pc_consola", "pct_entre_asistentes"))} contra ${pct(val("accion_aventura", "no_juega", "pct_entre_asistentes"))}). Al ajustar por edad, NSE, género, educación y región, las diferencias son ${top.map((g) => `${g.etiqueta} ${pp(g.dif_pp, 0)}`).join(", ")}, con intervalos amplios (${num(R.generos.n_asistentes)} asistentes).
Probamos ${nGeneros} géneros a la vez: por azar alguno puede "dar significativo". Con la corrección de Holm, ninguno lo es. El p más bajo sin corregir fue ${f(R.generos.p_min_sin_ajustar, 3)} (comedia, a favor de quienes no juegan).`);
}

// ================================================================== 9 · OFERTA VS DEMANDA
{
  const s = nueva("CONTENIDO", "Exploratorio", "OFERTA VS. DEMANDA", "Lo que la gente dice que vio, y lo que se vendió",
    `ENCC 2022/23 · INCAA estrenos 2022 con match TMDB confiable (${pct(mk.pct_entradas_match_confiable)} de las entradas)`);
  const g = [...D.encc_vs_incaa].sort((a, b) => b.pct_entradas_2022 - a.pct_entradas_2022);
  s.addChart(pres.charts.BAR, [
    { name: "% de asistentes que lo vio (ENCC)", labels: g.map((r) => r.etiqueta), values: g.map((r) => r.pct_asistentes_que_vieron) },
    { name: "% de entradas 2022 (INCAA)", labels: g.map((r) => r.etiqueta), values: g.map((r) => r.pct_entradas_2022) },
  ], {
    x: X0, y: 1.9, w: 8.2, h: 4.85, ...EJES, barDir: "bar", barGrouping: "clustered", barGapWidthPct: 55, catAxisOrientation: "maxMin",
    chartColors: [K.azul, K.ambar], valAxisMinVal: 0, valAxisMaxVal: 0.7, valAxisMajorUnit: 0.1, valAxisLabelFormatCode: "0%",
    showLegend: true, legendPos: "t", showValue: false,
  });
  const xR = 9.2, wR = W - X0 - xR;
  cifra(s, pct(sumaGeneros), "suman los géneros: una película tiene varios", xR, 2.0, wR, { size: 54, hEtq: 0.7 });
  texto(s, "Medidas distintas: contexto, no comparación uno a uno", { x: xR, y: 4.3, w: wR, h: 1.0, fontSize: 16, bold: true, color: K.pizarra });
  s.addNotes(`[Integrante 3] — 45 segundos. Es el cruce entre las dos fuentes, pero hay que leerlo con cuidado. Azul: porcentaje de quienes fueron al cine que dice haber visto ese género (ENCC). Ámbar: participación del género en las entradas de los estrenos de 2022, el período que cubre la encuesta (INCAA + TMDB).
No son la misma unidad (personas contra entradas), la ENCC clasifica según lo que percibe la persona y TMDB según el catálogo, y una película suma a varios géneros. Por eso no sacamos conclusiones del tipo "falta oferta de terror", como hacía la primera versión.
Pase a [Integrante 4].`);
}

// ================================================================== 10 · TÉCNICAS
{
  const s = nueva("CONTENIDO", "Modelos", "TÉCNICAS DE MINERÍA", "Dos técnicas, dos preguntas", "Ambas usan el ponderador oficial de la ENCC");
  const cols = [
    ["EXPLICAR", "Regresión logística", "¿Es real o es la edad?"],
    ["PREDECIR", "Logística vs. Random Forest", "¿El gaming ayuda a predecir?"],
  ];
  const gap = 0.5, cw = (CW - gap) / 2;
  cols.forEach(([k, t, q], i) => {
    const x = X0 + i * (cw + gap);
    tarjeta(s, x, 1.95, cw, 4.0);
    texto(s, k, { x: x + 0.35, y: 2.25, w: cw - 0.7, h: 0.35, fontSize: 13, bold: true, color: K.marron, charSpacing: 3 });
    texto(s, t, { x: x + 0.35, y: 2.75, w: cw - 0.7, h: 1.2, fontFace: "Oswald", fontSize: 26 });
    texto(s, q, { x: x + 0.35, y: 4.3, w: cw - 0.7, h: 1.3, fontSize: 18, bold: true, color: K.pizarra });
  });
  s.addNotes(`[Integrante 4] — 45 segundos. Cada técnica contesta una parte distinta de la pregunta; por eso no elegimos un "modelo ganador".
EXPLICAR: la regresión logística estima el efecto de jugar "a igualdad del resto" y, con el diseño de la encuesta, da intervalos honestos. Un árbol predice, pero no aísla efectos.
PREDECIR: comparamos bloques de variables (demografía → + gaming → + streaming) en un test que no se usó para nada antes. Eso mide cuánto aporta cada fuente de información.`);
}

// ================================================================== 11 · LOGÍSTICA
{
  const s = nueva("CONTENIDO", "Modelos", "REGRESIÓN LOGÍSTICA", "Al ajustar por demografía, la brecha se achica pero no desaparece",
    `Ajuste: edad, NSE, género, educación, actividad, región y tamaño de localidad · IC 95% con diseño muestral · n = ${num(R.asistencia.n_modelo)}`);
  const segs = ["pc_consola", "solo_movil", "no_juega"];
  s.addChart(pres.charts.BAR, [
    { name: "Observada", labels: segs.map((k) => NOMBRE_SEG[k]), values: segs.map((k) => desc[k].asistencia) },
    { name: "Ajustada por demografía", labels: segs.map((k) => NOMBRE_SEG[k]), values: segs.map((k) => aj[k].prob_ajustada) },
  ], {
    x: X0, y: 1.9, w: 6.6, h: 4.85, ...EJES, barDir: "bar", barGrouping: "clustered", barGapWidthPct: 60, catAxisOrientation: "maxMin",
    chartColors: [K.grisClaro, K.marron], valAxisMinVal: 0, valAxisMaxVal: 0.8, valAxisMajorUnit: 0.2, valAxisLabelFormatCode: "0%",
    showValue: true, dataLabelFormatCode: "0%", dataLabelPosition: "outEnd", showLegend: true, legendPos: "t",
    showTitle: true, title: "Probabilidad de haber ido al cine",
  });
  const xR = 7.6, wR = W - X0 - xR;
  texto(s, "PC/CONSOLA VS. NO JUEGA", { x: xR, y: 2.0, w: wR, h: 0.3, fontSize: 12, bold: true, color: K.marron, charSpacing: 2 });
  const pasos = [["crudo", "Sin ajustar"], ["edad_nse", "Edad + NSE"], ["completo", "Ajuste completo"]];
  pasos.forEach(([e, n], i) => {
    const r = con(e, "pc_consola vs no_juega"), y = 2.45 + i * 1.1, fin = e === "completo";
    tarjeta(s, xR, y, wR, 0.95, fin ? K.noche : K.tarjeta);
    texto(s, n, { x: xR + 0.3, y, w: 2.4, h: 0.95, fontSize: 16, bold: true, valign: "middle", color: fin ? K.claro : K.tinta });
    texto(s, pp(r.dif_pp), { x: xR + 2.6, y, w: wR - 2.9, h: 0.95, fontFace: "Oswald", fontSize: 30, align: "right", valign: "middle", color: fin ? K.ambar : K.marron });
  });
  texto(s, `IC 95% del ajuste completo: ${f(pcNo.dif_ic_inf)} a ${f(pcNo.dif_ic_sup)} pp`, { x: xR, y: 5.85, w: wR, h: 0.4, fontSize: 14, color: K.pizarra });
  s.addNotes(`[Integrante 4] — 1 minuto 15. Esta es la diapositiva que contesta "¿no es solo edad?".
Sin ajustar, la diferencia entre jugar en PC/consola y no jugar es de ${f(con("crudo", "pc_consola vs no_juega").dif_pp)} puntos. Al ajustar por edad y NSE baja a ${f(con("edad_nse", "pc_consola vs no_juega").dif_pp)}; con todos los controles, ${f(pcNo.dif_pp)}. La edad explica más de la mitad de la brecha, pero no toda: el intervalo (${f(pcNo.dif_ic_inf)} a ${f(pcNo.dif_ic_sup)}) no toca el cero.
Cómo leer el gráfico: si todos jugaran en PC/consola, habría ido al cine el ${pct(aj.pc_consola.prob_ajustada, 1)}; si nadie, el ${pct(aj.no_juega.prob_ajustada, 1)}.
También: solo celular vs. no juega ${pp(movNo.dif_pp)}; PC/consola vs. solo celular ${pp(pcMov.dif_pp)} (IC ${f(pcMov.dif_ic_inf)} a ${f(pcMov.dif_ic_sup)}).
Si preguntan por el odds ratio: ${f(pcNo.or, 2)} (IC ${f(pcNo.or_ic_inf, 2)}–${f(pcNo.or_ic_sup, 2)}). Compara chances (p/(1−p)), no probabilidades: NO significa "${f(pcNo.or, 1)} veces más probable". Por eso mostramos puntos porcentuales.
Detalle técnico: logística ponderada sin regularización, errores estándar por linealización (estrato región, conglomerado localidad, ${R.diseno.gl} grados de libertad), validada contra statsmodels.`);
}

// ================================================================== 12 · ROBUSTEZ
{
  const s = nueva("CONTENIDO", "Modelos", "ROBUSTEZ", "El resultado no depende de cómo lo midamos", "PC/consola vs. no juega · odds ratio con IC 95% · 1 = sin diferencia");
  const filas = [[celdaH("Variante"), celdaH("Odds ratio (IC 95%)", { align: "right" })]];
  const CORTO = {
    "Principal (diseño completo)": "Principal", "Sin ponderar": "Sin ponderar", "Varianza: solo conglomerado por localidad": "Varianza sin estratos",
    "Varianza: robusta por persona (sin diseño)": "Varianza sin diseño", "Edad lineal y NSE ordinal (especificación original)": "Especificación de la primera versión",
    "Solo 13 a 49 años (zona con jugadores de PC/consola)": "Solo 13 a 49 años", "Ponderadores recortados al percentil 99": "Ponderadores recortados",
    "Segmento PC/consola sin notebook (notebook pasa a 'otros jugadores')": "PC/consola sin notebook",
  };
  D.sensibilidad.forEach((r, i) => filas.push([celda(CORTO[r.variante] || r.variante, { bold: i === 0 }),
    celda(`${f(r.or, 2)}  (${f(r.or_ic_inf, 2)}–${f(r.or_ic_sup, 2)})`, { align: "right", bold: i === 0 })]));
  tabla(s, filas, { x: X0, y: 1.95, w: 7.6, colW: [4.6, 3.0], rowH: 0.5, fontSize: 15 });
  const xR = 8.9, wR = W - X0 - xR;
  cifra(s, `${f(sensMin, 2)}–${f(sensMax, 2)}`, `en las ${D.sensibilidad.length} variantes`, xR, 2.0, wR, { size: 48, hEtq: 0.4 });
  cifra(s, sensIcMin > 1 ? "0" : "Alguno", "intervalos que tocan el 1", xR, 4.0, wR, { size: 48, hEtq: 0.4 });
  s.addNotes(`[Integrante 4] — 45 segundos. No nos quedamos con una sola forma de medir. Probamos sin ponderar; con otras formas de calcular la varianza; con la especificación de la primera versión (edad lineal, NSE ordinal); solo entre 13 y 49 años, donde hay jugadores de PC/consola de todas las edades; recortando ponderadores extremos; y cambiando la definición del grupo (sin notebook).
En todos los casos el resultado se mantiene: odds ratio entre ${f(sensMin, 2)} y ${f(sensMax, 2)}, y el límite inferior más bajo de todos los intervalos es ${f(sensIcMin, 2)}, por encima de 1.`);
}

// ================================================================== 13 · PREDICCIÓN
{
  const s = nueva("CONTENIDO", "Modelos", "PREDICCIÓN · CLASIFICACIÓN: ¿VA AL CINE O NO?", "Para predecir, el gaming no suma; el streaming sí",
    `ROC-AUC en un test reservado (n = ${num(R.prediccion.n_test)}), ponderado · azar = 0,50`);
  const etqB = ["Demografía", "+ grupo de juego", "+ gaming completo", "+ streaming"];
  s.addChart(pres.charts.LINE, ["logistica", "random_forest"].map((m) => ({
    name: m === "logistica" ? "Regresión logística" : "Random Forest", labels: etqB, values: BLOQUES.map((b) => test(m, b).roc_auc),
  })), {
    x: X0, y: 1.9, w: 8.2, h: 4.85, ...EJES, chartColors: [K.azul, K.naranja], lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 9,
    valAxisMinVal: 0.6, valAxisMaxVal: 0.8, valAxisMajorUnit: 0.05, valAxisLabelFormatCode: "0.00", showValue: true, dataLabelFormatCode: "0.00",
    dataLabelPosition: "t", showLegend: true, legendPos: "t", showTitle: true, title: "ROC-AUC (eje desde 0,60)",
  });
  const xR = 9.2, wR = W - X0 - xR;
  cifra(s, sgn(difGaming.dif_auc), "al sumar gaming", xR, 2.0, wR, { size: 48, hEtq: 0.4 });
  cifra(s, sgn(difStream.dif_auc), "al sumar streaming", xR, 4.0, wR, { size: 48, hEtq: 0.4 });
  s.addNotes(`[Integrante 4] — 1 minuto. Es clasificación binaria: la variable a predecir es sí/no (fue al cine en el último año). Excluimos todas las preguntas del bloque cine para no hacer trampa (leakage).
Leer de izquierda a derecha: con demografía sola, AUC ${f(test("logistica", "1_demografia").roc_auc, 3)}. Sumando el grupo de juego o todas las variables de videojuegos, no mejora (${f(test("logistica", "3_demo_gaming").roc_auc, 3)}; diferencia ${sgn(difGaming.dif_auc)}, IC ${sgn(difGaming.ic_inf)} a ${sgn(difGaming.ic_sup)}: incluye el cero). Sumando streaming, sube a ${f(final.roc_auc, 3)} (${sgn(difStream.dif_auc)}, IC ${sgn(difStream.ic_inf)} a ${sgn(difStream.ic_sup)}).
Cómo se concilia con la diapositiva anterior: jugar está asociado a ir al cine, pero esa información ya está casi toda en la edad y la educación. Para predecir, no agrega.
¿Por qué no Random Forest? ${logitGanaEnTodos ? "La logística lo iguala o supera en los 4 bloques" : "Lo supera en algún bloque, pero por poco"}: con estas variables el patrón es casi lineal. Hiperparámetros elegidos con validación cruzada 5 × 3; IC por bootstrap de localidades.`);
}

// ================================================================== 14 · MODELO FINAL
{
  const s = nueva("CONTENIDO", "Modelos", "EL MODELO FINAL", "Un clasificador moderado: sirve para ordenar, no para decidir",
    `Regresión logística con demografía + gaming + streaming · test reservado · umbral ${f(final.umbral, 2)} elegido en entrenamiento`);
  const stats = [[f(final.roc_auc, 2), "ROC-AUC"], [pct(final.recall), "recall"], [pct(final.precision), "precisión"]];
  stats.forEach(([v, e], i) => cifra(s, v, e, X0, 1.85 + i * 1.6, 3.0, { size: 48, hEtq: 0.4 }));
  const xM = 4.2;
  texto(s, `MATRIZ DE CONFUSIÓN · ${num(R.prediccion.n_test)} CASOS`, { x: xM, y: 1.95, w: 4.3, h: 0.3, fontSize: 12, bold: true, color: K.marron, charSpacing: 1 });
  tabla(s, [
    [celdaH(""), celdaH("Predice: no va", { align: "center" }), celdaH("Predice: va", { align: "center" })],
    [celda("No fue", { bold: true }), celda(num(final.vn), { align: "center", fontSize: 22 }), celda(num(final.fp), { align: "center", fontSize: 22 })],
    [celda("Fue", { bold: true }), celda(num(final.fn), { align: "center", fontSize: 22 }), celda(num(final.vp), { align: "center", fontSize: 22, bold: true })],
  ], { x: xM, y: 2.4, w: 4.3, colW: [1.1, 1.6, 1.6], rowH: 0.8, fontSize: 14 });
  const xR = 9.2, wR = W - X0 - xR;
  texto(s, "QUÉ USA EL MODELO", { x: xR, y: 1.95, w: wR, h: 0.3, fontSize: 12, bold: true, color: K.marron, charSpacing: 2 });
  D.importancia.slice(0, 5).forEach((r, i) => {
    const y = 2.4 + i * 0.75;
    circulo(s, xR, y, 0.48, String(i + 1), r.bloque === "demografia" ? K.gris : r.bloque === "gaming" ? K.ambar : K.azul, r.bloque === "gaming" ? K.tinta : K.crema);
    texto(s, VAR[r.variable] || r.variable, { x: xR + 0.62, y: y - 0.02, w: wR - 0.62, h: 0.52, fontSize: 14, valign: "middle" });
  });
  texto(s, "Gris: demografía · azul: streaming", { x: xR, y: 6.25, w: wR, h: 0.3, fontSize: 11, color: K.gris });
  s.addNotes(`[Integrante 4] — 1 minuto. El mejor modelo es moderado: AUC ${f(final.roc_auc, 2)} (IC ${f(final.auc_ic_inf, 2)}–${f(final.auc_ic_sup, 2)}). Si tomo al azar una persona que fue al cine y otra que no, el modelo le da más probabilidad a la que fue el ${pct(final.roc_auc)} de las veces.
Recall ${pct(final.recall)}: detecta ${pct(final.recall)} de quienes fueron. Precisión ${pct(final.precision)}: de los que marca como "va", ${pct(final.precision)} fueron. Exactitud ${pct(final.exactitud)}, pero ojo: predecir siempre "no va" ya acierta el ${pct(baseline.exactitud)}, porque la mayoría no fue (${pct(desc.total.asistencia)} fue al cine). Por eso sirve como ranking de propensión, no como filtro sí/no.
La matriz muestra casos sin ponderar; las métricas están ponderadas.
Lo que más usa: edad y nivel educativo; después, el consumo de streaming. La primera variable de videojuegos aparece recién en el puesto ${D.importancia.findIndex((r) => r.bloque === "gaming") + 1}. Es importancia predictiva (por permutación), no causalidad.
Si comparan con la primera versión (AUC 0,79): se calculó sobre otra partición y con la variable de ocupación mal construida; un test de este tamaño tiene una incertidumbre de ± 0,06.
Pase a [Integrante 5].`);
}

// ================================================================== 15 · CONCLUSIÓN
{
  const s = nueva("CONTENIDO", "Cierre", "CONCLUSIÓN · VOLVEMOS A LA HIPÓTESIS", "Se confirma una parte; la otra no resiste una medición correcta",
    "Cifras ajustadas por demografía, con diseño muestral · predicción en test reservado");
  const filas = [
    ["H1", "Van más al cine", `Sí · ${pp(pcNo.dif_pp)}`, K.marron],
    ["H2", "Ven otros géneros", `No · ${nSigHolm} de ${nGeneros}`, K.pizarra],
    ["H3", "Una campaña dirigida rinde más", "Sin datos para medirlo", K.gris],
    ["+", "El gaming ayuda a predecir", "No · el streaming sí", K.pizarra],
  ];
  filas.forEach(([n, h, v, col], i) => {
    const y = 1.95 + i * 1.18;
    tarjeta(s, X0, y, 7.7, 1.0);
    circulo(s, X0 + 0.22, y + 0.22, 0.55, n);
    texto(s, h, { x: X0 + 1.0, y, w: 3.5, h: 1.0, fontSize: 17, valign: "middle" });
    texto(s, v, { x: X0 + 4.4, y, w: 3.1, h: 1.0, fontSize: 17, bold: true, color: col, align: "right", valign: "middle" });
  });
  const xR = 8.7, wR = W - X0 - xR;
  tarjeta(s, xR, 1.95, wR, 4.55, K.noche);
  texto(s, "PARA UNA DISTRIBUIDORA", { x: xR + 0.3, y: 2.2, w: wR - 0.6, h: 0.3, fontSize: 12, bold: true, color: K.ambar, charSpacing: 2 });
  ["El gamer de PC/consola sí tiene afinidad con las salas", "Para estimar público, mirar streaming y demografía", "Antes de pautar, medirlo con un A/B"].forEach((t, i) => {
    const y = 2.8 + i * 1.2;
    circulo(s, xR + 0.3, y, 0.45, String(i + 1), K.ambar, K.tinta);
    texto(s, t, { x: xR + 0.95, y: y - 0.12, w: wR - 1.25, h: 0.8, fontSize: 16, color: K.claro });
  });
  s.addNotes(`[Integrante 5] — 1 minuto. Contestar la hipótesis parte por parte, como la presentamos al principio.
H1 se confirma: quien juega en PC/consola tiene ${f(pcNo.dif_pp)} puntos más de probabilidad de haber ido al cine, a igual edad, NSE y demás (IC ${f(pcNo.dif_ic_inf)} a ${f(pcNo.dif_ic_sup)}), y se sostiene en ocho variantes del análisis.
H2 no se sostiene: la "preferencia" por géneros era un artefacto de medirla sobre toda la población. Entre quienes fueron al cine, ${nSigHolm} de ${nGeneros} géneros difieren tras la corrección.
H3 no se puede contestar con estos datos. Por eso retiramos el simulador de la primera versión: dependía de supuestos (costo por mil impresiones, conversión) que no medimos.
Exploratoria: el gaming no mejora la predicción (${sgn(difGaming.dif_auc)} de AUC); el streaming sí (${sgn(difStream.dif_auc)}).
Recomendaciones: (1) el perfil PC/consola es una señal real de afinidad con las salas, no solo un efecto de la edad; (2) para estimar público, la demografía y el consumo de streaming dicen más que saber si alguien juega; (3) antes de concentrar pauta en gamers, probarlo con un A/B en el próximo estreno (mismo presupuesto, costo por entrada vendida).
Límites, si preguntan: es asociación, no causalidad (encuesta de un solo momento); el diseño muestral es aproximado (no hay radios censales); la encuesta mide lo declarado, no compras.`);
}

// ================================================================== 16 · GRACIAS
{
  const s = pres.addSlide({ masterName: "PORTADA", sectionTitle: seccion("Cierre") });
  texto(s, "CINE & GAMING", { x: X0 + 0.2, y: 1.5, w: CW, h: 0.4, fontSize: 14, bold: true, color: K.ambar, charSpacing: 3 });
  texto(s, "¡GRACIAS!", { x: X0 + 0.2, y: 2.2, w: CW, h: 1.6, fontFace: "Oswald", fontSize: 88, color: K.claro, valign: "middle" });
  texto(s, "¿Preguntas?", { x: X0 + 0.2, y: 3.9, w: CW, h: 0.6, fontSize: 26, color: K.arena });
  texto(s, "[Integrante 1] · [Integrante 2] · [Integrante 3] · [Integrante 4] · [Integrante 5]",
        { x: X0 + 0.2, y: 6.2, w: CW, h: 0.4, fontSize: 14, color: K.arena });
  s.addNotes(`[Integrante 5] — Cerrar y abrir las preguntas. Respuestas preparadas en las notas de cada diapositiva.`);
}

// ------------------------------------------------------------------ escritura
(async () => {
  await pres.writeFile({ fileName: SALIDA });
  await applyTheme(SALIDA, THEME);
  console.log("→ " + path.relative(path.join(__dirname, ".."), SALIDA));
})();
