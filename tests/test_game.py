import pytest

from chess.exceptions import (
    GameOverError, InvalidFenError, InvalidMoveError, InvalidSquareError,
)
from chess.game import (
    Game, FEN_INICIAL, RESULTADO_BLANCAS, RESULTADO_NEGRAS, RESULTADO_TABLAS,
    JAQUE_MATE, AHOGADO, MATERIAL_INSUFICIENTE, TRIPLE_REPETICION,
    REGLA_50_MOVIMIENTOS,
)
from chess.move import Move, jugada_desde_texto
from chess.pieces import (
    Piece, square_from_algebraic, WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
)


def sq(texto):
    return square_from_algebraic(texto)


def jugar_todas(game, *jugadas):
    for j in jugadas:
        game.jugar(j)


# ---------- Estado inicial ----------

def test_partida_nueva_estado_inicial():
    game = Game()
    assert game.turno == WHITE
    assert game.derechos_enroque == {"K", "Q", "k", "q"}
    assert game.casilla_al_paso is None
    assert game.historial == []
    assert game.resultado is None
    assert not game.esta_terminada()
    assert not game.esta_en_jaque()
    assert game.ganador() is None


def test_partida_nueva_tiene_20_jugadas():
    assert len(Game().jugadas_legales()) == 20


def test_fen_de_la_partida_nueva():
    assert Game().fen() == FEN_INICIAL


def test_str_es_el_tablero():
    assert str(Game()) == str(Game().board)


# ---------- Jugar ----------

def test_jugar_cambia_el_turno_y_guarda_historial():
    game = Game()
    game.jugar("e2e4")
    assert game.turno == BLACK
    assert game.board.get_piece(sq("e4")) == Piece(PAWN, WHITE)
    assert game.historial == [Move(sq("e2"), sq("e4"))]


def test_jugar_acepta_objetos_move():
    game = Game()
    game.jugar(Move(sq("g1"), sq("f3")))
    assert game.board.get_piece(sq("f3")) == Piece(KNIGHT, WHITE)


def test_jugada_ilegal_lanza_error_y_no_cambia_la_partida():
    game = Game()
    fen_antes = game.fen()
    with pytest.raises(InvalidMoveError):
        game.jugar("e2e5")
    assert game.fen() == fen_antes
    assert game.turno == WHITE


def test_no_se_puede_mover_pieza_del_rival():
    game = Game()
    with pytest.raises(InvalidMoveError):
        game.jugar("e7e5")


def test_no_se_puede_mover_una_casilla_vacia():
    with pytest.raises(InvalidMoveError):
        Game().jugar("e4e5")


def test_texto_invalido_lanza_error():
    game = Game()
    with pytest.raises(InvalidMoveError):
        game.jugar("e2")
    with pytest.raises(InvalidSquareError):
        game.jugar("hola")
    with pytest.raises(InvalidSquareError):
        game.jugar("z9z9")


def test_numero_de_jugada_sube_tras_mover_negras():
    game = Game()
    game.jugar("e2e4")
    assert game.numero_jugada == 1
    game.jugar("e7e5")
    assert game.numero_jugada == 2


def test_fen_tras_1_e4():
    game = Game()
    game.jugar("e2e4")
    assert game.fen() == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"


def test_medios_movimientos_se_reinician_con_peon_y_captura():
    game = Game()
    game.jugar("g1f3")
    assert game.medios_movimientos == 1
    game.jugar("g8f6")
    assert game.medios_movimientos == 2
    game.jugar("e2e4")
    assert game.medios_movimientos == 0


# ---------- Jaque y jaque mate ----------

def test_jaque_se_detecta_tras_una_jugada():
    game = Game()
    jugar_todas(game, "e2e4", "f7f6", "d1h5")
    assert game.esta_en_jaque()
    assert not game.esta_terminada()


def test_mate_del_loco():
    game = Game()
    jugar_todas(game, "f2f3", "e7e5", "g2g4", "d8h4")
    assert game.esta_terminada()
    assert game.resultado == RESULTADO_NEGRAS
    assert game.motivo == JAQUE_MATE
    assert game.ganador() == BLACK
    assert game.jugadas_legales() == []


def test_mate_del_pastor():
    game = Game()
    jugar_todas(game, "e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7")
    assert game.resultado == RESULTADO_BLANCAS
    assert game.motivo == JAQUE_MATE
    assert game.ganador() == WHITE


def test_no_se_puede_jugar_con_la_partida_terminada():
    game = Game()
    jugar_todas(game, "f2f3", "e7e5", "g2g4", "d8h4")
    with pytest.raises(GameOverError):
        game.jugar("a2a3")


# ---------- Tablas ----------

def test_ahogado():
    game = Game.desde_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert game.resultado == RESULTADO_TABLAS
    assert game.motivo == AHOGADO
    assert game.ganador() is None
    assert not game.esta_en_jaque()


def test_ahogado_tras_jugar():
    game = Game.desde_fen("7k/8/5QK1/8/8/8/8/8 w - - 0 1")
    game.jugar("f6f7")
    assert game.resultado == RESULTADO_TABLAS
    assert game.motivo == AHOGADO


@pytest.mark.parametrize("fen", [
    "8/8/8/4k3/8/8/4K3/8 w - - 0 1",           # rey contra rey
    "8/8/8/4k3/8/8/4K3/6N1 w - - 0 1",         # rey y caballo contra rey
    "8/8/8/4k3/8/8/4K3/6B1 w - - 0 1",         # rey y alfil contra rey
    "8/8/8/4k1b1/8/8/4K3/6B1 w - - 0 1",       # alfiles en casillas del mismo color
])
def test_material_insuficiente(fen):
    game = Game.desde_fen(fen)
    assert game.resultado == RESULTADO_TABLAS
    assert game.motivo == MATERIAL_INSUFICIENTE


@pytest.mark.parametrize("fen", [
    "8/8/8/4k3/8/8/4K3/5BB1 w - - 0 1",        # dos alfiles de colores distintos
    "8/8/8/4k3/8/8/4K3/6NN w - - 0 1",         # dos caballos (se puede mate)
    "8/8/8/4k3/8/8/4K1P1/8 w - - 0 1",         # hay un peon
    "8/8/8/4k3/8/8/4K3/6R1 w - - 0 1",         # hay una torre
])
def test_material_suficiente(fen):
    game = Game.desde_fen(fen)
    assert game.resultado is None


def test_triple_repeticion():
    game = Game()
    ciclo = ["g1f3", "g8f6", "f3g1", "f6g8"]
    jugar_todas(game, *ciclo)
    assert game.resultado is None  # la posicion inicial se ha visto 2 veces
    jugar_todas(game, *ciclo[:3])
    assert game.resultado is None
    game.jugar(ciclo[3])           # tercera vez
    assert game.resultado == RESULTADO_TABLAS
    assert game.motivo == TRIPLE_REPETICION


def test_regla_de_los_50_movimientos():
    game = Game.desde_fen("4k3/8/8/8/8/8/R7/4K3 w - - 99 80")
    assert game.resultado is None
    game.jugar("a2a3")
    assert game.resultado == RESULTADO_TABLAS
    assert game.motivo == REGLA_50_MOVIMIENTOS


def test_jaque_mate_gana_a_la_regla_de_50_movimientos():
    # Mate con el contador en 99: el mate manda sobre las tablas.
    game = Game.desde_fen("7k/8/6K1/8/8/8/8/R7 w - - 99 80")
    game.jugar("a1a8")
    assert game.resultado == RESULTADO_BLANCAS
    assert game.motivo == JAQUE_MATE


# ---------- Enroque dentro de una partida ----------

def test_enroque_corto_en_partida():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    game.jugar("e1g1")
    assert game.board.get_piece(sq("g1")) == Piece(KING, WHITE)
    assert game.board.get_piece(sq("f1")) == Piece(ROOK, WHITE)
    assert game.derechos_enroque == {"k", "q"}


def test_enroque_largo_negro_en_partida():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1")
    game.jugar("e8c8")
    assert game.board.get_piece(sq("c8")) == Piece(KING, BLACK)
    assert game.board.get_piece(sq("d8")) == Piece(ROOK, BLACK)
    assert game.derechos_enroque == {"K", "Q"}


def test_mover_torre_pierde_el_enroque_en_partida():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    game.jugar("h1h2")
    assert game.derechos_enroque == {"Q", "k", "q"}
    game.jugar("a8a7")
    assert game.derechos_enroque == {"Q", "k"}


def test_capturar_torre_pierde_el_enroque_del_rival():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    game.jugar("a1a8")
    assert game.derechos_enroque == {"K", "k"}


def test_no_se_puede_enrocar_despues_de_mover_el_rey_y_volver():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    jugar_todas(game, "e1e2", "e8e7", "e2e1", "e7e8")
    assert game.derechos_enroque == set()
    with pytest.raises(InvalidMoveError):
        game.jugar("e1g1")


# ---------- Captura al paso y promocion dentro de una partida ----------

def test_captura_al_paso_en_partida():
    game = Game()
    jugar_todas(game, "e2e4", "a7a6", "e4e5", "d7d5")
    assert game.casilla_al_paso == sq("d6")
    game.jugar("e5d6")
    assert game.board.get_piece(sq("d6")) == Piece(PAWN, WHITE)
    assert game.board.is_empty(sq("d5"))  # el peon capturado desaparece


def test_captura_al_paso_solo_vale_en_el_turno_siguiente():
    game = Game()
    jugar_todas(game, "e2e4", "a7a6", "e4e5", "d7d5", "h2h3", "h7h6")
    assert game.casilla_al_paso is None
    with pytest.raises(InvalidMoveError):
        game.jugar("e5d6")


def test_promocion_en_partida():
    game = Game.desde_fen("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    game.jugar("a7a8q")
    assert game.board.get_piece(sq("a8")) == Piece(QUEEN, WHITE)


def test_promocion_a_caballo_en_partida():
    game = Game.desde_fen("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    game.jugar("a7a8n")
    assert game.board.get_piece(sq("a8")) == Piece(KNIGHT, WHITE)


def test_promocion_sin_elegir_pieza_es_ilegal():
    game = Game.desde_fen("8/P6k/8/8/8/8/8/K7 w - - 0 1")
    with pytest.raises(InvalidMoveError):
        game.jugar("a7a8")


# ---------- FEN ----------

@pytest.mark.parametrize("fen", [
    FEN_INICIAL,
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
    "r3k2r/8/8/8/8/8/8/R3K2R b Kq - 12 30",
])
def test_fen_ida_y_vuelta(fen):
    assert Game.desde_fen(fen).fen() == fen


def test_desde_fen_lee_turno_y_contadores():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R b Kq - 12 30")
    assert game.turno == BLACK
    assert game.derechos_enroque == {"K", "q"}
    assert game.medios_movimientos == 12
    assert game.numero_jugada == 30


@pytest.mark.parametrize("fen", [
    "",
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1",                 # faltan filas
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN w KQkq - 0 1",         # fila corta
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNX w KQkq - 0 1",        # pieza rara
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1",        # turno malo
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkz - 0 1",        # enroque malo
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq z9 0 1",       # al paso malo
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - x 1",        # contador malo
])
def test_fen_invalido_lanza_error(fen):
    with pytest.raises(InvalidFenError):
        Game.desde_fen(fen)


# ---------- copy ----------

def test_copy_es_independiente():
    game = Game()
    game.jugar("e2e4")
    copia = game.copy()
    copia.jugar("e7e5")
    copia.jugar("g1f3")
    assert game.fen() == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    assert len(game.historial) == 1
    assert len(copia.historial) == 3


def test_copy_no_comparte_derechos_ni_repeticiones():
    game = Game.desde_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    copia = game.copy()
    copia.jugar("e1e2")
    assert game.derechos_enroque == {"K", "Q", "k", "q"}
    assert copia.derechos_enroque == {"k", "q"}


def test_copy_conserva_el_resultado():
    game = Game()
    jugar_todas(game, "f2f3", "e7e5", "g2g4", "d8h4")
    assert game.copy().resultado == RESULTADO_NEGRAS


# ---------- jugada_desde_texto ----------

def test_jugada_desde_texto():
    assert jugada_desde_texto("e2e4") == Move(sq("e2"), sq("e4"))
    assert jugada_desde_texto(" E7E8Q ") == Move(sq("e7"), sq("e8"), QUEEN)
    assert jugada_desde_texto("a2a1n").promocion == KNIGHT


@pytest.mark.parametrize("texto", ["", "e2", "e2e4e5", "e2e4k", "e2e4 q"])
def test_jugada_desde_texto_invalida(texto):
    with pytest.raises(InvalidMoveError):
        jugada_desde_texto(texto)
