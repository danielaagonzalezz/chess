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
    RESULTADO_BLANCAS, RESULTADO_NEGRAS, RESULTADO_TABLAS, Game,
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
<style>
:root { --fondo:#f3efe6; --superficie:#fffdf8; --texto:#25231f; --suave:#6d675b;
        --borde:#ddd5c4; --acento:#2f6f5b; --mal:#b42318; }
@media (prefers-color-scheme: dark) {
  :root { --fondo:#17181a; --superficie:#212326; --texto:#eceae4; --suave:#a29d90;
          --borde:#34363a; --acento:#5fb596; --mal:#f97066; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--fondo); color:var(--texto);
       font:16px/1.5 system-ui, "Segoe UI", sans-serif; }
main { max-width:960px; margin:0 auto; padding:24px 16px 48px; }
h1 { margin:0 0 4px; font-size:1.6rem; }
h2 { margin:32px 0 8px; font-size:1.15rem; }
p, .nota { color:var(--suave); margin:4px 0 16px; }
a { color:var(--acento); }
.tabla { overflow-x:auto; background:var(--superficie); border:1px solid var(--borde);
         border-radius:10px; }
table { border-collapse:collapse; width:100%%; min-width:560px; }
th, td { padding:8px 12px; text-align:right; border-bottom:1px solid var(--borde); }
th:nth-child(2), td:nth-child(2), th:first-child, td:first-child { text-align:left; }
tr:last-child td { border-bottom:0; }
thead th { font-size:.8rem; text-transform:uppercase; letter-spacing:.04em; color:var(--suave); }
td.bot { font-family:ui-monospace, Consolas, monospace; }
td.elo { font-weight:700; }
td.mal { color:var(--mal); font-weight:600; }
td.propio { color:var(--suave); }
</style>
</head>
<body>
<main>
<h1>♞ Clasificación de bots</h1>
<p>%(resumen)s</p>
<p><a href="./">Juega contra ellos</a></p>
<div class="tabla"><table>
<thead><tr><th>#</th><th>Bot</th><th>Elo</th><th>Puntos</th><th>Partidas</th>
<th>V</th><th>T</th><th>D</th><th>Fallos</th></tr></thead>
<tbody>
%(filas)s
</tbody></table></div>
<p class="nota">Victoria 1, tablas ½, derrota 0. Cada pareja juega %(por_pareja)d partidas con
colores alternados y aperturas al azar (iguales para los dos bots de la pareja). Si una partida
pasa de %(max_jugadas)d medias jugadas se da por tablas. Un bot que falla, se cuelga o hace una
jugada ilegal pierde la partida, pero no rompe el torneo. El Elo es aproximado (media 1000).</p>
<h2>Puntos de cada bot contra cada rival</h2>
<div class="tabla"><table>
<thead><tr><th></th>%(cabecera_cruces)s</tr></thead>
<tbody>
%(filas_cruces)s
</tbody></table></div>
<p class="nota">Datos completos, con todas las partidas: <a href="clasificacion.json">clasificacion.json</a>.</p>
</main>
</body>
</html>
"""


def a_html(torneo):
    """La clasificacion como una pagina web autocontenida."""
    from html import escape

    c = torneo["configuracion"]
    filas = []
    for f in torneo["clasificacion"]:
        clase_fallos = ' class="mal"' if f["fallos"] else ""
        filas.append(
            '<tr><td>%d</td><td class="bot">%s</td><td class="elo">%d</td><td>%s</td>'
            "<td>%d</td><td>%d</td><td>%d</td><td>%d</td><td%s>%d</td></tr>" % (
                f["posicion"], escape(f["bot"]), f["elo"], _formato(f["puntos"]),
                f["partidas"], f["victorias"], f["tablas"], f["derrotas"],
                clase_fallos, f["fallos"]))
    orden = [f["bot"] for f in torneo["clasificacion"]]
    cabecera = "".join('<th class="bot">%s</th>' % escape(b) for b in orden)
    filas_cruces = []
    for a in orden:
        celdas = []
        for b in orden:
            if a == b:
                celdas.append('<td class="propio">·</td>')
            else:
                celdas.append("<td>%s</td>" % _formato(torneo["cruces"][a][b]))
        filas_cruces.append('<tr><td class="bot">%s</td>%s</tr>' % (escape(a), "".join(celdas)))
    resumen = "Generada el %s: %d partidas en %d s." % (
        torneo["generado"], len(torneo["partidas"]), torneo["duracion_segundos"])
    return _PLANTILLA_HTML % {
        "resumen": escape(resumen),
        "filas": "\n".join(filas),
        "por_pareja": c["partidas_por_pareja"],
        "max_jugadas": c["max_jugadas"],
        "cabecera_cruces": cabecera,
        "filas_cruces": "\n".join(filas_cruces),
    }


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
