"""
Validacion de bots: comprueba que un bot cumple el contrato.

Antes de aceptar un bot nuevo en el repositorio hay que asegurarse de que
no rompe el juego. Este modulo hace esas comprobaciones, para cualquier
bot, sin que el autor tenga que escribir tests:

  - Es un Bot, con un nombre (texto no vacio).
  - En varias posiciones (inicial, jaque, enroque, captura al paso,
    promocion, final...) y jugando con blancas y con negras:
      * no lanza ninguna excepcion,
      * devuelve una Move,
      * la jugada esta en game.jugadas_legales(),
      * tarda menos del limite de tiempo.
  - Juega unas jugadas de una partida real contra RandomBot sin fallar.

Los tests (tests/test_validar_bots.py) lo ejecutan sobre TODOS los bots de
BOTS, asi que un bot nuevo se prueba solo en cuanto se anade al catalogo.

Tambien se puede usar desde la terminal:

    python -m chess.bots.validacion minimax-2          (un bot del catalogo)
    python -m chess.bots.validacion --todos            (todo el catalogo)
    python -m chess.bots.validacion mi_modulo.MiBot    (una clase tuya)
"""

import importlib
import sys
import time

from chess.bots.base import Bot
from chess.bots.random_bot import RandomBot
from chess.game import FEN_INICIAL, Game
from chess.move import Move

# Segundos maximos por jugada. Es un limite generoso: sirve para pillar
# bots que se cuelgan, no para medir su velocidad.
TIEMPO_MAXIMO = 30

# Posiciones de prueba: (descripcion, FEN).
POSICIONES = [
    ("posicion inicial", FEN_INICIAL),
    ("negras mueven tras 1.e4",
     "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"),
    ("jaque con una unica respuesta (Rxe2)",
     "4k3/8/8/8/8/8/4q3/4K3 w - - 0 1"),
    ("enroque disponible",
     "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"),
    ("captura al paso posible",
     "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"),
    ("promocion posible",
     "8/P6k/8/8/8/8/8/K7 w - - 0 1"),
    ("final de rey y dama contra rey",
     "8/8/8/4k3/8/8/8/3QK3 w - - 0 1"),
]


class BotInvalidoError(Exception):
    """El bot no cumple el contrato. El mensaje explica por que."""


def _pedir_jugada(bot, game, descripcion, tiempo_maximo):
    """Pide una jugada al bot y comprueba que es correcta."""
    legales = game.jugadas_legales()
    inicio = time.time()
    try:
        jugada = bot.choose_move(game.copy())
    except Exception as error:  # el bot es codigo ajeno: se captura todo
        raise BotInvalidoError(
            "[%s] choose_move lanzo %s: %s" % (descripcion, type(error).__name__, error)
        )
    segundos = time.time() - inicio

    if not isinstance(jugada, Move):
        raise BotInvalidoError(
            "[%s] choose_move debe devolver una Move, no %r" % (descripcion, jugada)
        )
    if jugada not in legales:
        raise BotInvalidoError(
            "[%s] jugada ilegal: %s (legales: %s)"
            % (descripcion, jugada, ", ".join(sorted(str(j) for j in legales)))
        )
    if segundos > tiempo_maximo:
        raise BotInvalidoError(
            "[%s] tardo %.1f s (maximo %s s)" % (descripcion, segundos, tiempo_maximo)
        )
    return jugada


def validar_bot(bot, posiciones=POSICIONES, jugadas_de_partida=3,
                tiempo_maximo=TIEMPO_MAXIMO):
    """
    Comprueba que 'bot' cumple el contrato. Lanza BotInvalidoError si no.

    - posiciones: lista de (descripcion, fen) en las que probar el bot.
    - jugadas_de_partida: cuantas jugadas propias hace en una partida
      contra RandomBot, con blancas y con negras (0 para saltarse esto).
    - tiempo_maximo: segundos maximos por jugada.

    Devuelve el bot, para poder encadenar llamadas.
    """
    if not isinstance(bot, Bot):
        raise BotInvalidoError("el bot debe heredar de chess.bots.Bot")
    if not isinstance(bot.name, str) or not bot.name.strip():
        raise BotInvalidoError("el bot necesita un 'name' (texto no vacio)")

    for descripcion, fen in posiciones:
        game = Game.desde_fen(fen)
        _pedir_jugada(bot, game, descripcion, tiempo_maximo)

    for color_del_bot in ("white", "black"):
        game = Game()
        rival = RandomBot(seed=1)
        propias = 0
        while not game.esta_terminada() and propias < jugadas_de_partida:
            if game.turno == color_del_bot:
                descripcion = "partida con %s, jugada %d" % (color_del_bot, propias + 1)
                game.jugar(_pedir_jugada(bot, game, descripcion, tiempo_maximo))
                propias += 1
            else:
                game.jugar(rival.choose_move(game.copy()))
    return bot


# ---------------------------------------------------------
# Linea de comandos
# ---------------------------------------------------------

def _crear_bot(nombre):
    """Crea un bot a partir de su nombre en BOTS o de 'modulo.Clase'."""
    from chess.bots import BOTS

    if nombre in BOTS:
        return BOTS[nombre]()
    if "." in nombre:
        modulo, _, clase = nombre.rpartition(".")
        return getattr(importlib.import_module(modulo), clase)()
    raise SystemExit(
        "No conozco el bot '%s'. Usa un nombre de BOTS (%s) o 'modulo.Clase'."
        % (nombre, ", ".join(BOTS))
    )


def main(argumentos=None):
    from chess.bots import BOTS

    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if not argumentos:
        print(__doc__)
        return 2
    nombres = list(BOTS) if argumentos == ["--todos"] else argumentos

    fallos = 0
    for nombre in nombres:
        try:
            validar_bot(_crear_bot(nombre))
            print("OK     " + nombre)
        except BotInvalidoError as error:
            fallos += 1
            print("FALLA  %s: %s" % (nombre, error))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
