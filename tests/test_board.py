from chess.pieces import (
    Piece, Square, square_from_algebraic,
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)
from chess.board import Board, create_initial_board


# ---------- Tablero vacío: colocar, leer, quitar piezas ----------

def test_new_board_is_empty():
    board = Board()
    for file in range(8):
        for rank in range(8):
            assert board.is_empty(Square(file, rank))


def test_set_and_get_piece():
    board = Board()
    square = square_from_algebraic("e4")
    piece = Piece(QUEEN, WHITE)
    board.set_piece(square, piece)
    assert board.get_piece(square) == piece
    assert not board.is_empty(square)


def test_remove_piece():
    board = Board()
    square = square_from_algebraic("e4")
    board.set_piece(square, Piece(PAWN, WHITE))
    board.remove_piece(square)
    assert board.is_empty(square)
    assert board.get_piece(square) is None


def test_set_piece_overwrites_previous_piece():
    board = Board()
    square = square_from_algebraic("e4")
    board.set_piece(square, Piece(PAWN, WHITE))
    board.set_piece(square, Piece(QUEEN, BLACK))
    assert board.get_piece(square) == Piece(QUEEN, BLACK)


def test_empty_board_has_no_pieces():
    board = Board()
    assert board.all_pieces() == []


# ---------- Posición inicial estándar ----------

def test_initial_board_white_back_rank():
    board = create_initial_board()
    assert board.get_piece(square_from_algebraic("a1")) == Piece(ROOK, WHITE)
    assert board.get_piece(square_from_algebraic("b1")) == Piece(KNIGHT, WHITE)
    assert board.get_piece(square_from_algebraic("c1")) == Piece(BISHOP, WHITE)
    assert board.get_piece(square_from_algebraic("d1")) == Piece(QUEEN, WHITE)
    assert board.get_piece(square_from_algebraic("e1")) == Piece(KING, WHITE)
    assert board.get_piece(square_from_algebraic("f1")) == Piece(BISHOP, WHITE)
    assert board.get_piece(square_from_algebraic("g1")) == Piece(KNIGHT, WHITE)
    assert board.get_piece(square_from_algebraic("h1")) == Piece(ROOK, WHITE)


def test_initial_board_black_back_rank():
    board = create_initial_board()
    assert board.get_piece(square_from_algebraic("a8")) == Piece(ROOK, BLACK)
    assert board.get_piece(square_from_algebraic("d8")) == Piece(QUEEN, BLACK)
    assert board.get_piece(square_from_algebraic("e8")) == Piece(KING, BLACK)
    assert board.get_piece(square_from_algebraic("h8")) == Piece(ROOK, BLACK)


def test_initial_board_pawns():
    board = create_initial_board()
    for file in range(8):
        white_pawn_square = Square(file, 1)
        black_pawn_square = Square(file, 6)
        assert board.get_piece(white_pawn_square) == Piece(PAWN, WHITE)
        assert board.get_piece(black_pawn_square) == Piece(PAWN, BLACK)


def test_initial_board_middle_is_empty():
    # Las filas 3, 4, 5 y 6 (indices 2 a 5) no tienen ninguna pieza al empezar.
    board = create_initial_board()
    for rank in range(2, 6):
        for file in range(8):
            assert board.is_empty(Square(file, rank))


def test_initial_board_has_32_pieces():
    board = create_initial_board()
    assert len(board.all_pieces()) == 32


# ---------- Representación en texto ----------

def test_board_str_has_9_lines():
    board = create_initial_board()
    lineas = str(board).split("\n")
    # 8 filas del tablero + 1 linea final con las letras de las columnas
    assert len(lineas) == 9


def test_board_str_contains_column_letters():
    board = create_initial_board()
    assert "a b c d e f g h" in str(board)


def test_board_str_shows_white_rook_on_a1():
    board = create_initial_board()
    # La fila 1 es la ultima linea antes de la de las letras
    lineas = str(board).split("\n")
    primera_fila = lineas[-2]
    assert primera_fila.startswith("1  R")