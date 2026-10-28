from chess.pieces import (
    Piece, square_from_algebraic, WHITE, BLACK, PAWN, KNIGHT,
)
from chess.board import Board, create_initial_board
from chess.movimientos_peon import obtener_movimientos_peon


def sq(texto):
    return square_from_algebraic(texto)


def nombres(casillas):
    # Convierte una lista de casillas a un conjunto de textos ("e3", "e4"...)
    # para comparar mas facil en los tests.
    return {str(c) for c in casillas}


# ---------- Avance ----------

def test_peon_blanco_inicial_puede_avanzar_una_o_dos_casillas():
    board = create_initial_board()

    destinos = obtener_movimientos_peon(board, sq("e2"), WHITE)

    assert nombres(destinos) == {"e3", "e4"}


def test_peon_negro_inicial_puede_avanzar_una_o_dos_casillas():
    board = create_initial_board()

    destinos = obtener_movimientos_peon(board, sq("e7"), BLACK)

    assert nombres(destinos) == {"e6", "e5"}


def test_peon_fuera_de_fila_inicial_solo_avanza_una_casilla():
    board = Board()
    board.set_piece(sq("e3"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_peon(board, sq("e3"), WHITE)

    assert nombres(destinos) == {"e4"}


def test_peon_negro_avanza_hacia_abajo():
    board = Board()
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_peon(board, sq("d5"), BLACK)

    assert nombres(destinos) == {"d4"}


# ---------- Bloqueos ----------

def test_peon_bloqueado_por_pieza_delante_no_avanza():
    board = Board()
    board.set_piece(sq("e2"), Piece(PAWN, WHITE))
    board.set_piece(sq("e3"), Piece(KNIGHT, BLACK))

    destinos = obtener_movimientos_peon(board, sq("e2"), WHITE)

    # No puede capturar hacia delante, ni saltarse la pieza.
    assert destinos == []


def test_peon_no_puede_hacer_doble_avance_si_la_segunda_casilla_esta_ocupada():
    board = Board()
    board.set_piece(sq("e2"), Piece(PAWN, WHITE))
    board.set_piece(sq("e4"), Piece(KNIGHT, BLACK))

    destinos = obtener_movimientos_peon(board, sq("e2"), WHITE)

    assert nombres(destinos) == {"e3"}


# ---------- Capturas ----------

def test_peon_captura_en_diagonal_pieza_enemiga():
    board = Board()
    board.set_piece(sq("e4"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(KNIGHT, BLACK))
    board.set_piece(sq("f5"), Piece(KNIGHT, BLACK))

    destinos = obtener_movimientos_peon(board, sq("e4"), WHITE)

    assert nombres(destinos) == {"e5", "d5", "f5"}


def test_peon_no_captura_pieza_propia_en_diagonal():
    board = Board()
    board.set_piece(sq("e4"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(KNIGHT, WHITE))

    destinos = obtener_movimientos_peon(board, sq("e4"), WHITE)

    assert nombres(destinos) == {"e5"}


def test_peon_no_se_mueve_en_diagonal_a_casilla_vacia():
    board = Board()
    board.set_piece(sq("e4"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_peon(board, sq("e4"), WHITE)

    assert "d5" not in nombres(destinos)
    assert "f5" not in nombres(destinos)


def test_peon_negro_captura_en_diagonal_hacia_abajo():
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, BLACK))
    board.set_piece(sq("d4"), Piece(KNIGHT, WHITE))

    destinos = obtener_movimientos_peon(board, sq("e5"), BLACK)

    assert nombres(destinos) == {"e4", "d4"}


# ---------- Bordes ----------

def test_peon_en_columna_a_solo_captura_hacia_un_lado():
    board = Board()
    board.set_piece(sq("a4"), Piece(PAWN, WHITE))
    board.set_piece(sq("b5"), Piece(KNIGHT, BLACK))

    destinos = obtener_movimientos_peon(board, sq("a4"), WHITE)

    assert nombres(destinos) == {"a5", "b5"}


def test_peon_en_ultima_fila_no_tiene_movimientos():
    # Un peon blanco en la fila 8 se sale del tablero al avanzar.
    # (En una partida real ya se habria promocionado.)
    board = Board()
    board.set_piece(sq("e8"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_peon(board, sq("e8"), WHITE)

    assert destinos == []


# ---------- Captura al paso ----------

def test_peon_blanco_captura_al_paso():
    # El peon blanco esta en e5. El rival mueve d7 -> d5 (dos casillas):
    # la casilla "por la que ha pasado" es d6.
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_peon(
        board, sq("e5"), WHITE, casilla_al_paso=sq("d6")
    )

    assert nombres(destinos) == {"e6", "d6"}


def test_peon_negro_captura_al_paso():
    board = Board()
    board.set_piece(sq("d4"), Piece(PAWN, BLACK))
    board.set_piece(sq("e4"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_peon(
        board, sq("d4"), BLACK, casilla_al_paso=sq("e3")
    )

    assert nombres(destinos) == {"d3", "e3"}


def test_sin_casilla_al_paso_no_hay_captura_al_paso():
    board = Board()
    board.set_piece(sq("e5"), Piece(PAWN, WHITE))
    board.set_piece(sq("d5"), Piece(PAWN, BLACK))

    destinos = obtener_movimientos_peon(board, sq("e5"), WHITE)

    assert nombres(destinos) == {"e6"}


def test_casilla_al_paso_lejana_no_afecta():
    # Si la casilla al paso no esta en una diagonal del peon, se ignora.
    board = Board()
    board.set_piece(sq("a2"), Piece(PAWN, WHITE))

    destinos = obtener_movimientos_peon(
        board, sq("a2"), WHITE, casilla_al_paso=sq("g6")
    )

    assert nombres(destinos) == {"a3", "a4"}