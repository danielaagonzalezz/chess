from chess.pieces import Piece, square_from_algebraic, WHITE, BLACK, QUEEN, PAWN
from chess.board import Board, create_initial_board
from chess.movimientos_dama import obtener_movimientos_dama


def test_dama_sola_en_tablero_vacio_desde_d4_tiene_27_movimientos():
    # Desde d4 en un tablero vacio: 14 de torre (fila + columna)
    # y 13 de alfil (las dos diagonales) = 27.
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(QUEEN, WHITE))

    destinos = obtener_movimientos_dama(board, square, WHITE)

    assert len(destinos) == 27


def test_dama_en_esquina_tiene_21_movimientos():
    # Desde a1: 7 hacia arriba, 7 hacia la derecha y 7 en la diagonal.
    board = Board()
    square = square_from_algebraic("a1")
    board.set_piece(square, Piece(QUEEN, WHITE))

    destinos = obtener_movimientos_dama(board, square, WHITE)

    assert len(destinos) == 21


def test_dama_se_mueve_recto_y_en_diagonal():
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(QUEEN, WHITE))

    destinos = obtener_movimientos_dama(board, square, WHITE)

    assert square_from_algebraic("d8") in destinos  # recto, columna
    assert square_from_algebraic("h4") in destinos  # recto, fila
    assert square_from_algebraic("h8") in destinos  # diagonal
    assert square_from_algebraic("a1") in destinos  # diagonal
    # Un salto de caballo no es un movimiento de dama.
    assert square_from_algebraic("e6") not in destinos


def test_dama_se_para_al_chocar_con_pieza_propia():
    board = Board()
    casilla_dama = square_from_algebraic("d4")
    board.set_piece(casilla_dama, Piece(QUEEN, WHITE))
    # Un peon propio en la diagonal, 2 casillas arriba a la derecha.
    board.set_piece(square_from_algebraic("f6"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_dama(board, casilla_dama, WHITE)

    assert square_from_algebraic("e5") in destinos
    assert square_from_algebraic("f6") not in destinos
    assert square_from_algebraic("g7") not in destinos


def test_dama_puede_capturar_pero_no_saltar_pieza_enemiga():
    board = Board()
    casilla_dama = square_from_algebraic("d4")
    board.set_piece(casilla_dama, Piece(QUEEN, WHITE))
    # Un peon ENEMIGO en la fila, 2 casillas a la derecha.
    board.set_piece(square_from_algebraic("f4"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_dama(board, casilla_dama, WHITE)

    assert square_from_algebraic("e4") in destinos
    assert square_from_algebraic("f4") in destinos  # captura
    assert square_from_algebraic("g4") not in destinos


def test_dama_d1_en_posicion_inicial_no_tiene_movimientos():
    # Al empezar, la dama esta rodeada de sus propias piezas.
    board = create_initial_board()
    casilla_dama = square_from_algebraic("d1")

    destinos = obtener_movimientos_dama(board, casilla_dama, WHITE)

    assert destinos == []


def test_dama_no_devuelve_casillas_repetidas():
    board = Board()
    square = square_from_algebraic("e5")
    board.set_piece(square, Piece(QUEEN, WHITE))

    destinos = obtener_movimientos_dama(board, square, WHITE)

    assert len(destinos) == len(set(destinos))