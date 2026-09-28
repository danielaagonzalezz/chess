"""
Estructuras de datos básicas: colores, tipos de pieza, piezas y casillas.

Este módulo no contiene lógica de movimientos ni de reglas: solo las
representaciones fundamentales sobre las que se construirán `board.py`,
`rules.py` y `game.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from chess.exceptions import InvalidSquareError


class Color(Enum):
    """Color de un jugador o de una pieza."""

    WHITE = "white"
    BLACK = "black"

    def opposite(self) -> "Color":
        """Devuelve el color contrario."""
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    def __str__(self) -> str:
        return self.value


class PieceType(Enum):
    """Tipo de pieza, usando la letra estándar de la notación algebraica en inglés."""

    PAWN = "P"
    KNIGHT = "N"
    BISHOP = "B"
    ROOK = "R"
    QUEEN = "Q"
    KING = "K"


# Valor material estándar de cada pieza (el rey no se valora: no aplica / infinito).
_MATERIAL_VALUE = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 0,
}

# Símbolos unicode para representar el tablero visualmente (útil en __str__ / debug).
_UNICODE_SYMBOLS = {
    (PieceType.PAWN, Color.WHITE): "♙",
    (PieceType.KNIGHT, Color.WHITE): "♘",
    (PieceType.BISHOP, Color.WHITE): "♗",
    (PieceType.ROOK, Color.WHITE): "♖",
    (PieceType.QUEEN, Color.WHITE): "♕",
    (PieceType.KING, Color.WHITE): "♔",
    (PieceType.PAWN, Color.BLACK): "♟",
    (PieceType.KNIGHT, Color.BLACK): "♞",
    (PieceType.BISHOP, Color.BLACK): "♝",
    (PieceType.ROOK, Color.BLACK): "♜",
    (PieceType.QUEEN, Color.BLACK): "♛",
    (PieceType.KING, Color.BLACK): "♚",
}


@dataclass(frozen=True)
class Piece:
    """Una pieza concreta: su tipo y su color. Inmutable."""

    piece_type: PieceType
    color: Color

    @property
    def value(self) -> int:
        """Valor material estándar (peón=1 ... reina=9, rey=0)."""
        return _MATERIAL_VALUE[self.piece_type]

    def symbol(self) -> str:
        """Letra FEN: mayúscula si es blanca, minúscula si es negra (ej. 'N', 'n')."""
        letter = self.piece_type.value
        return letter if self.color is Color.WHITE else letter.lower()

    def unicode(self) -> str:
        """Símbolo unicode de la pieza, para mostrarla en un tablero de texto."""
        return _UNICODE_SYMBOLS[(self.piece_type, self.color)]

    def __str__(self) -> str:
        return self.symbol()


_FILES = "abcdefgh"


@dataclass(frozen=True)
class Square:
    """
    Una casilla del tablero, en coordenadas internas 0-indexadas.

    file: columna, 0=a ... 7=h
    rank: fila,   0=rango 1 ... 7=rango 8
    """

    file: int
    rank: int

    def __post_init__(self) -> None:
        if not (0 <= self.file <= 7 and 0 <= self.rank <= 7):
            raise InvalidSquareError(
                f"Casilla fuera del tablero: file={self.file}, rank={self.rank}"
            )

    @classmethod
    def from_algebraic(cls, notation: str) -> "Square":
        """Crea una Square a partir de notación algebraica, ej. 'e4'."""
        if len(notation) != 2:
            raise InvalidSquareError(f"Notación de casilla inválida: '{notation}'")

        file_char, rank_char = notation[0].lower(), notation[1]
        if file_char not in _FILES or rank_char not in "12345678":
            raise InvalidSquareError(f"Notación de casilla inválida: '{notation}'")

        return cls(file=_FILES.index(file_char), rank=int(rank_char) - 1)

    def to_algebraic(self) -> str:
        """Devuelve la notación algebraica, ej. 'e4'."""
        return f"{_FILES[self.file]}{self.rank + 1}"

    def to_index(self) -> int:
        """Índice único 0-63 (rank * 8 + file), útil para representar el tablero como lista plana."""
        return self.rank * 8 + self.file

    @classmethod
    def from_index(cls, index: int) -> "Square":
        """Crea una Square a partir de un índice 0-63."""
        if not (0 <= index <= 63):
            raise InvalidSquareError(f"Índice de casilla inválido: {index}")
        return cls(file=index % 8, rank=index // 8)

    def offset(self, delta_file: int, delta_rank: int) -> Optional["Square"]:
        """
        Devuelve la casilla desplazada (delta_file, delta_rank) columnas/filas,
        o None si el resultado cae fuera del tablero (en vez de lanzar excepción).

        Pensado para la futura generación de movimientos: "intenta ir aquí, y si
        no se puede, lo descarto sin más" en vez de tener que capturar excepciones
        en cada llamada.
        """
        new_file = self.file + delta_file
        new_rank = self.rank + delta_rank
        if 0 <= new_file <= 7 and 0 <= new_rank <= 7:
            return Square(file=new_file, rank=new_rank)
        return None

    def __str__(self) -> str:
        return self.to_algebraic()
