"""
Jugadas: la clase Move y como aplicar una jugada al tablero.

Una jugada (Move) dice "mueve la pieza de esta casilla a esta otra".
Si es un peon que llega al final del tablero, tambien dice en que pieza
se convierte (promocion).

Las funciones de movimientos (movimientos_torre.py, etc.) solo
CALCULAN a donde puede ir una pieza. Este archivo es el que MUEVE de
verdad la pieza en el tablero, con sus casos especiales: capturas,
captura al paso y promocion.
"""

from chess.exceptions import InvalidMoveError
from chess.movimientos import obtener_movimientos
from chess.pieces import (
    Piece, Square, PIECE_LETTERS,
    WHITE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN,
)

# Piezas en las que puede convertirse un peon al promocionar.
PIEZAS_DE_PROMOCION = [QUEEN, ROOK, BISHOP, KNIGHT]


class Move:
    """
    Una jugada: de la casilla 'origen' a la casilla 'destino'.

    'promocion' solo se usa cuando un peon llega a la ultima fila: es el
    tipo de pieza en el que se convierte (QUEEN, ROOK, BISHOP o KNIGHT).
    En cualquier otra jugada es None.
    """

    def __init__(self, origen, destino, promocion=None):
        if promocion is not None and promocion not in PIEZAS_DE_PROMOCION:
            raise InvalidMoveError("Promocion invalida: '" + str(promocion) + "'")
        self.origen = origen
        self.destino = destino
        self.promocion = promocion

    def __str__(self):
        # Por ejemplo "e2e4", o "e7e8q" si es una promocion a dama.
        texto = str(self.origen) + str(self.destino)
        if self.promocion is not None:
            texto = texto + PIECE_LETTERS[self.promocion].lower()
        return texto

    def __repr__(self):
        return "Move('" + str(self) + "')"

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return (
            self.origen == other.origen
            and self.destino == other.destino
            and self.promocion == other.promocion
        )

    def __hash__(self):
        return hash((self.origen, self.destino, self.promocion))


def _fila_de_promocion(color):
    """Fila (rank 0-7) a la que tiene que llegar un peon de ese color."""
    if color == WHITE:
        return 7  # fila 8
    return 0      # fila 1


def calcular_casilla_al_paso(board, move):
    """
    Dice si, despues de esta jugada, el rival podra capturar al paso.

    Hay que llamarla ANTES de aplicar la jugada. Si la jugada es un peon
    que avanza dos casillas, devuelve la casilla "por la que ha pasado"
    (por ejemplo d6 si un peon negro va de d7 a d5). Si no, devuelve None.

    Esa casilla es la que se le pasa a obtener_movimientos y a
    aplicar_jugada en el turno siguiente.
    """
    pieza = board.get_piece(move.origen)

    if pieza is None or pieza.piece_type != PAWN:
        return None

    if abs(move.destino.rank - move.origen.rank) != 2:
        return None

    fila_intermedia = (move.destino.rank + move.origen.rank) // 2
    return Square(move.origen.file, fila_intermedia)


def aplicar_jugada(board, move, casilla_al_paso=None):
    """
    Mueve una pieza en el tablero segun la jugada 'move'.

    Devuelve la pieza capturada (o None si no se ha capturado nada).
    Lanza InvalidMoveError si la jugada no es posible: no hay pieza en
    el origen, la pieza no puede ir al destino, falta la promocion, o se
    indica una promocion donde no corresponde.

    'casilla_al_paso' es la casilla de captura al paso del turno actual
    (ver calcular_casilla_al_paso), o None.

    OJO: de momento solo comprueba las reglas de movimiento de cada
    pieza. Que la jugada deje al rey en jaque, de quien es el turno y el
    enroque se anadiran mas adelante.
    """
    pieza = board.get_piece(move.origen)

    if pieza is None:
        raise InvalidMoveError("No hay ninguna pieza en " + str(move.origen))

    destinos_posibles = obtener_movimientos(board, move.origen, casilla_al_paso)
    if move.destino not in destinos_posibles:
        raise InvalidMoveError(
            "Jugada ilegal: " + str(pieza) + " no puede ir de "
            + str(move.origen) + " a " + str(move.destino)
        )

    # ---- Promocion ----
    llega_al_final = (
        pieza.piece_type == PAWN
        and move.destino.rank == _fila_de_promocion(pieza.color)
    )
    if llega_al_final and move.promocion is None:
        raise InvalidMoveError(
            "El peon llega al final del tablero: hay que elegir la promocion"
        )
    if move.promocion is not None and not llega_al_final:
        raise InvalidMoveError(
            "Solo un peon que llega al final del tablero puede promocionar"
        )

    # ---- Captura (normal o al paso) ----
    pieza_capturada = board.get_piece(move.destino)

    es_captura_al_paso = (
        pieza.piece_type == PAWN
        and pieza_capturada is None
        and move.destino.file != move.origen.file
    )
    if es_captura_al_paso:
        # El peon capturado no esta en la casilla de destino, sino justo
        # al lado del peon que captura (en su misma fila).
        casilla_peon_capturado = Square(move.destino.file, move.origen.rank)
        pieza_capturada = board.get_piece(casilla_peon_capturado)
        board.remove_piece(casilla_peon_capturado)

    # ---- Mover la pieza ----
    board.remove_piece(move.origen)
    if move.promocion is not None:
        board.set_piece(move.destino, Piece(move.promocion, pieza.color))
    else:
        board.set_piece(move.destino, pieza)

    return pieza_capturada


def jugada_desde_texto(texto):
    """
    Crea una Move a partir de un texto como "e2e4" o "e7e8q" (promocion).

    Lanza InvalidSquareError si las casillas no existen y InvalidMoveError
    si el texto no tiene el formato correcto.
    """
    from chess.pieces import square_from_algebraic

    texto = texto.strip().lower()
    if len(texto) not in (4, 5):
        raise InvalidMoveError("Formato de jugada invalido: '" + texto + "'")

    origen = square_from_algebraic(texto[0:2])
    destino = square_from_algebraic(texto[2:4])

    promocion = None
    if len(texto) == 5:
        letras = {"q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT}
        if texto[4] not in letras:
            raise InvalidMoveError("Promocion invalida: '" + texto[4] + "'")
        promocion = letras[texto[4]]

    return Move(origen, destino, promocion)
