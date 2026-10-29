"""
Bot aleatorio: elige una jugada legal al azar.

Es el bot mas simple posible. Sirve de ejemplo de como se escribe un bot
y como rival de prueba (juega muy mal).
"""

import random

from chess.bots.base import Bot


class RandomBot(Bot):
    """Elige una jugada legal al azar."""

    name = "aleatorio"

    def __init__(self, seed=None):
        # Con una semilla fija el bot juega siempre igual (util en tests).
        self._azar = random.Random(seed)

    def choose_move(self, game):
        return self._azar.choice(game.jugadas_legales())
