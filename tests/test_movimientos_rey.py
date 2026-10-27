from chess.pieces import Piece, square_from_algebraic, WHITE, BLACK, KING, PAWN
from chess.board import Board, create_initial_board
from chess.movimientos_rey import obtener_movimientos_rey


def test_rey_solo_en_el_centro_tiene_8_movimientos():
    # Un rey en medio de un tablero vacio puede ir a las 8 casillas de alrededor.
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(KING, WHITE))

    destinos = obtener_movimientos_rey(board, square, WHITE)

    assert len(destinos) == 8


def test_rey_en_esquina_tiene_3_movimientos():
    board = Board()
    square = square_from_algebraic("a1")
    board.set_piece(square, Piece(KING, WHITE))

    destinos = obtener_movimientos_rey(board, square, WHITE)

    assert len(destinos) == 3
    assert square_from_algebraic("a2") in destinos
    assert square_from_algebraic("b1") in destinos
    assert square_from_algebraic("b2") in destinos


def test_rey_en_borde_tiene_5_movimientos():
    board = Board()
    square = square_from_algebraic("e1")
    board.set_piece(square, Piece(KING, WHITE))

    destinos = obtener_movimientos_rey(board, square, WHITE)

    assert len(destinos) == 5


def test_rey_solo_se_mueve_una_casilla():
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(KING, WHITE))

    destinos = obtener_movimientos_rey(board, square, WHITE)

    assert square_from_algebraic("d5") in destinos
    assert square_from_algebraic("d6") not in destinos
    assert square_from_algebraic("f4") not in destinos


def test_rey_no_puede_ir_a_casilla_con_pieza_propia():
    board = Board()
    casilla_rey = square_from_algebraic("d4")
    board.set_piece(casilla_rey, Piece(KING, WHITE))
    board.set_piece(square_from_algebraic("d5"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_rey(board, casilla_rey, WHITE)

    assert square_from_algebraic("d5") not in destinos
    assert len(destinos) == 7


def test_rey_puede_capturar_pieza_enemiga():
    board = Board()
    casilla_rey = square_from_algebraic("d4")
    board.set_piece(casilla_rey, Piece(KING, WHITE))
    board.set_piece(square_from_algebraic("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_rey(board, casilla_rey, WHITE)

    assert square_from_algebraic("d5") in destinos
    assert len(destinos) == 8


def test_rey_e1_en_posicion_inicial_no_tiene_movimientos():
    # Al empezar, el rey esta rodeado de sus propias piezas.
    board = create_initial_board()
    casilla_rey = square_from_algebraic("e1")

    destinos = obtener_movimientos_rey(board, casilla_rey, WHITE)

    assert destinos == []