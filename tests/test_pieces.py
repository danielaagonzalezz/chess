import pytest

from chess.exceptions import InvalidSquareError
from chess.pieces import (
    WHITE, BLACK, opposite_color,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    Piece, Square, square_from_algebraic, square_from_index,
)


# =========================================================
# COLOR
# =========================================================

def test_opposite_color():
    assert opposite_color(WHITE) == BLACK
    assert opposite_color(BLACK) == WHITE


# =========================================================
# PIECE
# =========================================================

def test_piece_material_value():
    # En vez de un decorador, simplemente probamos cada pieza, una por una.
    assert Piece(PAWN, WHITE).value() == 1
    assert Piece(KNIGHT, WHITE).value() == 3
    assert Piece(BISHOP, WHITE).value() == 3
    assert Piece(ROOK, WHITE).value() == 5
    assert Piece(QUEEN, WHITE).value() == 9
    assert Piece(KING, WHITE).value() == 0


def test_piece_symbol_uppercase_for_white():
    piece = Piece(KNIGHT, WHITE)
    assert piece.symbol() == "N"


def test_piece_symbol_lowercase_for_black():
    piece = Piece(KNIGHT, BLACK)
    assert piece.symbol() == "n"


def test_piece_str_matches_symbol():
    piece = Piece(QUEEN, BLACK)
    assert str(piece) == "q"
    assert piece.symbol() == "q"


def test_piece_unicode_differs_by_color():
    white_king = Piece(KING, WHITE)
    black_king = Piece(KING, BLACK)
    assert white_king.unicode() != black_king.unicode()


def test_piece_equality():
    assert Piece(ROOK, WHITE) == Piece(ROOK, WHITE)
    assert Piece(ROOK, WHITE) != Piece(ROOK, BLACK)


# =========================================================
# SQUARE: creación y validación
# =========================================================

def test_square_valid_bounds():
    corner = Square(0, 0)
    assert corner.file == 0
    assert corner.rank == 0


def test_square_out_of_bounds_raises():
    # Probamos varias casillas invalidas, una por una, cada una en su
    # propio "with pytest.raises". Si alguna NO lanzara el error, el
    # test fallaria justo en esa linea.
    with pytest.raises(InvalidSquareError):
        Square(-1, 0)

    with pytest.raises(InvalidSquareError):
        Square(8, 0)

    with pytest.raises(InvalidSquareError):
        Square(0, -1)

    with pytest.raises(InvalidSquareError):
        Square(0, 8)

    with pytest.raises(InvalidSquareError):
        Square(8, 8)


# =========================================================
# SQUARE: notación algebraica ("e4")
# =========================================================

def test_square_from_algebraic():
    assert square_from_algebraic("a1").file == 0
    assert square_from_algebraic("a1").rank == 0

    assert square_from_algebraic("h1").file == 7
    assert square_from_algebraic("h1").rank == 0

    assert square_from_algebraic("a8").file == 0
    assert square_from_algebraic("a8").rank == 7

    assert square_from_algebraic("h8").file == 7
    assert square_from_algebraic("h8").rank == 7

    assert square_from_algebraic("e4").file == 4
    assert square_from_algebraic("e4").rank == 3


def test_square_to_algebraic_roundtrip():
    # "roundtrip" quiere decir: convertir de ida y de vuelta, y
    # comprobar que llegamos al mismo sitio donde empezamos.
    notaciones = ["a1", "h1", "a8", "h8", "e4", "d5"]
    for notacion in notaciones:
        square = square_from_algebraic(notacion)
        assert square.to_algebraic() == notacion


def test_square_from_algebraic_invalid():
    textos_invalidos = ["", "e", "e44", "i4", "e9", "E4x"]
    for texto in textos_invalidos:
        with pytest.raises(InvalidSquareError):
            square_from_algebraic(texto)


def test_square_from_algebraic_case_insensitive():
    # "case insensitive" = no importa si usas mayuscula o minuscula.
    assert square_from_algebraic("E4") == square_from_algebraic("e4")


# =========================================================
# SQUARE: índice plano 0-63
# =========================================================

def test_square_to_index():
    assert square_from_algebraic("a1").to_index() == 0
    assert square_from_algebraic("h1").to_index() == 7
    assert square_from_algebraic("a8").to_index() == 56
    assert square_from_algebraic("h8").to_index() == 63


def test_square_from_index_roundtrip():
    for index in range(64):
        square = square_from_index(index)
        assert square.to_index() == index


def test_square_from_index_invalid():
    with pytest.raises(InvalidSquareError):
        square_from_index(-1)

    with pytest.raises(InvalidSquareError):
        square_from_index(64)

    with pytest.raises(InvalidSquareError):
        square_from_index(100)


# =========================================================
# SQUARE: offset (desplazarse desde una casilla)
# =========================================================

def test_square_offset_valid():
    e4 = square_from_algebraic("e4")
    assert e4.offset(1, 1) == square_from_algebraic("f5")
    assert e4.offset(-1, -1) == square_from_algebraic("d3")


def test_square_offset_out_of_bounds_returns_none():
    a1 = square_from_algebraic("a1")
    assert a1.offset(-1, 0) is None
    assert a1.offset(0, -1) is None

    h8 = square_from_algebraic("h8")
    assert h8.offset(1, 0) is None
    assert h8.offset(0, 1) is None


def test_square_str_is_algebraic():
    assert str(square_from_algebraic("g6")) == "g6"