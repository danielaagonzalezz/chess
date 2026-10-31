"""
Libro de aperturas aprendido de partidas reales.

Cuenta, en las primeras jugadas de las partidas de Lichess, que jugada se
hace en cada posicion, y se queda con las posiciones muy repetidas y con
las jugadas mas populares. El bot (libro.py) lo usa en las primeras
jugadas: elige una al azar, con mas probabilidad cuanto mas frecuente. Asi
no juega siempre la misma apertura, y las conoce sin tener que calcularlas.

Igual que preparar_datos.py, necesita la libreria python-chess (que choca
de nombre con este proyecto): usa el mismo entorno virtual aparte.

Uso:
    .venv-datos/bin/python training/crear_libro.py data/lichess_2013-09.pgn.zst \\
        --salida src/chess/bots/libro_aperturas.json
"""

import argparse
import io
import json
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

try:
    import chess
    import chess.pgn
except ImportError:  # pragma: no cover
    sys.exit("Falta python-chess en un entorno aparte: mira el mensaje de preparar_datos.py")

from preparar_datos import partidas_filtradas


def clave(tablero):
    """Colocacion + turno + enroques (lo que identifica una posicion en el libro)."""
    return "%s %s %s" % (tablero.board_fen(), "w" if tablero.turn else "b", tablero.castling_xfen())


def jugadas_de_apertura(args):
    texto, plies = args
    juego = chess.pgn.read_game(io.StringIO(texto))
    if juego is None:
        return []
    tablero = juego.board()
    resultado = []
    for i, jugada in enumerate(juego.mainline_moves()):
        if i >= plies:
            break
        resultado.append((clave(tablero), jugada.uci()))
        tablero.push(jugada)
    return resultado


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada")
    ap.add_argument("--salida", default="src/chess/bots/libro_aperturas.json")
    ap.add_argument("--elo-minimo", type=int, default=1600)
    ap.add_argument("--plies", type=int, default=16, help="medias jugadas que cubre el libro")
    ap.add_argument("--min-posicion", type=int, default=40, help="veces minimas que debe aparecer una posicion")
    ap.add_argument("--min-jugada", type=int, default=10, help="veces minimas que debe jugarse una jugada")
    ap.add_argument("--min-cuota", type=float, default=0.08, help="cuota minima de una jugada en su posicion")
    ap.add_argument("--procesos", type=int, default=2)
    args = ap.parse_args()

    cuentas = defaultdict(Counter)
    trabajos = ((t, args.plies) for t in partidas_filtradas(args.entrada, args.elo_minimo, 0))
    partidas = 0
    with Pool(args.procesos) as pool:
        for filas in pool.imap(jugadas_de_apertura, trabajos, chunksize=64):
            partidas += 1
            for k, uci in filas:
                cuentas[k][uci] += 1

    libro = {}
    for k, jugadas in cuentas.items():
        total = sum(jugadas.values())
        if total < args.min_posicion:
            continue
        buenas = [[uci, n] for uci, n in jugadas.most_common()
                  if n >= args.min_jugada and n / total >= args.min_cuota]
        if buenas:
            libro[k] = buenas
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(libro, f, separators=(",", ":"), sort_keys=True)
    print(f"{partidas} partidas -> {len(libro)} posiciones en el libro ({args.salida})")


if __name__ == "__main__":
    main()
