"""
Los bots disponibles.

BOTS es el catalogo: asocia el nombre de cada bot con una funcion que
crea el bot. La interfaz web lo usa para ofrecer los rivales, de menor a
mayor nivel.
"""

from chess.bots.base import Bot
from chess.bots.dama_segura import DamaSegura
from chess.bots.greedy_bot import GreedyBot
from chess.bots.ines_bot import InesBot
from chess.bots.minimax_bot import MinimaxBot
from chess.bots.ml_bot import MLBot
from chess.bots.montecarlo_bot import MonteCarloBot
from chess.bots.random_bot import RandomBot


def _minimax(profundidad, tiempo=None):
    nombre = "minimax-" + str(profundidad)
    return lambda: MinimaxBot(profundidad, name=nombre, tiempo=tiempo)


def _ml(profundidad=None, tiempo=None, libro=False):
    nombre = "ml-" + (str(profundidad) if profundidad is not None else "%gs" % tiempo)
    return lambda: MLBot(profundidad=profundidad, tiempo=tiempo, name=nombre, libro=libro)


BOTS = {
    RandomBot.name: RandomBot,
    GreedyBot.name: GreedyBot,
    # Monte Carlo (MCTS): muestrea partidas cortas en vez de mirar todas las jugadas.
    MonteCarloBot.name: MonteCarloBot,
    "minimax-2": _minimax(2),
    "minimax-3": _minimax(3),
    # Enviado por el equipo de Tic-Tac-Toe Arena: minimax sobre el material y
    # la posicion, hasta 2 segundos por jugada (nivel parecido a minimax-3).
    DamaSegura.name: DamaSegura,
    # Evaluacion y libro de aperturas aprendidos de partidas de Lichess +
    # busqueda rapida. "ml-3s" piensa hasta 3 segundos por jugada.
    "ml-2": _ml(profundidad=2),
    "ml-4": _ml(profundidad=4),
    "ml-6": _ml(profundidad=6),
    "ml-3s": _ml(tiempo=3, libro=True),
    InesBot.name: InesBot,
}

__all__ = [
    "BOTS",
    "Bot",
    "DamaSegura",
    "GreedyBot",
    "InesBot",
    "MLBot",
    "MinimaxBot",
    "MonteCarloBot",
    "RandomBot",
]
