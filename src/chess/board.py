"""
Tablero de ajedrez: donde esta cada pieza.

Representamos el tablero con una lista de 64 casillas, como una fila
larga de 64 cajitas numeradas de la 0 a la 63 (el mismo numero que usa
Square.to_index en pieces.py). Cada cajita guarda una Piece, o None si
la casilla esta vacia.
"""

from chess.pieces import (
    Piece, Square, square_from_index,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)


class Board:
    """El tablero: 64 casillas, cada una vacia o con una pieza encima."""

    def __init__(self):
        # Empezamos con un tablero completamente vacio: una lista con
        # 64 huecos, todos con valor None, que significa "sin pieza".
        self.squares = []
        for i in range(64):
            self.squares.append(None)

    def get_piece(self, square):
        """Devuelve la Piece que hay en esa casilla, o None si esta vacia."""
        index = square.to_index()
        return self.squares[index]

    def set_piece(self, square, piece):
        """Coloca una pieza en esa casilla (sobrescribe lo que hubiera antes)."""
        index = square.to_index()
        self.squares[index] = piece

    def remove_piece(self, square):
        """Quita la pieza que haya en esa casilla, si es que hay alguna."""
        index = square.to_index()
        self.squares[index] = None

    def is_empty(self, square):
        """True si no hay ninguna pieza en esa casilla."""
        piece = self.get_piece(square)
        return piece is None

    def all_pieces(self):
        """
        Devuelve una lista de parejas (square, piece) con todas las
        piezas que hay actualmente colocadas en el tablero.
        """
        result = []
        for index in range(64):
            piece = self.squares[index]
            if piece is not None:
                square = square_from_index(index)
                result.append((square, piece))
        return result

    def __str__(self):
        """
        Representa el tablero como texto, con la fila 8 arriba (asi se
        ve normalmente un tablero de ajedrez dibujado) y la fila 1 abajo.
        Las casillas vacias se muestran como un punto.
        """
        lineas = []
        for rank in range(7, -1, -1):  # de 7 a 0: de la fila 8 a la fila 1
            simbolos_de_la_fila = []
            for file in range(8):
                square = Square(file, rank)
                piece = self.get_piece(square)
                if piece is None:
                    simbolos_de_la_fila.append(".")
                else:
                    simbolos_de_la_fila.append(piece.symbol())
            numero_de_fila = rank + 1
            lineas.append(str(numero_de_fila) + "  " + " ".join(simbolos_de_la_fila))
        lineas.append("   a b c d e f g h")
        return "\n".join(lineas)


def create_initial_board():
    """Crea un tablero con la posicion inicial estandar de una partida."""
    board = Board()

    # Orden de las piezas "importantes" en la primera/ultima fila,
    # leyendo de la columna a (file=0) a la columna h (file=7).
    orden_fila_trasera = [ROOK, KNIGHT, BISHOP, QUEEN, KING, BISHOP, KNIGHT, ROOK]

    for file in range(8):
        piece_type = orden_fila_trasera[file]

        # Fila 1 (rank=0): piezas blancas importantes
        board.set_piece(Square(file, 0), Piece(piece_type, WHITE))
        # Fila 8 (rank=7): piezas negras importantes
        board.set_piece(Square(file, 7), Piece(piece_type, BLACK))
        # Fila 2 (rank=1): peones blancos
        board.set_piece(Square(file, 1), Piece(PAWN, WHITE))
        # Fila 7 (rank=6): peones negros
        board.set_piece(Square(file, 6), Piece(PAWN, BLACK))

    return board
