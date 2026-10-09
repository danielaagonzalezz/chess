from chess.pieces import Piece, square_from_algebraic, WHITE, BLACK, ROOK, PAWN
from chess.board import Board, create_initial_board
from chess.movimientos_torre import obtener_movimientos_torre


def test_torre_sola_en_tablero_vacio_tiene_14_movimientos():
    # Una torre sola en medio de un tablero vacio puede recorrer toda
    # su columna (7 casillas) y toda su fila (7 casillas) = 14.
    board = Board()
    square = square_from_algebraic("d4")
    board.set_piece(square, Piece(ROOK, WHITE))

    destinos = obtener_movimientos_torre(board, square, WHITE)

    assert len(destinos) == 14


def test_torre_se_para_al_chocar_con_pieza_propia():
    board = Board()
    casilla_torre = square_from_algebraic("d4")
    board.set_piece(casilla_torre, Piece(ROOK, WHITE))
    # Un peon propio justo 2 casillas arriba.
    board.set_piece(square_from_algebraic("d6"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_torre(board, casilla_torre, WHITE)

    # Hacia arriba solo puede llegar hasta d5 (la casilla justo antes
    # del peon propio); no puede entrar en d6 ni seguir mas alla.
    assert square_from_algebraic("d5") in destinos
    assert square_from_algebraic("d6") not in destinos
    assert square_from_algebraic("d7") not in destinos
    assert square_from_algebraic("d8") not in destinos


def test_torre_puede_capturar_pero_no_saltar_pieza_enemiga():
    board = Board()
    casilla_torre = square_from_algebraic("d4")
    board.set_piece(casilla_torre, Piece(ROOK, WHITE))
    # Un peon ENEMIGO justo 2 casillas abajo.
    board.set_piece(square_from_algebraic("d2"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_torre(board, casilla_torre, WHITE)

    # Hacia abajo: puede llegar hasta d3 (vacia) y capturar en d2,
    # pero no puede seguir hasta d1 (estaria saltando la pieza capturada).
    assert square_from_algebraic("d3") in destinos
    assert square_from_algebraic("d2") in destinos  # captura
    assert square_from_algebraic("d1") not in destinos


def test_torre_a1_en_posicion_inicial_no_tiene_movimientos():
    # Al empezar una partida, la torre de a1 esta completamente
    # bloqueada: el peon de a2 le tapa hacia arriba, y el caballo
    # de b1 le tapa hacia la derecha. No puede moverse a ningun sitio.
    board = create_initial_board()
    casilla_torre = square_from_algebraic("a1")

    destinos = obtener_movimientos_torre(board, casilla_torre, WHITE)

    assert destinos == []
