"""
Movimientos de la dama.

La dama es la pieza mas poderosa: se mueve como una torre (recto) y
como un alfil (en diagonal) a la vez. Por eso no hace falta repetir
codigo: sus movimientos son simplemente los de una torre mas los de un
alfil colocados en la misma casilla.
"""

from chess.movimientos_torre import obtener_movimientos_torre
from chess.movimientos_alfil import obtener_movimientos_alfil


def obtener_movimientos_dama(board, square, color):
    """
    Devuelve la lista de casillas a las que se puede mover una dama
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.
    """
    destinos_posibles = []
    destinos_posibles.extend(obtener_movimientos_torre(board, square, color))
    destinos_posibles.extend(obtener_movimientos_alfil(board, square, color))
    return destinos_posibles