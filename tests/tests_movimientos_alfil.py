from chess.pieces import Piece, square_from_algebraic, WHITE, BLACK, BISHOP, PAWN
from chess.board import Board, create_initial_board
from chess.movimientos_alfil import obtener_movimientos_alfil


def test_alfil_solo_en_tablero_vacio_tiene_13_movimientos():
    # Un alfil en d4 puede recorrer sus 4 diagonales completas:
    # arriba-derecha (e5,f6,g7,h8 = 4), abajo-derecha (e3,f2,g1 = 3),
    # arriba-izquierda (c5,b6,a7 = 3), abajo-izquierda (c3,b2,a1 = 3)
    # Total: 4+3+3+3 = 13
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(BISHOP, WHITE))

    destinos = obtener_movimientos_alfil(board, square, WHITE)

    assert len(destinos) == 13


def test_alfil_se_para_al_chocar_con_pieza_propia():
    board = Board()
    casilla_alfil = square_from_algebraic("d4")
    board.set_piece(casilla_alfil, Piece(BISHOP, WHITE))
    # Un peon propio en la diagonal arriba-derecha, 2 casillas mas alla.
    board.set_piece(square_from_algebraic("f6"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_alfil(board, casilla_alfil, WHITE)

    assert square_from_algebraic("e5") in destinos
    assert square_from_algebraic("f6") not in destinos
    assert square_from_algebraic("g7") not in destinos
    assert square_from_algebraic("h8") not in destinos


def test_alfil_puede_capturar_pero_no_saltar_pieza_enemiga():
    board = Board()
    casilla_alfil = square_from_algebraic("d4")
    board.set_piece(casilla_alfil, Piece(BISHOP, WHITE))
    # Un peon ENEMIGO en la diagonal abajo-izquierda, 2 casillas mas alla.
    board.set_piece(square_from_algebraic("b2"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_alfil(board, casilla_alfil, WHITE)

    assert square_from_algebraic("c3") in destinos
    assert square_from_algebraic("b2") in destinos  # captura
    assert square_from_algebraic("a1") not in destinos  # no puede saltarlo


def test_alfil_c1_en_posicion_inicial_no_tiene_movimientos():
    # Al empezar una partida, el alfil de c1 esta completamente
    # bloqueado por sus propios peones (b2 y d2).
    board = create_initial_board()
    casilla_alfil = square_from_algebraic("c1")

    destinos = obtener_movimientos_alfil(board, casilla_alfil, WHITE)

    assert destinos == []