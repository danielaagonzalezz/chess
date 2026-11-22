"""
Torneo: enfrenta a todos los bots del catalogo y produce una clasificacion.

Cada pareja de bots juega varias partidas, cambiando de color y empezando
desde aperturas distintas (unas pocas jugadas al azar, iguales para los dos
bots de la pareja), porque casi todos los bots son deterministas y sin esto
repetirian siempre la misma partida.

Un bot que falla NO rompe el torneo. Cada bot juega en su propio proceso,
asi que:

  - si lanza una excepcion            -> pierde la partida ("excepcion")
  - si devuelve una jugada ilegal     -> pierde la partida ("ilegal")
  - si tarda mas del tiempo maximo    -> pierde la partida ("tiempo"), y
                                         su proceso se mata
  - si el proceso se cae del todo     -> pierde la partida ("caida")

Puntuacion: victoria 1, tablas 0.5, derrota 0. Ademas se calcula un Elo
aproximado (la media del torneo vale 1000). Si una partida pasa del maximo
de jugadas se da por tablas.

Uso desde la terminal:

    python -m chess.torneo                       (todos los bots de BOTS)
    python -m chess.torneo --partidas 4 --paralelo 4
    python -m chess.torneo --bots aleatorio,1-paso,minimax-2
    python -m chess.torneo --salida clasificacion/

Escribe clasificacion.json, clasificacion.md y clasificacion.html en la
carpeta de salida. El workflow de GitHub Actions lo ejecuta y publica el
resultado en GitHub Pages.
"""

import argparse
import itertools
import math
import multiprocessing
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from chess.bots import BOTS
from chess.game import (
    AHOGADO, JAQUE_MATE, MATERIAL_INSUFICIENTE, REGLA_50_MOVIMIENTOS, RESULTADO_BLANCAS,
    RESULTADO_NEGRAS, RESULTADO_TABLAS, TRIPLE_REPETICION, Game,
)
from chess.move import Move

# Valores por defecto.
TIEMPO_MAXIMO = 15      # segundos por jugada (cada bot lleva su propio limite menor)
TIEMPO_ARRANQUE = 60    # segundos para crear el bot (cargar pesos, etc.)
MAX_JUGADAS = 160       # medias jugadas; si se pasa, tablas
JUGADAS_APERTURA = 4    # medias jugadas al azar al empezar cada pareja
PARTIDAS_POR_PAREJA = 2  # siempre par: la mitad con cada color

# Motivos de partida perdida por culpa del bot.
FALLOS = ("excepcion", "ilegal", "tiempo", "caida", "arranque")

LIMITE_JUGADAS = "limite de jugadas"


# ---------------------------------------------------------
# Un bot por proceso
# ---------------------------------------------------------

def _trabajador(conexion, nombre, fabrica):
    """
    Codigo del proceso de un bot. Crea el bot y responde a peticiones.

    Recibe (fen_inicial, jugadas): reconstruye la partida y contesta con
    ("jugada", texto) o con el motivo del fallo.
    """
    try:
        bot = fabrica() if fabrica is not None else BOTS[nombre]()
        conexion.send(("listo", None))
    except BaseException as error:  # noqa: BLE001 - el bot es codigo ajeno
        conexion.send(("excepcion", "%s: %s" % (type(error).__name__, error)))
        return
    while True:
        try:
            peticion = conexion.recv()
        except EOFError:
            return
        if peticion is None:
            return
        fen_inicial, jugadas = peticion
        try:
            game = Game.desde_fen(fen_inicial)
            for jugada in jugadas:
                game.jugar(jugada)
            elegida = bot.choose_move(game.copy())
            if not isinstance(elegida, Move):
                conexion.send(("ilegal", "no devuelve una Move: %r" % (elegida,)))
            else:
                conexion.send(("jugada", str(elegida)))
        except BaseException as error:  # noqa: BLE001
            conexion.send(("excepcion", "%s: %s" % (type(error).__name__, error)))


class _Jugador:
    """El proceso de un bot, visto desde el torneo."""

    def __init__(self, nombre, fabrica):
        contexto = multiprocessing.get_context("spawn")
        self._padre, hijo = contexto.Pipe()
        self._proceso = contexto.Process(
            target=_trabajador, args=(hijo, nombre, fabrica), daemon=True
        )
        self._proceso.start()
        hijo.close()

    def esperar(self, segundos):
        """Espera una respuesta. Devuelve (tipo, dato); 'tiempo' o 'caida' si falla."""
        try:
            if not self._padre.poll(segundos):
                return "tiempo", "mas de %g s" % segundos
            return self._padre.recv()
        except (EOFError, OSError):
            return "caida", "el proceso del bot termino de golpe"

    def pedir_jugada(self, fen_inicial, jugadas, segundos):
        try:
            self._padre.send((fen_inicial, jugadas))
        except (BrokenPipeError, OSError):
            return "caida", "el proceso del bot termino de golpe"
        return self.esperar(segundos)

    def cerrar(self):
        try:
            self._padre.send(None)
        except (BrokenPipeError, OSError):
            pass
        self._proceso.join(timeout=1)
        if self._proceso.is_alive():
            self._proceso.kill()
            self._proceso.join(timeout=5)
        self._padre.close()


# ---------------------------------------------------------
# Una partida
# ---------------------------------------------------------

def _apertura(semilla, jugadas_apertura):
    """Partida tras unas jugadas al azar. Devuelve (partida, jugadas en texto)."""
    azar = random.Random(semilla)
    game = Game()
    jugadas = []
    for _ in range(jugadas_apertura):
        if game.esta_terminada():
            break
        jugada = azar.choice(game.jugadas_legales())
        game.jugar(jugada)
        jugadas.append(str(jugada))
    return game, jugadas


def jugar_partida(blancas, negras, semilla=0, jugadas_apertura=JUGADAS_APERTURA,
                  tiempo_maximo=TIEMPO_MAXIMO, max_jugadas=MAX_JUGADAS):
    """
    Juega una partida entre dos bots. 'blancas' y 'negras' son tuplas
    (nombre, fabrica); la fabrica es una funcion sin argumentos que crea el
    bot (o None para usar BOTS[nombre]).

    Devuelve un diccionario con el resultado, el motivo, quien fallo (si
    alguien fallo) y las jugadas.
    """
    partida, apertura = _apertura(semilla, jugadas_apertura)
    fen_inicial = partida.fen()
    jugadores = {}
    resultado = motivo = fallo = None
    jugadas = []
    try:
        for color, (nombre, fabrica) in (("white", blancas), ("black", negras)):
            jugadores[color] = _Jugador(nombre, fabrica)
        # Los dos bots arrancan a la vez; se espera a cada uno.
        for color, jugador in jugadores.items():
            tipo, dato = jugador.esperar(TIEMPO_ARRANQUE)
            if tipo != "listo":
                fallo = fallo or {}
                fallo[color] = ("arranque", dato if tipo != "tiempo" else "no arranco a tiempo")
        if fallo:
            if len(fallo) == 2:
                resultado, motivo = RESULTADO_TABLAS, "los dos bots fallaron al arrancar"
            else:
                perdedor = next(iter(fallo))
                resultado = RESULTADO_NEGRAS if perdedor == "white" else RESULTADO_BLANCAS
                motivo = "arranque: " + fallo[perdedor][1]
        while resultado is None:
            if partida.esta_terminada():
                resultado, motivo = partida.resultado, partida.motivo
                break
            if len(partida.historial) >= max_jugadas:
                resultado, motivo = RESULTADO_TABLAS, LIMITE_JUGADAS
                break
            color = partida.turno
            tipo, dato = jugadores[color].pedir_jugada(fen_inicial, jugadas, tiempo_maximo)
            legales = {str(j): j for j in partida.jugadas_legales()}
            if tipo == "jugada" and dato in legales:
                partida.jugar(legales[dato])
                jugadas.append(dato)
                continue
            if tipo == "jugada":
                tipo, dato = "ilegal", "jugada ilegal: " + str(dato)
            fallo = {color: (tipo, dato)}
            resultado = RESULTADO_NEGRAS if color == "white" else RESULTADO_BLANCAS
            motivo = "%s: %s" % (tipo, dato)
    finally:
        for jugador in jugadores.values():
            jugador.cerrar()

    return {
        "blancas": blancas[0],
        "negras": negras[0],
        "resultado": resultado,
        "motivo": motivo,
        "fallo": None if not fallo else {
            ("blancas" if c == "white" else "negras"): tipo for c, (tipo, _) in fallo.items()
        },
        "apertura": apertura,
        "jugadas": " ".join(apertura + jugadas),
        "medias_jugadas": len(apertura) + len(jugadas),
    }


# ---------------------------------------------------------
# El torneo
# ---------------------------------------------------------

def _puntos(resultado, color):
    """Puntos que obtiene 'color' con ese resultado."""
    if resultado == RESULTADO_TABLAS:
        return 0.5
    gana_blancas = resultado == RESULTADO_BLANCAS
    return 1.0 if gana_blancas == (color == "white") else 0.0


def calcular_elo(nombres, partidas, ancla=1000):
    """
    Elo aproximado de cada bot a partir de los resultados.

    Ajusta las valoraciones para que los resultados esperados coincidan con
    los reales (maxima verosimilitud). Se anade una partida de tablas contra
    un rival ficticio de valor 'ancla', para que un bot que gana (o pierde)
    todas sus partidas no tenga un Elo infinito. La media queda en 'ancla'.
    """
    elo = {nombre: 0.0 for nombre in nombres}
    jugadas = {nombre: [] for nombre in nombres}  # (rival, puntos)
    for p in partidas:
        jugadas[p["blancas"]].append((p["negras"], _puntos(p["resultado"], "white")))
        jugadas[p["negras"]].append((p["blancas"], _puntos(p["resultado"], "black")))

    def esperado(a, b):
        return 1 / (1 + 10 ** ((b - a) / 400))

    for _ in range(2000):
        cambio_maximo = 0.0
        nuevo = {}
        for nombre in nombres:
            real = 0.5  # la partida ficticia: tablas contra el ancla
            previsto = esperado(elo[nombre], 0.0)
            for rival, puntos in jugadas[nombre]:
                real += puntos
                previsto += esperado(elo[nombre], elo[rival])
            paso = 60 * (real - previsto) / (len(jugadas[nombre]) + 1)
            nuevo[nombre] = elo[nombre] + paso
            cambio_maximo = max(cambio_maximo, abs(paso))
        elo = nuevo
        if cambio_maximo < 0.01:
            break
    media = sum(elo.values()) / len(elo) if elo else 0
    return {nombre: round(ancla + valor - media) for nombre, valor in elo.items()}


def _resumir(nombres, partidas):
    """Tabla de clasificacion ordenada: puntos, luego Elo."""
    elo = calcular_elo(nombres, partidas)
    filas = {
        nombre: {
            "bot": nombre, "partidas": 0, "puntos": 0.0, "victorias": 0,
            "tablas": 0, "derrotas": 0, "fallos": 0,
        }
        for nombre in nombres
    }
    for p in partidas:
        for color, clave in (("white", "blancas"), ("black", "negras")):
            fila = filas[p[clave]]
            puntos = _puntos(p["resultado"], color)
            fila["partidas"] += 1
            fila["puntos"] += puntos
            fila["victorias"] += puntos == 1.0
            fila["tablas"] += puntos == 0.5
            fila["derrotas"] += puntos == 0.0
            if p["fallo"] and clave in p["fallo"]:
                fila["fallos"] += 1
    tabla = sorted(filas.values(), key=lambda f: (-f["puntos"], -elo[f["bot"]], f["bot"]))
    for posicion, fila in enumerate(tabla, 1):
        fila["posicion"] = posicion
        fila["elo"] = elo[fila["bot"]]
    return tabla


def _cruces(nombres, partidas):
    """Matriz {bot: {rival: puntos}} con los puntos de cada bot contra cada rival."""
    matriz = {a: {b: 0.0 for b in nombres if b != a} for a in nombres}
    for p in partidas:
        matriz[p["blancas"]][p["negras"]] += _puntos(p["resultado"], "white")
        matriz[p["negras"]][p["blancas"]] += _puntos(p["resultado"], "black")
    return matriz


def jugar_torneo(bots=None, partidas_por_pareja=PARTIDAS_POR_PAREJA, semilla=0,
                 jugadas_apertura=JUGADAS_APERTURA, tiempo_maximo=TIEMPO_MAXIMO,
                 max_jugadas=MAX_JUGADAS, paralelo=1, progreso=None):
    """
    Enfrenta a todos los bots contra todos.

    - bots: diccionario {nombre: fabrica}. Por defecto, el catalogo BOTS.
    - partidas_por_pareja: debe ser par (la mitad con cada color).
    - paralelo: cuantas partidas se juegan a la vez.
    - progreso: funcion opcional que recibe un texto cada vez que acaba una partida.

    Devuelve un diccionario listo para guardar como JSON.
    """
    bots = dict(BOTS if bots is None else bots)
    if len(bots) < 2:
        raise ValueError("hacen falta al menos dos bots para un torneo")
    if partidas_por_pareja < 2 or partidas_por_pareja % 2:
        raise ValueError("partidas_por_pareja debe ser un numero par (2, 4, ...)")

    def fabrica_de(nombre):
        # Los bots del catalogo se recrean por nombre en el otro proceso
        # (las fabricas del catalogo son funciones locales, no se pueden enviar).
        return None if bots[nombre] is BOTS.get(nombre) else bots[nombre]

    nombres = sorted(bots)
    trabajos = []
    for i, (a, b) in enumerate(itertools.combinations(nombres, 2)):
        for k in range(partidas_por_pareja // 2):
            # La misma apertura con los dos colores.
            semilla_apertura = semilla * 100003 + i * 1009 + k
            trabajos.append((a, b, semilla_apertura))
            trabajos.append((b, a, semilla_apertura))

    inicio = time.time()
    partidas = []

    def ejecutar(trabajo):
        blancas, negras, semilla_apertura = trabajo
        try:
            return jugar_partida(
                (blancas, fabrica_de(blancas)), (negras, fabrica_de(negras)),
                semilla_apertura, jugadas_apertura, tiempo_maximo, max_jugadas,
            )
        except Exception as error:  # un fallo del propio torneo no debe romperlo todo
            return {
                "blancas": blancas, "negras": negras, "resultado": RESULTADO_TABLAS,
                "motivo": "error del torneo: %s: %s" % (type(error).__name__, error),
                "fallo": None, "apertura": [], "jugadas": "", "medias_jugadas": 0,
            }

    with ThreadPoolExecutor(max_workers=max(1, paralelo)) as pool:
        for hecha in pool.map(ejecutar, trabajos):
            partidas.append(hecha)
            if progreso:
                progreso("[%d/%d] %s - %s: %s (%s)" % (
                    len(partidas), len(trabajos), hecha["blancas"], hecha["negras"],
                    hecha["resultado"], hecha["motivo"],
                ))

    return {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "duracion_segundos": round(time.time() - inicio),
        "configuracion": {
            "partidas_por_pareja": partidas_por_pareja,
            "jugadas_apertura": jugadas_apertura,
            "max_jugadas": max_jugadas,
            "tiempo_maximo_por_jugada": tiempo_maximo,
            "semilla": semilla,
        },
        "clasificacion": _resumir(nombres, partidas),
        "cruces": _cruces(nombres, partidas),
        "partidas": partidas,
    }


# ---------------------------------------------------------
# Salidas: markdown y html
# ---------------------------------------------------------

def _formato(puntos):
    return ("%g" % puntos).replace(".5", ",5")


def a_markdown(torneo):
    """La clasificacion como tabla markdown."""
    c = torneo["configuracion"]
    lineas = [
        "# Clasificación de bots",
        "",
        "Generada el %s (%d partidas, %d s)." % (
            torneo["generado"], len(torneo["partidas"]), torneo["duracion_segundos"]),
        "",
        "| # | Bot | Elo | Puntos | Partidas | V | T | D | Fallos |",
        "|--:|---|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for f in torneo["clasificacion"]:
        lineas.append("| %d | `%s` | %d | %s | %d | %d | %d | %d | %d |" % (
            f["posicion"], f["bot"], f["elo"], _formato(f["puntos"]), f["partidas"],
            f["victorias"], f["tablas"], f["derrotas"], f["fallos"]))
    lineas += [
        "",
        "Cada pareja juega %d partidas (colores alternados, aperturas al azar), con un "
        "máximo de %d medias jugadas (si se pasa, tablas)." % (
            c["partidas_por_pareja"], c["max_jugadas"]),
    ]
    return "\n".join(lineas) + "\n"


_PLANTILLA_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clasificación de bots</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&display=swap">
<style>
:root {
  --fondo:#0c0c0e; --superficie:#18181c; --texto:#ecebe7; --suave:#a19e97; --borde:#33333a;
  --acento:#d9bf85; --acento-texto:#121216; --mal:#f97066;
  --gana:#5aa889; --tablas:#8f8466; --pierde:#d06a52;
  --celda-gana:#2f735a; --celda-pierde:#8c3b2b; --celda-neutra:#24242a;
  --oro:#e3b941; --plata:#c3c9d1; --bronce:#cf8a55;
  --metal:linear-gradient(165deg, #ffffff 0%, #dfe2e6 22%, #8b9098 48%, #eef0f2 66%, #9aa0a8 82%, #5e636a 100%);
  --sombra:0 1px 2px rgba(0,0,0,.5), 0 12px 32px rgba(0,0,0,.45);
  --titulos:"Cinzel", "Trajan Pro", Georgia, serif;
  color-scheme:dark;
}
* { box-sizing:border-box; }
html, body { margin:0; }
body { background:radial-gradient(ellipse 90% 50% at 50% -10%, #2c2c33 0%, #141417 55%, var(--fondo) 100%) fixed, var(--fondo);
       color:var(--texto); font:16px/1.5 system-ui, "Segoe UI", sans-serif; }
main { max-width:980px; margin:0 auto; padding:28px 16px 56px; }
a { color:var(--acento); }
.mono { font-family:ui-monospace, "Cascadia Mono", Consolas, monospace; }

/* Cabecera */
.cabecera { display:flex; flex-wrap:wrap; gap:12px 24px; align-items:end; justify-content:space-between; }
h1 { margin:0; font-family:var(--titulos); font-size:clamp(1.6rem, 4vw, 2.2rem); letter-spacing:.04em;
     background:var(--metal); -webkit-background-clip:text; background-clip:text; color:transparent; }
h1 .icono { -webkit-text-fill-color:initial; }
.cabecera p { margin:4px 0 0; color:var(--suave); }
.botones { display:flex; flex-wrap:wrap; gap:8px; }
.boton { display:inline-flex; align-items:center; gap:6px; padding:8px 14px; border-radius:999px;
         border:1px solid var(--borde); background:var(--superficie); color:var(--texto);
         text-decoration:none; font-weight:600; font-size:.92rem; transition:transform .15s, box-shadow .15s; }
.boton:hover { transform:translateY(-1px); box-shadow:var(--sombra); }
.boton.primario { background:var(--metal); color:var(--acento-texto); border-color:#6b7078; font-family:var(--titulos); letter-spacing:.05em; }

/* Cifras */
.cifras { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin:24px 0; }
.cifra { background:var(--superficie); border:1px solid var(--borde); border-radius:14px; padding:14px 16px; }
.cifra b { display:block; font-size:1.6rem; line-height:1.2; font-variant-numeric:tabular-nums; }
.cifra span { color:var(--suave); font-size:.85rem; }

/* Podio */
.podio { display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; align-items:end; margin:8px 0 8px; }
.puesto { position:relative; background:linear-gradient(180deg, rgba(255,255,255,.05), transparent 50%), var(--superficie); border:1px solid var(--borde); border-radius:16px;
          padding:18px 16px 16px; text-align:center; box-shadow:var(--sombra);
          animation:subir .6s cubic-bezier(.2,.8,.2,1) both; }
.puesto::before { content:""; position:absolute; inset:0 0 auto; height:5px; border-radius:16px 16px 0 0; background:var(--medalla); }
.puesto.p1 { --medalla:var(--oro); order:2; padding-top:30px; animation-delay:.15s; }
.puesto.p2 { --medalla:var(--plata); order:1; animation-delay:.3s; }
.puesto.p3 { --medalla:var(--bronce); order:3; animation-delay:.45s; }
.medalla { width:44px; height:44px; margin:0 auto 8px; border-radius:50%; display:grid; place-items:center;
           font-weight:800; font-size:1.15rem; color:#2a2110;
           background:radial-gradient(circle at 35% 30%, rgba(255,255,255,.75), transparent 45%), var(--medalla);
           box-shadow:inset 0 -2px 0 rgba(0,0,0,.15); }
.p1 .medalla { width:56px; height:56px; font-size:1.4rem; }
.puesto .nombre { font-weight:700; font-size:1.05rem; overflow-wrap:anywhere; }
.puesto .elo { font-family:var(--titulos); font-size:2rem; font-weight:800; line-height:1.1; margin:6px 0 2px; font-variant-numeric:tabular-nums; }
.p1 .elo { font-size:2.5rem; }
.puesto .detalle { color:var(--suave); font-size:.85rem; }

/* Secciones */
section { margin-top:36px; }
h2 { margin:0 0 4px; font-family:var(--titulos); font-size:1.15rem; letter-spacing:.06em; }
h3 { margin:0 0 8px; font-size:.95rem; }
.intro { margin:0 0 12px; color:var(--suave); font-size:.92rem; }
.tarjeta { background:linear-gradient(180deg, rgba(255,255,255,.035), transparent 40%), var(--superficie); border:1px solid var(--borde); border-radius:14px; overflow-x:auto; }

/* Tabla */
table { border-collapse:collapse; width:100%; }
th, td { padding:10px 12px; border-bottom:1px solid var(--borde); text-align:right; white-space:nowrap; }
tbody tr:last-child td, tbody tr:last-child th { border-bottom:0; }
tbody tr { transition:background .15s; }
.clasificacion tbody tr:hover { background:color-mix(in srgb, var(--acento) 7%, transparent); }
thead th { font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; color:var(--suave); font-weight:600; }
.izq { text-align:left; }
.pos { width:2.5rem; text-align:center; font-weight:700; color:var(--suave); }
.chapa { display:inline-grid; place-items:center; width:26px; height:26px; border-radius:50%; color:#2a2110; background:var(--medalla); }
.clasificacion { min-width:680px; }
.col-elo { width:30%; }
.barra-elo { display:flex; align-items:center; gap:10px; }
.barra-elo b { min-width:3.2rem; text-align:right; font-variant-numeric:tabular-nums; }
.pista { flex:1; min-width:80px; height:10px; border-radius:999px; background:color-mix(in srgb, var(--borde) 60%, transparent); overflow:hidden; }
.relleno { height:100%; border-radius:999px; background:linear-gradient(90deg, color-mix(in srgb, var(--acento) 45%, transparent), var(--acento));
           transform-origin:left; animation:crecer .9s cubic-bezier(.2,.8,.2,1) both; }
.vtd { display:flex; width:150px; height:10px; border-radius:999px; overflow:hidden; margin-left:auto;
       transform-origin:left; animation:crecer .9s cubic-bezier(.2,.8,.2,1) both; }
.vtd span { display:block; height:100%; }
.v { background:var(--gana); } .t { background:var(--tablas); } .d { background:var(--pierde); }
.vtd-num { font-size:.8rem; color:var(--suave); margin-top:3px; font-variant-numeric:tabular-nums; }
td.num { font-variant-numeric:tabular-nums; }
td.mal { color:var(--mal); font-weight:700; }

/* Mapa de calor */
.cruces { min-width:560px; }
.cruces th, .cruces td { padding:8px 6px; text-align:center; }
.cruces thead th { writing-mode:vertical-rl; transform:rotate(180deg); text-transform:none; letter-spacing:0;
                   font-family:ui-monospace, Consolas, monospace; font-size:.78rem; height:7.5rem; vertical-align:bottom; padding:8px 4px; }
.cruces th.fila { text-align:left; font-family:ui-monospace, Consolas, monospace; font-size:.85rem; font-weight:600;
                  position:sticky; left:0; background:var(--superficie); padding-left:12px; }
.cruces td { border:2px solid var(--superficie); }
.cruces td.celda { min-width:42px; font-weight:600; font-variant-numeric:tabular-nums; border-radius:8px; transition:transform .15s; }
.cruces td.celda:hover { transform:scale(1.12); position:relative; z-index:1; box-shadow:var(--sombra); }
.cruces td.propio { background:repeating-linear-gradient(45deg, transparent 0 4px, color-mix(in srgb, var(--borde) 70%, transparent) 4px 6px); }
.leyenda { display:flex; flex-wrap:wrap; gap:6px 16px; align-items:center; margin-top:10px; font-size:.85rem; color:var(--suave); }
.leyenda i { display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
.degradado { width:140px; height:10px; border-radius:999px; background:linear-gradient(90deg, var(--celda-pierde), var(--celda-neutra), var(--celda-gana)); }

/* Como terminan */
.final { padding:16px; display:grid; gap:20px; }
.apilada { display:flex; height:28px; border-radius:8px; overflow:hidden; transform-origin:left; animation:crecer 1s cubic-bezier(.2,.8,.2,1) both; }
.apilada span { display:grid; place-items:center; color:#fff; font-size:.78rem; font-weight:700; min-width:0; overflow:hidden; text-shadow:0 1px 1px rgba(0,0,0,.3); }

.nota { color:var(--suave); font-size:.85rem; margin-top:24px; }
footer { margin-top:8px; color:var(--suave); font-size:.85rem; }

@keyframes crecer { from { transform:scaleX(0); } to { transform:scaleX(1); } }
@keyframes subir { from { opacity:0; transform:translateY(18px); } to { opacity:1; transform:none; } }
@media (prefers-reduced-motion: reduce) { *, *::before { animation:none !important; transition:none !important; } }
@media (max-width:600px) {
  .podio { grid-template-columns:1fr; gap:8px; }
  .puesto.p1, .puesto.p2, .puesto.p3 { order:0; padding:12px 14px 12px 16px; display:grid; text-align:left;
                                       grid-template-columns:auto 1fr auto; grid-template-areas:"m n e" "m d e" "m x e"; column-gap:12px; align-items:center; }
  .puesto::before { inset:0 auto 0 0; width:5px; height:auto; border-radius:16px 0 0 16px; }
  .puesto .medalla, .p1 .medalla { grid-area:m; width:40px; height:40px; font-size:1.1rem; margin:0; }
  .puesto .nombre { grid-area:n; }
  .puesto .elo, .p1 .elo { grid-area:e; font-size:1.6rem; margin:0; }
  .puesto .detalle { grid-area:d; font-size:.8rem; }
  .puesto .detalle + .detalle { grid-area:x; }
}
</style>
</head>
<body>
<main>
<header class="cabecera">
  <div>
    <h1><span class="icono">🏆</span> Clasificación de bots</h1>
    <p>{{resumen}}</p>
  </div>
  <nav class="botones">
    <a class="boton primario" href="./">♞ Juega contra ellos</a>
    <a class="boton" href="https://chess-ia.readthedocs.io/es/latest/subir-un-bot/">🤖 Crea tu bot</a>
  </nav>
</header>

<div class="cifras">{{cifras}}</div>

<div class="podio">{{podio}}</div>

<section>
  <h2>Clasificación completa</h2>
  <p class="intro">Ordenada por puntos (victoria 1, tablas ½, derrota 0) y, si empatan, por Elo.</p>
  <div class="tarjeta"><table class="clasificacion">
    <thead><tr><th class="pos">#</th><th class="izq">Bot</th><th class="izq col-elo">Elo</th><th>Puntos</th><th>Partidas</th><th>Victorias · tablas · derrotas</th><th>Fallos</th></tr></thead>
    <tbody>
{{filas}}
    </tbody>
  </table></div>
</section>

<section>
  <h2>Cada bot contra cada rival</h2>
  <p class="intro">Puntos que saca el bot de la fila contra el de la columna (de {{por_pareja}} posibles).</p>
  <div class="tarjeta"><table class="cruces">
    <thead><tr><th></th>{{cabecera_cruces}}</tr></thead>
    <tbody>
{{filas_cruces}}
    </tbody>
  </table></div>
  <div class="leyenda"><span>Pierde</span><span class="degradado"></span><span>Gana</span></div>
</section>

{{final}}

<p class="nota">Cada pareja juega {{por_pareja}} partidas con colores alternados y aperturas al azar
(iguales para los dos bots de la pareja). Si una partida pasa de {{max_jugadas}} medias jugadas se da por
tablas. Un bot que falla, se cuelga o hace una jugada ilegal pierde la partida, pero no rompe el
torneo. El Elo es aproximado (media 1000).</p>
<footer>Datos completos, con todas las partidas: <a href="clasificacion.json">clasificacion.json</a>.</footer>
</main>
</body>
</html>
"""

# Nombre y color de cada forma de acabar una partida.
_FINALES = [
    (JAQUE_MATE, "Jaque mate", "var(--gana)"),
    (LIMITE_JUGADAS, "Límite de jugadas", "#b5a072"),
    (TRIPLE_REPETICION, "Triple repetición", "#7c8aa5"),
    (AHOGADO, "Ahogado", "#9a7fb5"),
    (MATERIAL_INSUFICIENTE, "Material insuficiente", "#5d9bb5"),
    (REGLA_50_MOVIMIENTOS, "Regla de 50 movimientos", "#b5835d"),
]


def _barra_apilada(trozos, total):
    """Barra horizontal con un trozo por cada (etiqueta, cantidad, color)."""
    from html import escape

    partes, leyenda = [], []
    for etiqueta, cantidad, color in trozos:
        if not cantidad:
            continue
        porcentaje = 100.0 * cantidad / total
        texto = "%d%%" % round(porcentaje) if porcentaje >= 8 else ""
        partes.append('<span style="width:%.2f%%;background:%s" title="%s: %d">%s</span>' % (
            porcentaje, color, escape(etiqueta), cantidad, texto))
        leyenda.append('<span><i style="background:%s"></i>%s · %d</span>' % (
            color, escape(etiqueta), cantidad))
    return '<div class="apilada">%s</div><div class="leyenda">%s</div>' % (
        "".join(partes), "".join(leyenda))


def _seccion_final(partidas):
    """Graficos de como terminan las partidas y de si ganan mas las blancas o las negras."""
    if not partidas:
        return ""
    total = len(partidas)
    conocidos = {clave for clave, _, _ in _FINALES}
    trozos = [(etiqueta, sum(p["motivo"] == clave for p in partidas), color)
              for clave, etiqueta, color in _FINALES]
    trozos.append(("Fallo de un bot", sum(p["motivo"] not in conocidos for p in partidas), "var(--mal)"))
    blancas = sum(p["resultado"] == RESULTADO_BLANCAS for p in partidas)
    negras = sum(p["resultado"] == RESULTADO_NEGRAS for p in partidas)
    colores = [
        ("Ganan blancas", blancas, "#c2a868"),
        ("Tablas", total - blancas - negras, "#8d8a83"),
        ("Ganan negras", negras, "#3b3631"),
    ]
    return (
        '<section>\n  <h2>Cómo terminan las partidas</h2>\n'
        '  <p class="intro">Las %d partidas del torneo.</p>\n'
        '  <div class="tarjeta final">\n'
        '    <div><h3>Motivo del final</h3>%s</div>\n'
        '    <div><h3>Resultado por color</h3>%s</div>\n'
        '  </div>\n</section>' % (total, _barra_apilada(trozos, total),
                                  _barra_apilada(colores, total)))


def _color_celda(fraccion):
    """Color del mapa de calor: rojo si pierde, neutro si empata, verde si gana."""
    if fraccion >= 0.5:
        return "color-mix(in srgb, var(--celda-gana) %d%%, var(--celda-neutra))" % round((fraccion - 0.5) * 200)
    return "color-mix(in srgb, var(--celda-pierde) %d%%, var(--celda-neutra))" % round((0.5 - fraccion) * 200)


def a_html(torneo):
    """La clasificacion como una pagina web autocontenida, con graficos."""
    from html import escape

    c = torneo["configuracion"]
    tabla = torneo["clasificacion"]
    partidas = torneo["partidas"]

    # Cifras de cabecera
    mates = sum(p["motivo"] == JAQUE_MATE for p in partidas)
    cifras = [
        (str(len(tabla)), "bots"),
        (str(len(partidas)), "partidas jugadas"),
        ("%d%%" % round(100.0 * mates / len(partidas)) if partidas else "–", "acaban en jaque mate"),
        ("%d min" % round(torneo["duracion_segundos"] / 60.0), "de torneo"),
    ]
    html_cifras = "".join('<div class="cifra"><b>%s</b><span>%s</span></div>' % cifra for cifra in cifras)

    # Podio con los tres primeros
    podio = []
    for f in tabla[:3]:
        podio.append(
            '<div class="puesto p%d"><div class="medalla">%d</div>'
            '<div class="nombre mono">%s</div><div class="elo">%d</div>'
            '<div class="detalle">Elo · %s puntos</div>'
            '<div class="detalle">%d V · %d T · %d D</div></div>' % (
                f["posicion"], f["posicion"], escape(f["bot"]), f["elo"], _formato(f["puntos"]),
                f["victorias"], f["tablas"], f["derrotas"]))

    # Tabla con barras de Elo y de victorias/tablas/derrotas
    elos = [f["elo"] for f in tabla] or [0]
    minimo, maximo = min(elos), max(elos)
    medallas = {1: "var(--oro)", 2: "var(--plata)", 3: "var(--bronce)"}
    filas = []
    for i, f in enumerate(tabla):
        ancho = 100.0 if maximo == minimo else 12 + 88.0 * (f["elo"] - minimo) / (maximo - minimo)
        if f["posicion"] in medallas:
            pos = '<span class="chapa" style="--medalla:%s">%d</span>' % (medallas[f["posicion"]], f["posicion"])
        else:
            pos = str(f["posicion"])
        jugadas = max(f["partidas"], 1)
        retraso = "animation-delay:%.2fs" % (0.05 * i)
        vtd = "".join('<span class="%s" style="width:%.2f%%"></span>' % (clase, 100.0 * n / jugadas)
                      for clase, n in (("v", f["victorias"]), ("t", f["tablas"]), ("d", f["derrotas"])))
        filas.append(
            '<tr><td class="pos">%s</td><td class="izq mono">%s</td>'
            '<td class="izq"><div class="barra-elo"><b>%d</b><div class="pista">'
            '<div class="relleno" style="width:%.1f%%;%s"></div></div></div></td>'
            '<td class="num"><b>%s</b></td><td class="num">%d</td>'
            '<td><div class="vtd" style="%s">%s</div><div class="vtd-num">%d · %d · %d</div></td>'
            '<td class="num%s">%d</td></tr>' % (
                pos, escape(f["bot"]), f["elo"], ancho, retraso, _formato(f["puntos"]),
                f["partidas"], retraso, vtd, f["victorias"], f["tablas"], f["derrotas"],
                " mal" if f["fallos"] else "", f["fallos"]))

    # Mapa de calor con los cruces
    orden = [f["bot"] for f in tabla]
    jugadas_pareja = {}
    for p in partidas:
        pareja = frozenset((p["blancas"], p["negras"]))
        jugadas_pareja[pareja] = jugadas_pareja.get(pareja, 0) + 1
    cabecera = "".join("<th>%s</th>" % escape(b) for b in orden)
    filas_cruces = []
    for a in orden:
        celdas = []
        for b in orden:
            if a == b:
                celdas.append('<td class="propio"></td>')
                continue
            puntos = torneo["cruces"][a][b]
            jugadas = jugadas_pareja.get(frozenset((a, b)), c["partidas_por_pareja"]) or 1
            celdas.append('<td class="celda" style="background:%s" title="%s contra %s: %s de %d">%s</td>' % (
                _color_celda(puntos / jugadas), escape(a), escape(b), _formato(puntos), jugadas,
                _formato(puntos)))
        filas_cruces.append('<tr><th class="fila">%s</th>%s</tr>' % (escape(a), "".join(celdas)))

    resumen = "Generada el %s · %d partidas" % (torneo["generado"], len(partidas))
    valores = {
        "resumen": escape(resumen),
        "cifras": html_cifras,
        "podio": "".join(podio),
        "filas": "\n".join(filas),
        "por_pareja": str(c["partidas_por_pareja"]),
        "max_jugadas": str(c["max_jugadas"]),
        "cabecera_cruces": cabecera,
        "filas_cruces": "\n".join(filas_cruces),
        "final": _seccion_final(partidas),
    }
    pagina = _PLANTILLA_HTML
    for clave, valor in valores.items():
        pagina = pagina.replace("{{%s}}" % clave, valor)
    return pagina


def guardar(torneo, carpeta):
    """Escribe clasificacion.json, .md y .html en 'carpeta'."""
    import json
    from pathlib import Path

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "clasificacion.json").write_text(
        json.dumps(torneo, ensure_ascii=False, indent=1), encoding="utf-8")
    (carpeta / "clasificacion.md").write_text(a_markdown(torneo), encoding="utf-8")
    (carpeta / "clasificacion.html").write_text(a_html(torneo), encoding="utf-8")


# ---------------------------------------------------------
# Linea de comandos
# ---------------------------------------------------------

def main(argumentos=None):
    parser = argparse.ArgumentParser(
        prog="python -m chess.torneo",
        description="Enfrenta a todos los bots del catalogo y crea la clasificacion.",
    )
    parser.add_argument("--bots", help="nombres separados por comas (por defecto, todos)")
    parser.add_argument("--partidas", type=int, default=PARTIDAS_POR_PAREJA,
                        help="partidas por pareja, numero par (por defecto %d)" % PARTIDAS_POR_PAREJA)
    parser.add_argument("--paralelo", type=int, default=1,
                        help="partidas a la vez (por defecto 1)")
    parser.add_argument("--max-jugadas", type=int, default=MAX_JUGADAS,
                        help="medias jugadas maximas por partida (por defecto %d)" % MAX_JUGADAS)
    parser.add_argument("--tiempo", type=float, default=TIEMPO_MAXIMO,
                        help="segundos maximos por jugada (por defecto %g)" % TIEMPO_MAXIMO)
    parser.add_argument("--semilla", type=int, default=0)
    parser.add_argument("--salida", default="clasificacion",
                        help="carpeta donde escribir los resultados (por defecto 'clasificacion')")
    argumentos = parser.parse_args(argumentos)

    elegidos = None
    if argumentos.bots:
        nombres = [n.strip() for n in argumentos.bots.split(",") if n.strip()]
        desconocidos = [n for n in nombres if n not in BOTS]
        if desconocidos:
            parser.error("bots desconocidos: %s (disponibles: %s)" % (
                ", ".join(desconocidos), ", ".join(BOTS)))
        elegidos = {n: BOTS[n] for n in nombres}

    torneo = jugar_torneo(
        elegidos, partidas_por_pareja=argumentos.partidas, semilla=argumentos.semilla,
        tiempo_maximo=argumentos.tiempo, max_jugadas=argumentos.max_jugadas,
        paralelo=argumentos.paralelo, progreso=lambda texto: print(texto, flush=True),
    )
    guardar(torneo, argumentos.salida)
    print()
    print(a_markdown(torneo))
    print("Resultados en la carpeta '%s'." % argumentos.salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
