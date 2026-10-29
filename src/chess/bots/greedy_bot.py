"""
Bot "1-paso" (codicioso): mira UNA jugada por delante y elige la que mejor deja el tablero.

Para cada jugada legal, la prueba en una copia de la partida y evalua el
tablero que queda (material y posicion de las piezas, ver evaluacion.py).
Se queda con la mejor. Si hay varias igual de buenas, elige una al azar.

Captura siempre que puede, pero no piensa en la respuesta del rival: puede
capturar un peon con la dama y perderla en la jugada siguiente. Es el
primer escalon antes del bot minimax.
"""

import random

from chess.bots.base import Bot
from chess.bots.evaluacion import PUNTOS_MATE, evaluar
from chess.pieces import WHITE


class GreedyBot(Bot):
    """Elige la jugada que deja la mejor evaluacion inmediata."""

    name = "1-paso"

    def __init__(self, seed=None):
        self._azar = random.Random(seed)

    def choose_move(self, game):
        # +1 si juego con blancas (la evaluacion es "desde las blancas"), -1 si negras.
        signo = 1 if game.turno == WHITE else -1

        mejor_valor = None
        mejores = []
        for jugada in game.jugadas_legales():
            hijo = game.copy()
            hijo.jugar(jugada)

            if hijo.esta_terminada():
                if hijo.ganador() is None:
                    valor = 0                 # tablas
                else:
                    valor = PUNTOS_MATE       # he dado jaque mate
            else:
                valor = signo * evaluar(hijo.board)

            if mejor_valor is None or valor > mejor_valor:
                mejor_valor = valor
                mejores = [jugada]
            elif valor == mejor_valor:
                mejores.append(jugada)

        return self._azar.choice(mejores)
