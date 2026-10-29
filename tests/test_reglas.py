from chess.board import Board, create_initial_board
from chess.game import Game
from chess.move import Move, aplicar_jugada
from chess.pieces import (
    Piece, square_from_algebraic, WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)
from chess.reglas import (
    aplicar_jugada_completa, casilla_atacada, copiar_tablero,
    encontrar_rey, esta_en_jaque, jugadas_de_enroque, jugadas_legales,
    jugadas_pseudolegales, actualizar_derechos_enroque,
)


def sq(texto):
    return square_from_algebraic(texto)


def jugada(texto, promocion=None):
    return Move(sq(texto[:2]), sq(texto[2:4]), promocion)


def tablero(fen):
    # Atajo: crea un tablero a partir de un FEN (usando Game solo para leerlo).
    return Game.desde_fen(fen).board


def textos(jugadas):
    return sorted(str(j) for j in jugadas)


# ---------- copiar_tablero y encontrar_rey ----------

def test_copiar_tablero_es_independiente():
    original = create_initial_board()
    copia = copiar_tablero(original)
    aplicar_jugada(copia, jugada("e2e4"))
    assert original.get_piece(sq("e2")) == Piece(PAWN, WHITE)
    assert original.is_empty(sq("e4"))


def test_encontrar_rey():
    board = create_initial_board()
    assert encontrar_rey(board, WHITE) == sq("e1")
    assert encontrar_rey(board, BLACK) == sq("e8")


def test_encontrar_rey_en_tablero_vacio_es_none():
    assert encontrar_rey(Board(), WHITE) is None


# ---------- casilla_atacada y jaque ----------

def test_peon_ataca_en_diagonal_no_hacia_delante():
    board = tablero("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")
    assert casilla_atacada(board, sq("d3"), WHITE)
    assert casilla_atacada(board, sq("f3"), WHITE)
    assert not casilla_atacada(board, sq("e3"), WHITE)


def test_peon_negro_ataca_hacia_abajo():
    board = tablero("7k/4p3/8/8/8/8/8/4K3 w - - 0 1")
    assert casilla_atacada(board, sq("d6"), BLACK)
    assert casilla_atacada(board, sq("f6"), BLACK)
    assert not casilla_atacada(board, sq("d8"), BLACK)


def test_pieza_deslizante_bloqueada_no_ataca_detras():
    board = tablero("4k3/8/8/8/8/4P3/8/R3K3 w - - 0 1")
    assert casilla_atacada(board, sq("a8"), WHITE)
    # La torre ataca a lo largo de la fila 1 solo hasta el rey blanco.
    assert not casilla_atacada(board, sq("h1"), WHITE)


def test_posicion_inicial_no_hay_jaque():
    board = create_initial_board()
    assert not esta_en_jaque(board, WHITE)
    assert not esta_en_jaque(board, BLACK)


def test_jaque_de_torre():
    board = tablero("4r2k/8/8/8/8/8/8/4K3 w - - 0 1")
    assert esta_en_jaque(board, WHITE)
    assert not esta_en_jaque(board, BLACK)


def test_jaque_de_caballo():
    board = tablero("7k/8/8/8/8/3n4/8/4K3 w - - 0 1")
    assert esta_en_jaque(board, WHITE)


def test_jaque_de_peon():
    board = tablero("7k/8/8/8/8/8/3p4/4K3 w - - 0 1")
    assert esta_en_jaque(board, WHITE)


def test_tablero_sin_rey_no_esta_en_jaque():
    assert not esta_en_jaque(Board(), WHITE)


# ---------- jugadas legales ----------

def test_posicion_inicial_tiene_20_jugadas_legales():
    board = create_initial_board()
    assert len(jugadas_legales(board, WHITE)) == 20
    assert len(jugadas_legales(board, BLACK)) == 20


def test_rey_no_puede_moverse_a_casilla_atacada():
    # La torre negra controla la columna d: el rey no puede ir a d1 ni d2.
    board = tablero("3r3k/8/8/8/8/8/8/4K3 w - - 0 1")
    jugadas = textos(jugadas_legales(board, WHITE))
    assert "e1d1" not in jugadas
    assert "e1d2" not in jugadas
    assert "e1e2" in jugadas
    assert "e1f1" in jugadas


def test_pieza_clavada_no_puede_moverse_fuera_de_la_linea():
    # El alfil blanco de e2 esta clavado por la torre negra de e8.
    board = tablero("4r2k/8/8/8/8/8/4B3/4K3 w - - 0 1")
    jugadas = jugadas_legales(board, WHITE)
    assert [j for j in jugadas if j.origen == sq("e2")] == []


def test_pieza_clavada_si_puede_moverse_a_lo_largo_de_la_linea():
    # Una torre clavada en vertical puede seguir moviendose por esa columna.
    board = tablero("4r2k/8/8/8/8/8/4R3/4K3 w - - 0 1")
    jugadas = textos(jugadas_legales(board, WHITE))
    assert "e2e8" in jugadas  # captura a la torre que la clava
    assert "e2e5" in jugadas
    assert "e2a2" not in jugadas


def test_en_jaque_solo_valen_jugadas_que_lo_resuelven():
    # Jaque de torre en e8: el rey se aparta, o se tapa con la torre blanca.
    board = tablero("4r2k/8/8/8/8/8/R7/4K3 w - - 0 1")
    jugadas = textos(jugadas_legales(board, WHITE))
    assert "a2e2" in jugadas      # interponer la torre
    assert "a2a8" not in jugadas  # no resuelve el jaque
    assert "e1d1" in jugadas
    assert "e1e2" not in jugadas  # sigue en la columna e


def test_captura_al_paso_ilegal_si_deja_al_rey_en_jaque():
    # Si b5xc6 al paso, desaparecen b5 y c5 y la torre h5 da jaque al rey a5.
    board = tablero("8/8/8/KPp4r/8/8/8/7k w - c6 0 1")
    jugadas = textos(jugadas_legales(board, WHITE, sq("c6")))
    assert "b5c6" not in jugadas
    assert "b5b6" in jugadas


def test_captura_al_paso_legal():
    board = tablero("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    assert "e5d6" in textos(jugadas_legales(board, WHITE, sq("d6")))


def test_promocion_genera_cuatro_jugadas():
    board = tablero("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    del_peon = [j for j in jugadas_legales(board, WHITE) if j.origen == sq("a7")]
    assert textos(del_peon) == ["a7a8b", "a7a8n", "a7a8q", "a7a8r"]


def test_pseudolegales_incluyen_jugadas_que_dejan_en_jaque():
    # El alfil clavado esta en las pseudolegales pero no en las legales.
    board = tablero("4r2k/8/8/8/8/8/4B3/4K3 w - - 0 1")
    pseudo = [j for j in jugadas_pseudolegales(board, WHITE) if j.origen == sq("e2")]
    assert len(pseudo) > 0


# ---------- enroque ----------

def test_enroques_disponibles():
    board = tablero("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert textos(jugadas_de_enroque(board, WHITE, {"K", "Q", "k", "q"})) == ["e1c1", "e1g1"]
    assert textos(jugadas_de_enroque(board, BLACK, {"K", "Q", "k", "q"})) == ["e8c8", "e8g8"]


def test_enroque_sin_derechos_no_se_puede():
    board = tablero("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
    assert jugadas_de_enroque(board, WHITE, set()) == []
    assert textos(jugadas_de_enroque(board, WHITE, {"K"})) == ["e1g1"]
    assert textos(jugadas_de_enroque(board, WHITE, {"Q"})) == ["e1c1"]


def test_enroque_bloqueado_por_una_pieza():
    board = tablero("4k3/8/8/8/8/8/8/RN2K1NR w KQ - 0 1")
    assert jugadas_de_enroque(board, WHITE, {"K", "Q"}) == []


def test_no_se_puede_enrocar_en_jaque():
    board = tablero("4r2k/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert jugadas_de_enroque(board, WHITE, {"K", "Q"}) == []


def test_no_se_puede_enrocar_pasando_por_casilla_atacada():
    # La torre negra de f8 ataca f1: el enroque corto pasa por f1.
    board = tablero("5r1k/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert textos(jugadas_de_enroque(board, WHITE, {"K", "Q"})) == ["e1c1"]


def test_no_se_puede_enrocar_acabando_en_casilla_atacada():
    # La torre negra de g8 ataca g1: el rey acabaria en jaque.
    board = tablero("6rk/8/8/8/8/8/8/R3K2R w KQ - 0 1")
    assert textos(jugadas_de_enroque(board, WHITE, {"K", "Q"})) == ["e1c1"]


def test_enroque_largo_con_b1_atacada_es_legal():
    # Solo la torre pasa por b1; el rey no, asi que puede estar atacada.
    board = tablero("1r5k/8/8/8/8/8/8/R3K3 w Q - 0 1")
    assert textos(jugadas_de_enroque(board, WHITE, {"Q"})) == ["e1c1"]


def test_enroque_necesita_la_torre_en_su_sitio():
    board = tablero("4k3/8/8/8/8/8/8/4K2N w K - 0 1")
    assert jugadas_de_enroque(board, WHITE, {"K"}) == []


def test_jugadas_legales_incluyen_el_enroque():
    board = tablero("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    jugadas = textos(jugadas_legales(board, WHITE, None, {"K", "Q", "k", "q"}))
    assert "e1g1" in jugadas and "e1c1" in jugadas


def test_aplicar_enroque_corto_mueve_rey_y_torre():
    board = tablero("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    aplicar_jugada_completa(board, jugada("e1g1"))
    assert board.get_piece(sq("g1")) == Piece(KING, WHITE)
    assert board.get_piece(sq("f1")) == Piece(ROOK, WHITE)
    assert board.is_empty(sq("e1"))
    assert board.is_empty(sq("h1"))


def test_aplicar_enroque_largo_negro_mueve_rey_y_torre():
    board = tablero("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
    aplicar_jugada_completa(board, jugada("e8c8"))
    assert board.get_piece(sq("c8")) == Piece(KING, BLACK)
    assert board.get_piece(sq("d8")) == Piece(ROOK, BLACK)
    assert board.is_empty(sq("a8"))
    assert board.is_empty(sq("e8"))


def test_aplicar_jugada_completa_normal_funciona_como_aplicar_jugada():
    board = create_initial_board()
    capturada = aplicar_jugada_completa(board, jugada("e2e4"))
    assert capturada is None
    assert board.get_piece(sq("e4")) == Piece(PAWN, WHITE)


# ---------- derechos de enroque ----------

def test_mover_el_rey_pierde_los_dos_enroques():
    assert actualizar_derechos_enroque({"K", "Q", "k", "q"}, jugada("e1e2")) == {"k", "q"}


def test_mover_una_torre_pierde_solo_su_enroque():
    assert actualizar_derechos_enroque({"K", "Q", "k", "q"}, jugada("h1h2")) == {"Q", "k", "q"}
    assert actualizar_derechos_enroque({"K", "Q", "k", "q"}, jugada("a8a7")) == {"K", "Q", "k"}


def test_capturar_una_torre_en_su_esquina_pierde_ese_enroque():
    assert actualizar_derechos_enroque({"K", "Q", "k", "q"}, jugada("a1a8")) == {"K", "k"}


def test_una_jugada_normal_no_cambia_los_derechos():
    derechos = {"K", "Q", "k", "q"}
    assert actualizar_derechos_enroque(derechos, jugada("e2e4")) == derechos


def test_actualizar_derechos_no_modifica_el_conjunto_original():
    derechos = {"K", "Q"}
    actualizar_derechos_enroque(derechos, jugada("e1e2"))
    assert derechos == {"K", "Q"}
