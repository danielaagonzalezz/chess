"""
Movimientos de cualquier pieza.

Cada pieza tiene su propio archivo con su funcion de movimientos
(caballo.py, movimientos_torre.py...). Este archivo las junta: le dices
una casilla y el se fija en que pieza hay ahi y llama a la funcion
correcta.

Estos movimientos son "pseudo-legales": siguen las reglas de movimiento
de cada pieza, pero todavia no comprueban si dejan al propio rey en
jaque (eso se anadira mas adelante).
"""

from chess.pieces import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from chess.caballo import obtener_movimientos_caballo
from chess.movimientos_alfil import obtener_movimientos_alfil
from chess.movimientos_torre import obtener_movimientos_torre
from chess.movimientos_dama import obtener_movimientos_dama
from chess.movimientos_rey import obtener_movimientos_rey
from chess.movimientos_peon import obtener_movimientos_peon


def obtener_movimientos(board, square, casilla_al_paso=None):
    """
    Devuelve la lista de casillas a las que se puede mover la pieza que
    hay en 'square'. Si la casilla esta vacia, devuelve una lista vacia.

    'casilla_al_paso' solo afecta a los peones (captura al paso).
    """
    pieza = board.get_piece(square)

    if pieza is None:
        return []

    tipo = pieza.piece_type
    color = pieza.color

    if tipo == PAWN:
        return obtener_movimientos_peon(board, square, color, casilla_al_paso)
    if tipo == KNIGHT:
        return obtener_movimientos_caballo(board, square, color)
    if tipo == BISHOP:
        return obtener_movimientos_alfil(board, square, color)
    if tipo == ROOK:
        return obtener_movimientos_torre(board, square, color)
    if tipo == QUEEN:
        return obtener_movimientos_dama(board, square, color)
    if tipo == KING:
        return obtener_movimientos_rey(board, square, color)

    return []