"""
Paso 3: medir si el bot aprendido juega mejor que otro.

Enfrenta dos bots en varias partidas, cambiando de color en cada pareja y
empezando desde aperturas distintas (unas pocas jugadas al azar, iguales
para los dos bots de la pareja), porque los bots son casi deterministas
y sin esto repetirian siempre la misma partida.

Uso:
    python training/duelo.py ml-2 minimax-2 --parejas 20
    python training/duelo.py ml-3 minimax-3 --parejas 10 --procesos 2

Los nombres son los del catalogo BOTS (chess/bots/__init__.py), o un bot ML
con otros pesos: ml@ruta/pesos.json@0.5 (0.5 s por jugada) o @d4 (profundidad 4).
"""

import argparse
import math
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from chess.bots import BOTS, MLBot  # noqa: E402
from chess.bots.evaluacion_ml import cargar_extras, cargar_pesos  # noqa: E402
from chess.bots.motor_rapido import tablas_de_pesos  # noqa: E402
from chess.game import Game  # noqa: E402


def crear_bot(especificacion):
    """
    Un nombre del catalogo BOTS ("minimax-3") o un bot ML con otros pesos:
        ml@ruta/pesos.json@0.5   -> 0.5 segundos por jugada
        ml@ruta/pesos.json@d4    -> profundidad 4
    """
    if "@" not in especificacion:
        return BOTS[especificacion]()
    _, ruta, limite = especificacion.split("@")
    pesos = (tablas_de_pesos(*cargar_pesos(ruta)), cargar_extras(ruta))
    nombre = Path(ruta).stem
    if limite.startswith("d"):
        return MLBot(profundidad=int(limite[1:]), name=nombre, pesos=pesos)
    return MLBot(tiempo=float(limite), name=nombre, pesos=pesos)

MAX_JUGADAS = 300  # medias jugadas; si se pasa, se da por tablas


def partida(nombre_blancas, nombre_negras, jugadas_apertura, semilla):
    """Juega una partida entre dos bots. Devuelve 1, 0.5 o 0 (puntos de las blancas)."""
    azar = random.Random(semilla)
    game = Game()
    for _ in range(jugadas_apertura):
        game.jugar(azar.choice(game.jugadas_legales()))
        if game.esta_terminada():
            break
    blancas, negras = crear_bot(nombre_blancas), crear_bot(nombre_negras)
    inicio = len(game.historial)
    while not game.esta_terminada() and len(game.historial) - inicio < MAX_JUGADAS:
        bot = blancas if game.turno == "white" else negras
        game.jugar(bot.choose_move(game.copy()))
    if not game.esta_terminada():
        return 0.5
    return {"1-0": 1.0, "0-1": 0.0}.get(game.resultado, 0.5)


def pareja(trabajo):
    """Dos partidas con la misma apertura y los colores cambiados. Devuelve los puntos de A."""
    a, b, aperturas, semilla = trabajo
    como_blancas = partida(a, b, aperturas, semilla)
    como_negras = 1.0 - partida(b, a, aperturas, semilla)
    return como_blancas, como_negras


def elo_estimado(puntos, partidas):
    """Diferencia de Elo que corresponde a ese porcentaje de puntos."""
    p = min(max(puntos / partidas, 0.01), 0.99)
    return -400 * math.log10(1 / p - 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bot_a")
    ap.add_argument("bot_b")
    ap.add_argument("--parejas", type=int, default=10)
    ap.add_argument("--aperturas", type=int, default=4, help="jugadas aleatorias iniciales (medias jugadas)")
    ap.add_argument("--procesos", type=int, default=2)
    ap.add_argument("--semilla", type=int, default=1)
    args = ap.parse_args()

    trabajos = [(args.bot_a, args.bot_b, args.aperturas, args.semilla * 1000 + i)
                for i in range(args.parejas)]
    puntos = victorias = tablas = derrotas = 0
    inicio = time.time()
    with Pool(args.procesos) as pool:
        for i, resultados in enumerate(pool.imap_unordered(pareja, trabajos), start=1):
            for r in resultados:
                puntos += r
                victorias += r == 1.0
                tablas += r == 0.5
                derrotas += r == 0.0
            print(f"  pareja {i}/{args.parejas}: {args.bot_a} {puntos}/{2 * i}", flush=True)

    total = 2 * args.parejas
    print(f"\n{args.bot_a} vs {args.bot_b}: +{victorias} ={tablas} -{derrotas}  "
          f"({puntos}/{total} puntos, {puntos / total:.0%})")
    print(f"diferencia de Elo estimada: {elo_estimado(puntos, total):+.0f}   "
          f"(tiempo: {time.time() - inicio:.0f} s)")


if __name__ == "__main__":
    main()
