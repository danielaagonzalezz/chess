"""
Paso 1 del aprendizaje: convertir partidas de Lichess en posiciones etiquetadas.

Lee un archivo .pgn (o .pgn.zst) de https://database.lichess.org y guarda
un fichero .npz con:

  - tableros: matriz (N, 64) con el codigo de la pieza de cada casilla
              (0 = vacia, 1..6 = P N B R Q K blancas, 7..12 = negras).
              El orden de casillas es el del proyecto: a1=0, b1=1 ... h8=63.
  - resultado: 1.0 si ganaron blancas, 0.5 tablas, 0.0 si ganaron negras
               (el resultado FINAL de la partida de la que sale la posicion).
  - turno: 1 si mueven blancas, 0 si mueven negras.

Filtros (para que la etiqueta "quien gano" diga algo de la posicion):
  - los dos jugadores con al menos --elo-minimo de Elo,
  - partidas terminadas de forma normal (no por "tiempo agotado": alli el
    resultado no depende de la posicion),
  - se saltan las primeras jugadas (teoria de aperturas) y solo se guardan
    posiciones "tranquilas": sin jaque y sin que la ultima jugada fuera
    una captura o una promocion (en medio de un cambio de piezas el
    material engana).

IMPORTANTE: necesita la libreria python-chess, que se importa tambien como
'chess' y choca con este proyecto: usa un entorno virtual aparte donde NO
este instalado el proyecto (mira el mensaje de error si falla).

Uso:
    python training/preparar_datos.py data/lichess_2013-09.pgn.zst \
        --salida data/posiciones.npz --elo-minimo 1600
"""

import argparse
import io
import random
import sys
from multiprocessing import Pool

import numpy as np

try:
    import chess
    import chess.pgn
except ImportError:  # pragma: no cover
    sys.exit(
        "No se puede importar 'chess.pgn' (la libreria python-chess).\n"
        "OJO: python-chess y este proyecto se importan los dos como 'chess' y no\n"
        "pueden convivir en el mismo entorno. Ejecuta este script en un entorno\n"
        "virtual APARTE, sin instalar el proyecto:\n"
        "    python -m venv .venv-datos\n"
        "    .venv-datos/bin/python -m pip install -r training/requirements-datos.txt   (Windows: .venv-datos\\Scripts\\python)\n"
        "    .venv-datos/bin/python training/preparar_datos.py <archivo.pgn.zst> ..."
    )

CODIGOS = {
    chess.PAWN: 1, chess.KNIGHT: 2, chess.BISHOP: 3,
    chess.ROOK: 4, chess.QUEEN: 5, chess.KING: 6,
}
RESULTADOS = {"1-0": 1.0, "1/2-1/2": 0.5, "0-1": 0.0}


def abrir(ruta):
    """Abre un .pgn normal o un .pgn.zst como flujo de texto."""
    if ruta.endswith(".zst"):
        import zstandard
        flujo = zstandard.ZstdDecompressor().stream_reader(open(ruta, "rb"))
        return io.TextIOWrapper(flujo, encoding="utf-8", errors="replace")
    return open(ruta, encoding="utf-8", errors="replace")


def _elo(linea):
    try:
        return int(linea.split('"')[1])
    except (ValueError, IndexError):
        return 0


def partidas_filtradas(ruta, elo_minimo, maximo):
    """
    Genera el texto de cada partida que pasa el filtro de cabeceras.
    Se filtra mirando solo el texto (rapido) antes de interpretar la partida.
    """
    entregadas = 0
    cabecera = []
    elo_b = elo_n = 0
    termination = ""
    en_jugadas = False
    for linea in abrir(ruta):
        if linea.startswith("[Event "):
            cabecera = []
            elo_b = elo_n = 0
            termination = ""
            en_jugadas = False
        if linea.startswith("["):
            if linea.startswith("[WhiteElo "):
                elo_b = _elo(linea)
            elif linea.startswith("[BlackElo "):
                elo_n = _elo(linea)
            elif linea.startswith("[Termination "):
                termination = linea.split('"')[1]
            cabecera.append(linea)
        elif linea.strip() and not en_jugadas:
            # Primera linea de jugadas: aqui ya conocemos todas las cabeceras.
            en_jugadas = True
            if min(elo_b, elo_n) >= elo_minimo and termination == "Normal":
                yield "".join(cabecera) + "\n" + linea
                entregadas += 1
                if maximo and entregadas >= maximo:
                    return


def posiciones_de_partida(args):
    """Interpreta una partida y devuelve sus posiciones tranquilas muestreadas."""
    texto, por_partida, semilla = args
    juego = chess.pgn.read_game(io.StringIO(texto))
    if juego is None:
        return []
    resultado = RESULTADOS.get(juego.headers.get("Result"))
    if resultado is None:
        return []

    azar = random.Random(semilla)
    candidatas = []
    tablero = juego.board()
    for ply, jugada in enumerate(juego.mainline_moves(), start=1):
        era_captura = tablero.is_capture(jugada) or jugada.promotion is not None
        tablero.push(jugada)
        if ply < 8 or era_captura or tablero.is_check() or tablero.is_game_over():
            continue
        candidatas.append(_a_fila(tablero))
    if not candidatas:
        return []
    elegidas = azar.sample(candidatas, min(por_partida, len(candidatas)))
    return [(t, resultado, turno) for (t, turno) in elegidas]


def _a_fila(tablero):
    fila = np.zeros(64, dtype=np.int8)
    for casilla, pieza in tablero.piece_map().items():
        codigo = CODIGOS[pieza.piece_type]
        fila[casilla] = codigo if pieza.color == chess.WHITE else codigo + 6
    return fila, 1 if tablero.turn == chess.WHITE else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", help="archivo .pgn o .pgn.zst")
    ap.add_argument("--salida", default="data/posiciones.npz")
    ap.add_argument("--elo-minimo", type=int, default=1600)
    ap.add_argument("--por-partida", type=int, default=8, help="posiciones por partida")
    ap.add_argument("--max-partidas", type=int, default=0, help="0 = todas")
    ap.add_argument("--procesos", type=int, default=2)
    ap.add_argument("--semilla", type=int, default=0)
    args = ap.parse_args()

    trabajos = (
        (texto, args.por_partida, args.semilla * 1000003 + i)
        for i, texto in enumerate(partidas_filtradas(args.entrada, args.elo_minimo, args.max_partidas))
    )
    tableros, resultados, turnos = [], [], []
    partidas = 0
    with Pool(args.procesos) as pool:
        for filas in pool.imap(posiciones_de_partida, trabajos, chunksize=64):
            partidas += 1
            for t, r, turno in filas:
                tableros.append(t)
                resultados.append(r)
                turnos.append(turno)
            if partidas % 5000 == 0:
                print(partidas, "partidas,", len(tableros), "posiciones", flush=True)

    np.savez_compressed(
        args.salida,
        tableros=np.array(tableros, dtype=np.int8),
        resultado=np.array(resultados, dtype=np.float32),
        turno=np.array(turnos, dtype=np.int8),
    )
    print("Listo:", partidas, "partidas,", len(tableros), "posiciones ->", args.salida)


if __name__ == "__main__":
    main()
