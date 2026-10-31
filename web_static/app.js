// Interfaz del tablero. El motor de ajedrez (Python) vive en worker.js.
"use strict";

const GLIFOS = { k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟" };
const VS15 = "︎"; // fuerza el simbolo como texto (no emoji)
const PIEZAS_PROMO = ["q", "r", "b", "n"];
const DESCRIPCION_BOT = {
  "humano": "Dos personas en el mismo tablero: juegan por turnos, blancas y luego negras.",
  "bots": "Eliges un bot para las blancas y otro para las negras y miras cómo juegan entre sí.",
  "aleatorio": "Juega al azar. Ideal para aprender.",
  "1-paso": "Mira una jugada por delante: captura todo lo que puede.",
  "minimax-2": "Piensa 2 jugadas por delante (minimax con poda).",
  "minimax-3": "Piensa 3 jugadas por delante.",
  "minimax-4": "Hasta 4 jugadas por delante, máximo 5 s por jugada.",
  "ml-2": "Evaluación aprendida de partidas de Lichess. Piensa 2 jugadas por delante (muy rápido).",
  "ml-4": "Evaluación aprendida de partidas de Lichess. Piensa 4 jugadas por delante.",
  "ml-6": "Evaluación aprendida de partidas de Lichess. Piensa 6 jugadas por delante: puede tardar unos segundos.",
  "ml-3s": "Evaluación y libro de aperturas aprendidos de partidas de Lichess. Piensa hasta 3 s por jugada. El más fuerte.",
};

// Bots que pueden tardar: se avisa mientras piensan.
const TIEMPO_BOT = {
  "minimax-4": "Puede tardar hasta 5 segundos.",
  "ml-6": "Puede tardar unos segundos.",
  "ml-3s": "Piensa hasta 3 segundos.",
};

const $ = (id) => document.getElementById(id);
const el = {
  tablero: $("tablero"), velo: $("velo"), estado: $("estado"), estadoTexto: $("estado-texto"),
  estadoSub: $("estado-sub"), selBot: $("sel-bot"), pista: $("pista-bot"), jugadas: $("jugadas"),
  arriba: $("jugador-arriba"), abajo: $("jugador-abajo"), dlg: $("dlg-promo"),
  promoOpc: $("promo-opciones"), error: $("error"),
  ctrlBots: $("ctrl-bots"), bloqueBots: $("bloque-bots"), selBlancas: $("sel-blancas"),
  selNegras: $("sel-negras"), selVel: $("sel-vel"), btnPausa: $("btn-pausa"), btnPaso: $("btn-paso"),
  btnNueva: $("btn-nueva"), btnDeshacer: $("btn-deshacer"), btnGirar: $("btn-girar"), btnFen: $("btn-fen"),
};

let S = null;          // estado devuelto por Python
let sel = null;        // casilla seleccionada (0..63, a1 = 0)
let girado = false;    // tablero girado a mano
let ocupado = true;    // esperando al motor
let casillas = [];     // los 64 divs, en orden visual
let partida = 0;       // numero de partida: los bucles de partidas viejas se detienen solos
let pausado = false;   // bot contra bot: partida en pausa

// ---------- comunicacion con el worker ----------
const worker = new Worker("worker.js" + location.search);
let siguienteId = 1;
const pendientes = new Map();
worker.onmessage = (ev) => {
  const m = ev.data;
  if (m.tipo === "listo") return arrancarUI();
  if (m.tipo === "fallo") return mostrarError("No se pudo cargar el motor: " + m.error, true);
  const p = pendientes.get(m.id);
  if (!p) return;
  pendientes.delete(m.id);
  if (m.error) p.reject(new Error(m.error)); else p.resolve(m.resultado);
};
function py(cmd, ...args) {
  return new Promise((resolve, reject) => {
    const id = siguienteId++;
    pendientes.set(id, { resolve, reject });
    worker.postMessage({ id, cmd, args });
  });
}
const pyJSON = async (cmd, ...args) => JSON.parse(await py(cmd, ...args));

function mostrarError(texto, fatal) {
  el.error.textContent = texto;
  el.error.hidden = false;
  if (fatal) $("cargando").hidden = true;
  setTimeout(() => { if (!fatal) el.error.hidden = true; }, 5000);
}

// ---------- utilidades ----------
const idx = (txt) => "abcdefgh".indexOf(txt[0]) + (parseInt(txt[1], 10) - 1) * 8;
const nombreCasilla = (i) => "abcdefgh"[i % 8] + (Math.floor(i / 8) + 1);
const esBlanca = (s) => s !== "" && s === s.toUpperCase();
const orientacionBlancas = () => (S.orientacion === "white") !== girado;
const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} };
const leer = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };

// ---------- arranque ----------
async function arrancarUI() {
  const bots = await pyJSON("bots");
  for (const b of bots) el.selBot.add(new Option(b, b));
  el.selBot.add(new Option("👥 Otra persona (mismo dispositivo)", "humano"));
  el.selBot.add(new Option("🤖 Bot contra bot", "bots"));
  for (const b of bots) {
    el.selBlancas.add(new Option(b, b));
    el.selNegras.add(new Option(b, b));
  }
  const elegir = (sel, clave, porDefecto) => {
    const g = leer(clave);
    sel.value = bots.includes(g) ? g : porDefecto;
  };
  elegir(el.selBlancas, "bot_blancas", bots.includes("ml-4") ? "ml-4" : bots[bots.length - 1]);
  elegir(el.selNegras, "bot_negras", bots.includes("minimax-3") ? "minimax-3" : bots[0]);
  const vel = leer("velocidad");
  if (vel && [...el.selVel.options].some((o) => o.value === vel)) el.selVel.value = vel;
  bots.push("humano", "bots");
  const guardado = leer("bot");
  el.selBot.value = bots.includes(guardado) ? guardado : bots[Math.min(2, bots.length - 1)];
  const colorG = leer("color");
  if (colorG) document.querySelector(`input[name=color][value=${colorG}]`).checked = true;
  actualizarPista();

  construirTablero();
  $("cargando").hidden = true;
  $("app").hidden = false;
  await nuevaPartida();
}

function actualizarPista() {
  el.pista.textContent = DESCRIPCION_BOT[el.selBot.value] || "";
  const modo = el.selBot.value;
  document.querySelector("fieldset").hidden = modo === "humano" || modo === "bots";
  el.bloqueBots.hidden = modo !== "bots";
}

async function nuevaPartida() {
  const color = document.querySelector("input[name=color]:checked").value;
  const modo = el.selBot.value;
  guardar("bot", modo);
  guardar("color", color);
  guardar("bot_blancas", el.selBlancas.value);
  guardar("bot_negras", el.selNegras.value);
  const id = ++partida;
  ocupado = true;
  sel = null;
  girado = false;
  pausado = false;
  el.velo.hidden = true;
  const nuevo = modo === "bots"
    ? await pyJSON("nueva_bots", el.selBlancas.value, el.selNegras.value)
    : await pyJSON("nueva", color, modo);
  if (id !== partida) return; // mientras tanto se empezo otra partida
  S = nuevo;
  if (S.bvb) {
    ocupado = false;
    pintar();
    jugarBots(id);
    return;
  }
  pintar();
  await turnoDelBot();
}

// ---------- bot contra bot ----------
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

// Un bucle por partida: juega una jugada tras otra hasta que acaba o se empieza otra partida.
async function jugarBots(id) {
  while (id === partida && S.bvb && !S.terminada) {
    if (pausado || ocupado) { await esperar(80); continue; }
    await esperar(parseInt(el.selVel.value, 10));  // pausa para ver la posicion
    if (id !== partida || pausado || ocupado) continue;
    ocupado = true;
    pintar();
    try {
      const nuevo = await pyJSON("mover_bot");
      if (id !== partida) return;
      S = nuevo;
    } catch (e) {
      if (id !== partida) return;
      mostrarError("Error del bot: " + e);
      pausado = true; // para no repetir el error sin parar
    }
    ocupado = false;
    pintar();
  }
}

// Con la partida en pausa, juega solo una jugada.
async function unPaso() {
  if (!S || !S.bvb || S.terminada || ocupado || !pausado) return;
  const id = partida;
  ocupado = true;
  pintar();
  try {
    const nuevo = await pyJSON("mover_bot");
    if (id === partida) S = nuevo;
  } catch (e) {
    if (id === partida) mostrarError("Error del bot: " + e);
  }
  if (id !== partida) return;
  ocupado = false;
  pintar();
}

// ---------- tablero ----------
function construirTablero() {
  el.tablero.textContent = "";
  casillas = [];
  for (let v = 0; v < 64; v++) {
    const d = document.createElement("div");
    d.className = "casilla";
    d.setAttribute("role", "gridcell");
    d.dataset.visual = v;
    el.tablero.appendChild(d);
    casillas.push(d);
  }
}

// Convierte la posicion visual (0..63, de arriba-izquierda) en la casilla real.
function realDeVisual(v) {
  const fila = Math.floor(v / 8), col = v % 8;
  return orientacionBlancas() ? (7 - fila) * 8 + col : fila * 8 + (7 - col);
}

function destinosDesde(origen) {
  const m = new Map(); // destino -> [jugadas]
  const txt = nombreCasilla(origen);
  for (const j of S.legales) {
    if (j.startsWith(txt)) {
      const d = idx(j.slice(2, 4));
      if (!m.has(d)) m.set(d, []);
      m.get(d).push(j);
    }
  }
  return m;
}

function pintar() {
  const destinos = sel !== null ? destinosDesde(sel) : new Map();
  const ultimaO = S.ultima ? idx(S.ultima.slice(0, 2)) : -1;
  const ultimaD = S.ultima ? idx(S.ultima.slice(2, 4)) : -1;
  const blancasAbajo = orientacionBlancas();
  const puedoMover = !ocupado && !S.terminada && S.turno === S.humano;

  for (let v = 0; v < 64; v++) {
    const i = realDeVisual(v);
    const d = casillas[v];
    const pieza = S.casillas[i];
    const clara = ((i % 8) + Math.floor(i / 8)) % 2 === 1;
    d.className = "casilla " + (clara ? "clara" : "oscura");
    if (i === ultimaO || i === ultimaD) d.classList.add("ultima");
    if (i === sel) d.classList.add("seleccionada");
    if (i === S.rey_en_jaque) d.classList.add("jaque");
    if (destinos.has(i)) d.classList.add("destino", ...(pieza || esAlPaso(sel, i) ? ["captura"] : []));
    const propia = pieza && (esBlanca(pieza) === (S.humano === "white"));
    if (puedoMover && propia) d.classList.add("mia");
    d.dataset.real = i;
    d.setAttribute("aria-label", nombreCasilla(i) + (pieza ? ", " + pieza : ""));

    d.textContent = "";
    if (pieza) {
      const p = document.createElement("span");
      p.className = "pieza " + (esBlanca(pieza) ? "blanca" : "negra");
      p.textContent = GLIFOS[pieza.toLowerCase()] + VS15;
      d.appendChild(p);
    }
    const fila = Math.floor(v / 8), col = v % 8;
    if (col === 0) d.appendChild(coord("fila", String(Math.floor(i / 8) + 1)));
    if (fila === 7) d.appendChild(coord("col", "abcdefgh"[i % 8]));
  }

  pintarJugadores();
  pintarEstado();
  pintarJugadas();
  el.btnDeshacer.disabled = ocupado || S.historial.length === 0 || S.bvb;
  // En bot contra bot se puede empezar otra partida en cualquier momento.
  el.btnNueva.disabled = ocupado && !S.bvb;
  el.ctrlBots.hidden = !S.bvb;
  if (S.bvb) {
    el.btnPausa.textContent = pausado ? "▶ Seguir" : "⏸ Pausa";
    el.btnPausa.disabled = S.terminada;
    el.btnPaso.disabled = !pausado || ocupado || S.terminada;
  }
}

function esAlPaso(origen, destino) {
  if (origen === null || !S) return false;
  const p = S.casillas[origen];
  return p && p.toLowerCase() === "p" && origen % 8 !== destino % 8 && !S.casillas[destino];
}

function coord(clase, texto) {
  const s = document.createElement("span");
  s.className = "coord " + clase;
  s.textContent = texto;
  return s;
}

function pintarJugadores() {
  const abajoColor = orientacionBlancas() ? "white" : "black";
  const arribaColor = abajoColor === "white" ? "black" : "white";
  const quien = (color) => {
    const lado = color === "white" ? "blancas" : "negras";
    if (S.bvb) return "Bot " + (color === "white" ? S.bot_blancas : S.bot_negras) + " · " + lado;
    if (S.dos) return color === "white" ? "Blancas" : "Negras";
    return (color === S.humano ? "Tú" : "Bot " + S.bot) + " · " + lado;
  };
  const llenar = (cont, color) => {
    cont.querySelector(".nombre").textContent = quien(color);
    const c = cont.querySelector(".capturas");
    c.textContent = "";
    // Las piezas que he capturado son las del color contrario que faltan.
    const rival = color === "white" ? "black" : "white";
    const g = document.createElement("span");
    g.className = "grupo";
    const orden = { q: 0, r: 1, b: 2, n: 3, p: 4 };
    g.textContent = S.capturadas[rival].slice()
      .sort((a, b) => orden[a.toLowerCase()] - orden[b.toLowerCase()])
      .map((s) => GLIFOS[s.toLowerCase()] + VS15).join("");
    c.appendChild(g);
    const ventaja = color === "white" ? S.ventaja : -S.ventaja;
    if (ventaja > 0) {
      const v = document.createElement("span");
      v.className = "ventaja";
      v.textContent = "+" + ventaja;
      c.appendChild(v);
    }
  };
  // Abajo van las blancas (o las del humano si juega con negras), salvo que se gire el tablero.
  llenar(el.abajo, abajoColor);
  llenar(el.arriba, arribaColor);
}

const MOTIVOS = {
  "jaque mate": "jaque mate", "ahogado": "ahogado (el rey no está en jaque pero no hay jugadas)",
  "material insuficiente": "material insuficiente", "triple repeticion": "triple repetición",
  "regla de los 50 movimientos": "la regla de los 50 movimientos",
};

function pintarEstado() {
  el.estado.className = "tarjeta estado";
  el.estadoSub.textContent = "";
  if (S.terminada) {
    el.estado.classList.add("fin");
    let titulo;
    if (S.ganador === null) titulo = "Tablas";
    else if (S.bvb) {
      const blancas = S.ganador === "white";
      titulo = "Ganan las " + (blancas ? "blancas" : "negras") + " (" + (blancas ? S.bot_blancas : S.bot_negras) + ")";
    }
    else if (S.dos) titulo = "Ganan las " + (S.ganador === "white" ? "blancas" : "negras");
    else titulo = S.ganador === S.humano ? "¡Has ganado!" : "Has perdido";
    el.estadoTexto.textContent = titulo;
    el.estadoSub.textContent = "Por " + (MOTIVOS[S.motivo] || S.motivo) + " (" + S.resultado + ")";
    el.velo.innerHTML = "";
    const caja = document.createElement("div");
    caja.className = "caja";
    caja.innerHTML = "<strong></strong><span class='suave'></span><br>";
    caja.querySelector("strong").textContent = titulo;
    caja.querySelector("span").textContent = "Por " + (MOTIVOS[S.motivo] || S.motivo);
    const b = document.createElement("button");
    b.className = "primario";
    b.textContent = S.bvb ? "Otra partida" : "Jugar otra vez";
    b.onclick = () => nuevaPartida();
    const v = document.createElement("button");
    v.textContent = "Ver el tablero";
    v.style.marginLeft = "8px";
    v.onclick = () => { el.velo.hidden = true; };
    caja.append(b, v);
    el.velo.appendChild(caja);
    el.velo.hidden = false;
    return;
  }
  el.velo.hidden = true;
  if (S.bvb) {
    const lado = S.turno === "white" ? "blancas" : "negras";
    const bot = S.turno === "white" ? S.bot_blancas : S.bot_negras;
    if (ocupado) {
      el.estado.classList.add("pensando");
      el.estadoTexto.textContent = "Piensa " + bot + " (" + lado + ")";
      el.estadoSub.textContent = TIEMPO_BOT[bot] || "";
    } else if (pausado) {
      el.estadoTexto.textContent = "En pausa · turno de las " + lado;
      el.estadoSub.textContent = "Pulsa «Seguir» o «Un paso».";
    } else {
      el.estadoTexto.textContent = "Turno de las " + lado + " · " + bot;
    }
    if (S.jaque) { el.estado.classList.add("alerta"); el.estadoSub.textContent = "¡Jaque!"; }
    return;
  }
  if (S.turno === S.humano) {
    const lado = S.humano === "white" ? "blancas" : "negras";
    el.estadoTexto.textContent = S.dos ? "Turno de las " + lado : "Tu turno (" + lado + ")";
    if (S.jaque) { el.estado.classList.add("alerta"); el.estadoSub.textContent = S.dos ? "¡Jaque!" : "¡Estás en jaque!"; }
    else el.estadoSub.textContent = "Arrastra una pieza o púlsala y pulsa su destino.";
  } else {
    el.estado.classList.add("pensando");
    el.estadoTexto.textContent = "El bot está pensando";
    el.estadoSub.textContent = TIEMPO_BOT[S.bot] || "";
  }
}

function pintarJugadas() {
  el.jugadas.textContent = "";
  if (S.historial.length === 0) {
    const li = document.createElement("li");
    li.className = "vacio";
    li.textContent = "Todavía no hay jugadas.";
    el.jugadas.appendChild(li);
    return;
  }
  const h = S.historial;
  for (let i = 0; i < h.length; i += 2) {
    const n = document.createElement("li");
    n.className = "num";
    n.textContent = i / 2 + 1 + ".";
    el.jugadas.appendChild(n);
    for (const k of [i, i + 1]) {
      const li = document.createElement("li");
      if (h[k]) { li.textContent = h[k]; if (k === h.length - 1) li.className = "ult"; }
      el.jugadas.appendChild(li);
    }
  }
  el.jugadas.scrollTop = el.jugadas.scrollHeight;
}

// ---------- jugar ----------
async function intentarMover(origen, destino) {
  const prefijo = nombreCasilla(origen) + nombreCasilla(destino);
  const candidatas = S.legales.filter((j) => j.startsWith(prefijo));
  if (candidatas.length === 0) return false;
  let jugada = candidatas[0];
  if (candidatas.length > 1) {
    const pieza = await pedirPromocion();
    jugada = prefijo + pieza;
  }
  await jugarHumano(jugada);
  return true;
}

function pedirPromocion() {
  return new Promise((resolve) => {
    el.promoOpc.textContent = "";
    const color = S.humano === "white" ? "blanca" : "negra";
    const nombres = { q: "Dama", r: "Torre", b: "Alfil", n: "Caballo" };
    for (const p of PIEZAS_PROMO) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = color;
      b.textContent = GLIFOS[p] + VS15;
      b.title = nombres[p];
      b.setAttribute("aria-label", nombres[p]);
      b.onclick = () => { el.dlg.close(); resolve(p); };
      el.promoOpc.appendChild(b);
    }
    el.dlg.oncancel = (e) => e.preventDefault(); // hay que elegir una pieza
    el.dlg.showModal();
  });
}

async function jugarHumano(jugada) {
  ocupado = true;
  sel = null;
  try {
    S = await pyJSON("jugar", jugada);
  } catch (e) {
    mostrarError(String(e));
    S = await pyJSON("estado");
    ocupado = false;
    pintar();
    return;
  }
  pintar();
  await turnoDelBot();
}

async function turnoDelBot() {
  if (S.terminada || S.turno === S.humano) { ocupado = false; pintar(); return; }
  ocupado = true;
  pintar();
  // Pequeña pausa para que se vea tu jugada antes de que el bot responda.
  await new Promise((r) => setTimeout(r, 250));
  try {
    S = await pyJSON("mover_bot");
  } catch (e) {
    mostrarError("Error del bot: " + e);
  }
  ocupado = false;
  pintar();
}

// ---------- entrada: clic y arrastrar ----------
let arrastre = null;

el.tablero.addEventListener("pointerdown", (ev) => {
  if (ocupado || !S || S.terminada || S.turno !== S.humano || ev.button > 0) return;
  const d = ev.target.closest(".casilla");
  if (!d) return;
  const i = parseInt(d.dataset.real, 10);
  const pieza = S.casillas[i];
  const propia = pieza && (esBlanca(pieza) === (S.humano === "white"));

  if (sel !== null && sel !== i && destinosDesde(sel).has(i)) {
    // Segundo clic sobre un destino valido.
    intentarMover(sel, i);
    return;
  }
  if (propia) {
    sel = i;
    pintar();
    const glifo = d.querySelector(".pieza");
    arrastre = { origen: i, x: ev.clientX, y: ev.clientY, movido: false, glifo, fantasma: null };
    el.tablero.setPointerCapture(ev.pointerId);
  } else {
    sel = null;
    pintar();
  }
});

el.tablero.addEventListener("pointermove", (ev) => {
  if (!arrastre) return;
  if (!arrastre.movido && Math.hypot(ev.clientX - arrastre.x, ev.clientY - arrastre.y) < 6) return;
  if (!arrastre.movido) {
    arrastre.movido = true;
    const f = document.createElement("div");
    f.className = "fantasma " + arrastre.glifo.className.replace("pieza ", "");
    f.textContent = arrastre.glifo.textContent;
    const lado = el.tablero.getBoundingClientRect().width / 8;
    f.style.fontSize = lado * 0.76 + "px";
    document.body.appendChild(f);
    arrastre.fantasma = f;
    arrastre.glifo.style.opacity = "0.25";
  }
  arrastre.fantasma.style.left = ev.clientX + "px";
  arrastre.fantasma.style.top = ev.clientY + "px";
});

async function terminarArrastre(ev, cancelar) {
  if (!arrastre) return;
  const a = arrastre;
  arrastre = null;
  if (a.fantasma) a.fantasma.remove();
  a.glifo.style.opacity = "";
  if (!a.movido || cancelar) return;
  const bajo = document.elementFromPoint(ev.clientX, ev.clientY);
  const d = bajo && bajo.closest ? bajo.closest(".casilla") : null;
  if (!d) return;
  const destino = parseInt(d.dataset.real, 10);
  if (destino === a.origen) return;
  if (!(await intentarMover(a.origen, destino))) { sel = null; pintar(); }
}
el.tablero.addEventListener("pointerup", (ev) => terminarArrastre(ev, false));
el.tablero.addEventListener("pointercancel", (ev) => terminarArrastre(ev, true));

// ---------- botones ----------
el.btnNueva.onclick = () => nuevaPartida();
el.selBot.onchange = actualizarPista;
el.btnPausa.onclick = () => { pausado = !pausado; if (S) pintar(); };
el.btnPaso.onclick = () => unPaso();
el.selVel.onchange = () => guardar("velocidad", el.selVel.value);
el.btnGirar.onclick = () => { girado = !girado; pintar(); };
el.btnDeshacer.onclick = async () => {
  if (ocupado) return;
  ocupado = true;
  sel = null;
  S = await pyJSON("deshacer");
  await turnoDelBot();
};
el.btnFen.onclick = async () => {
  try {
    await navigator.clipboard.writeText(S.fen);
    el.btnFen.textContent = "¡Copiado!";
  } catch (_) {
    el.btnFen.textContent = S.fen;
  }
  setTimeout(() => { el.btnFen.textContent = "Copiar posición (FEN)"; }, 2500);
};
