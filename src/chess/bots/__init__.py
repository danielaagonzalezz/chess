"""
Los bots disponibles.

BOTS es el catalogo: asocia el nombre de cada bot con una funcion que
crea el bot. La interfaz web lo usa para ofrecer los rivales, de menor a
mayor nivel.
"""

from chess.bots.base import Bot
from chess.bots.greedy_bot import GreedyBot
from chess.bots.minimax_bot import MinimaxBot
from chess.bots.random_bot import RandomBot


def _minimax(profundidad, tiempo=None):
    nombre = "minimax-" + str(profundidad)
    return lambda: MinimaxBot(profundidad, name=nombre, tiempo=tiempo)


BOTS = {
    RandomBot.name: RandomBot,
    GreedyBot.name: GreedyBot,
    "minimax-2": _minimax(2),
    "minimax-3": _minimax(3),
    # Hasta profundidad 4, pero como mucho 5 segundos por jugada.
    "minimax-4": _minimax(4, tiempo=5),
}

__all__ = ["Bot", "RandomBot", "GreedyBot", "MinimaxBot", "BOTS"]
