import pytest

from chess.exceptions import InvalidMoveError
from chess.pieces import (
    Piece, square_from_algebraic, WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)
from chess.board import Board, create_initial_board
from chess.move import Move, aplicar_jugada, calcular_casilla_al_paso


def sq(texto):
    return square_from_algebraic(texto)


def jugada(texto, promocion=None):
    # Atajo para crear una jugada a partir de "e2e4".
    return Move(sq(texto[:2]), sq(texto[2:4]), promocion)


# ---------- La clase Move ----------

def test_move_se_imprime_como_origen_y_destino():
    assert str(jugada("e2e4")) == "e2e4"


def test_move_con_promocion_se_imprime_con_letra():
    assert str(jugada("e7e8", QUEEN)) == "e7e8q"
    assert str(jugada("a2a1", KNIGHT)) == "a2a1n"


def test_dos_moves_iguales_son_iguales():
    assert jugada("e2e4") == jugada("e2e4")
    assert jugada("e2e4") != jugada("e2e3")
    assert jugada("e7e8", QUEEN) != jugada("e7e8", ROOK)


def test_move_es_hashable():
    assert len({jugada("e2e4"), jugada("e2e4")}) == 1


def test_move_con_promocion_invalida_da_error():
    with pytest.raises(InvalidMoveError):
        jugada("e7e8", KING)
    with pytest.raises(InvalidMoveError):
        jugada("e7e8", PAWN)


# ---------- Mover piezas ----------

def test_mover_peon_inicial_dos_casillas():
    board = create_initial_board()

    capturada = aplicar_jugada(board, jugada("e2e4"))

    assert capturada is None
    assert board.is_empty(sq("e2"))
    assert board.get_piece(sq("e4")) == Piece(PAWN, WHITE)
    assert len(board.all_pieces()) == 32


def test_mover_caballo_inicial():
    board = create_initial_board()

    aplicar_jugada(board, jugada("g1f3"))

    assert board.is_empty(sq("g1"))
    assert board.get_piece(sq("f3")) == Piece(KNIGHT, WHITE)


# ---------- Capturas ----------

def test_captura_devuelve_la_pieza_capturada_y_la_quita_del_tablero():
    board = Board()
    board.set_piece(sq("d4"), Piece(ROOK, WHITE))
    board.set_piece(sq("d7"), Piece(KNIGHT, BLACK))

    capturada = aplicar_jugada(board, jugada("d4d7"))

    assert capturada == Piece(KNIGHT, BLACK)
    assert board.get_piece(sq("d7")) == Piece(ROOK, WHITE)
    assert board.is_empty(sq("d4"))
    assert len(board.all_pieces()) == 1


# ---------- Captura al paso ----------

def test_captura_al_paso_quita_el_peon_de_al_lado():
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    capturada = aplicar_jugada(board, jugada("e5d6"), casilla_al_paso=sq("d6"))

    assert capturada == Piece(PAWN, BLACK)
    assert board.get_piece(sq("d6")) == Piece(PAWN, WHITE)
    assert board.is_empty(sq("d5"))  # el peon capturado desaparece
    assert board.is_empty(sq("e5"))


def test_captura_al_paso_de_peon_negro():
    board = Board()
    board.set_piece(sq("d4"), Piece(PAWN, BLACK))
    board.set_piece(sq("e4"), Piece(PAWN, WHITE))

    aplicar_jugada(board, jugada("d4e3"), casilla_al_paso=sq("e3"))

    assert board.get_piece(sq("e3")) == Piece(PAWN, BLACK)
    assert board.is_empty(sq("e4"))


def test_sin_casilla_al_paso_no_se_puede_capturar_al_paso():
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("e5d6"))


def test_calcular_casilla_al_paso_tras_doble_avance():
    board = create_initial_board()

    assert str(calcular_casilla_al_paso(board, jugada("e2e4"))) == "e3"
    assert str(calcular_casilla_al_paso(board, jugada("d7d5"))) == "d6"


def test_calcular_casilla_al_paso_es_none_si_no_es_doble_avance():
    board = create_initial_board()

    assert calcular_casilla_al_paso(board, jugada("e2e3")) is None
    assert calcular_casilla_al_paso(board, jugada("g1f3")) is None


def test_partida_corta_con_captura_al_paso():
    # 1. e4 a6 2. e5 d5 3. exd6 (al paso)
    board = create_initial_board()
    aplicar_jugada(board, jugada("e2e4"))
    aplicar_jugada(board, jugada("a7a6"))
    aplicar_jugada(board, jugada("e4e5"))

    doble_avance = jugada("d7d5")
    al_paso = calcular_casilla_al_paso(board, doble_avance)
    aplicar_jugada(board, doble_avance)

    capturada = aplicar_jugada(board, jugada("e5d6"), casilla_al_paso=al_paso)

    assert capturada == Piece(PAWN, BLACK)
    assert board.is_empty(sq("d5"))
    assert len(board.all_pieces()) == 31


# ---------- Promocion ----------

def test_peon_blanco_promociona_a_dama():
    board = Board()
    board.set_piece(sq("e7"), Piece(PAWN, WHITE))

    aplicar_jugada(board, jugada("e7e8", QUEEN))

    assert board.get_piece(sq("e8")) == Piece(QUEEN, WHITE)
    assert board.is_empty(sq("e7"))


def test_peon_negro_promociona_a_caballo():
    board = Board()
    board.set_piece(sq("a2"), Piece(PAWN, BLACK))

    aplicar_jugada(board, jugada("a2a1", KNIGHT))

    assert board.get_piece(sq("a1")) == Piece(KNIGHT, BLACK)


def test_promocion_con_captura():
    board = Board()
    board.set_piece(sq("g7"), Piece(PAWN, WHITE))
    board.set_piece(sq("h8"), Piece(ROOK, BLACK))

    capturada = aplicar_jugada(board, jugada("g7h8", ROOK))

    assert capturada == Piece(ROOK, BLACK)
    assert board.get_piece(sq("h8")) == Piece(ROOK, WHITE)


def test_llegar_al_final_sin_elegir_promocion_da_error():
    board = Board()
    board.set_piece(sq("e7"), Piece(PAWN, WHITE))

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("e7e8"))
    # y el tablero no ha cambiado
    assert board.get_piece(sq("e7")) == Piece(PAWN, WHITE)


def test_promocionar_fuera_del_final_da_error():
    board = Board()
    board.set_piece(sq("e2"), Piece(PAWN, WHITE))

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("e2e3", QUEEN))


def test_una_pieza_que_no_es_peon_no_puede_promocionar():
    board = Board()
    board.set_piece(sq("a1"), Piece(ROOK, WHITE))

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("a1a8", QUEEN))


# ---------- Jugadas ilegales ----------

def test_mover_desde_casilla_vacia_da_error():
    board = create_initial_board()

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("e4e5"))


def test_jugada_ilegal_da_error_y_no_cambia_el_tablero():
    board = create_initial_board()

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("e2e5"))  # el peon no avanza tres

    assert board.get_piece(sq("e2")) == Piece(PAWN, WHITE)
    assert board.is_empty(sq("e5"))


def test_no_se_puede_capturar_pieza_propia():
    board = create_initial_board()

    with pytest.raises(InvalidMoveError):
        aplicar_jugada(board, jugada("a1a2"))