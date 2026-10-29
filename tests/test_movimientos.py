from chess.pieces import (
    Piece, square_from_algebraic, WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)
from chess.board import Board, create_initial_board
from chess.movimientos import obtener_movimientos


def sq(texto):
    return square_from_algebraic(texto)


def test_casilla_vacia_no_tiene_movimientos():
    board = Board()

    assert obtener_movimientos(board, sq("e4")) == []


def test_cada_pieza_usa_sus_propios_movimientos():
    # Una pieza sola en d4, en un tablero vacio: cuantos destinos tiene.
    esperados = {
        KNIGHT: 8,
        BISHOP: 13,
        ROOK: 14,
        QUEEN: 27,
        KING: 8,
        PAWN: 1,  # un peon blanco en d4 solo avanza una casilla
    }
    for tipo, cantidad in esperados.items():
        board = Board()
        board.set_piece(sq("d4"), Piece(tipo, WHITE))

        destinos = obtener_movimientos(board, sq("d4"))

        assert len(destinos) == cantidad, tipo


def test_el_color_de_la_pieza_se_toma_del_tablero():
    board = Board()
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos(board, sq("d5"))

    assert [str(d) for d in destinos] == ["d4"]


def test_posicion_inicial_blancas_tienen_20_movimientos():
    # En la posicion inicial las blancas tienen 20 jugadas posibles:
    # 16 de peon (8 peones x 2) y 4 de caballo (2 caballos x 2).
    board = create_initial_board()
    total = 0

    for square, pieza in board.all_pieces():
        if pieza.color == WHITE:
            total += len(obtener_movimientos(board, square))

    assert total == 20


def test_casilla_al_paso_llega_hasta_el_peon():
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos(board, sq("e5"), casilla_al_paso=sq("d6"))

    assert sq("d6") in destinos