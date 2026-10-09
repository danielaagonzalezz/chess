from chess.pieces import Piece, square_from_algebraic, WHITE, BLACK, KNIGHT, PAWN
from chess.board import Board, create_initial_board
from chess.caballo import obtener_movimientos_caballo


def test_caballo_en_tablero_vacio_centro_tiene_8_movimientos():
    # Un caballo solo en medio de un tablero vacio puede ir a las 8
    # posiciones en L, porque no hay nada que se lo impida.
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(KNIGHT, WHITE))

    destinos = obtener_movimientos_caballo(board, square, WHITE)

    destinos_esperados = [
        square_from_algebraic("e6"),
        square_from_algebraic("f5"),
        square_from_algebraic("f3"),
        square_from_algebraic("e2"),
        square_from_algebraic("c2"),
        square_from_algebraic("b3"),
        square_from_algebraic("b5"),
        square_from_algebraic("c6"),
    ]

    assert len(destinos) == 8
    for esperado in destinos_esperados:
        assert esperado in destinos


def test_caballo_en_esquina_tiene_solo_2_movimientos():
    # Un caballo en la esquina a1 tiene mucho menos sitio: la mayoria
    # de sus 8 saltos se salen del tablero.
    board = Board()
    square = square_from_algebraic("a1")
    board.set_piece(square, Piece(KNIGHT, WHITE))

    destinos = obtener_movimientos_caballo(board, square, WHITE)

    assert len(destinos) == 2
    assert square_from_algebraic("b3") in destinos
    assert square_from_algebraic("c2") in destinos


def test_caballo_no_puede_moverse_sobre_pieza_propia():
    board = Board()
    casilla_caballo = square_from_algebraic("d4")
    board.set_piece(casilla_caballo, Piece(KNIGHT, WHITE))
    # Colocamos un peon blanco (mismo color) en uno de los destinos posibles.
    board.set_piece(square_from_algebraic("f5"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_caballo(board, casilla_caballo, WHITE)

    assert square_from_algebraic("f5") not in destinos
    assert len(destinos) == 7  # los otros 7 destinos siguen disponibles


def test_caballo_puede_capturar_pieza_enemiga():
    board = Board()
    casilla_caballo = square_from_algebraic("d4")
    board.set_piece(casilla_caballo, Piece(KNIGHT, WHITE))
    # Colocamos un peon NEGRO (color contrario) en uno de los destinos.
    board.set_piece(square_from_algebraic("f5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_caballo(board, casilla_caballo, WHITE)

    # Si puede capturarlo, f5 SIGUE estando en la lista de destinos.
    assert square_from_algebraic("f5") in destinos
    assert len(destinos) == 8


def test_caballo_b1_en_posicion_inicial():
    # Comprobacion con la posicion real de inicio de una partida:
    # el caballo blanco de b1 solo puede ir a a3 o c3 al principio
    # (el resto de sus saltos caen en piezas propias o fuera del tablero).
    board = create_initial_board()
    casilla_caballo = square_from_algebraic("b1")

    destinos = obtener_movimientos_caballo(board, casilla_caballo, WHITE)

    assert len(destinos) == 2
    assert square_from_algebraic("a3") in destinos
    assert square_from_algebraic("c3") in destinos