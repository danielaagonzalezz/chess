import json
import sys
from pathlib import Path

import pytest

from chess.board import Board, create_initial_board
from chess.bots import BOTS, MLBot
from chess.bots.evaluacion_ml import (
    EvaluadorAprendido, LETRAS, RUTA_PESOS, TIPOS, cargar_pesos,
)
from chess.game import Game
from chess.pieces import BLACK, WHITE, Piece, square_from_algebraic as sq


def espejo(board):
    """El mismo tablero con los colores cambiados y dado la vuelta (las blancas pasan a ser negras)."""
    otro = Board()
    for i, pieza in enumerate(board.squares):
        if pieza is not None:
            color = BLACK if pieza.color == WHITE else WHITE
            otro.squares[i ^ 56] = Piece(pieza.piece_type, color)
    return otro


# ---------- Los pesos ----------

def test_el_fichero_de_pesos_tiene_el_formato_correcto():
    mg, eg = cargar_pesos()
    for fase in (mg, eg):
        assert set(fase) == set(LETRAS.values())
        for letra in LETRAS.values():
            assert len(fase[letra]) == 64
            assert all(isinstance(x, int) for x in fase[letra])


def test_el_material_aprendido_es_razonable():
    # El entrenamiento fija el valor medio del material: dama > torre > alfil/caballo > peon.
    mg, _ = cargar_pesos()
    media = {letra: sum(mg[letra]) / 64 for letra in "PNBRQ"}
    assert media["Q"] > media["R"] > media["B"] > media["P"] > 0
    assert media["R"] > media["N"] > media["P"]


# ---------- La evaluacion ----------

def test_posicion_inicial_igualada():
    assert EvaluadorAprendido().evaluar(create_initial_board()) == 0


def test_la_evaluacion_es_simetrica_entre_colores():
    evaluador = EvaluadorAprendido()
    for fen in [
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/5k2/8/8/3K4/8/4P3/8 w - - 0 1",
    ]:
        board = Game.desde_fen(fen).board
        assert evaluador.evaluar(board) == -evaluador.evaluar(espejo(board))


def test_tener_mas_material_es_mejor():
    evaluador = EvaluadorAprendido()
    board = create_initial_board()
    board.remove_piece(sq("b8"))          # a las negras les falta un caballo
    assert evaluador.evaluar(board) > 100
    board = create_initial_board()
    board.remove_piece(sq("d1"))          # a las blancas les falta la dama
    assert evaluador.evaluar(board) < -500


def test_la_fase_va_de_24_a_0():
    evaluador = EvaluadorAprendido()
    assert evaluador.fase(create_initial_board()) == 24
    solo_reyes = Game.desde_fen("8/8/4k3/8/8/4K3/8/8 w - - 0 1").board
    assert evaluador.fase(solo_reyes) == 0


def test_el_entrenamiento_el_evaluador_y_el_motor_dan_lo_mismo():
    """
    Tres formas de calcular la misma evaluacion: el producto escalar de
    training/entrenar.py, la clase de referencia EvaluadorAprendido y el
    evaluador del motor rapido que usa el bot.
    """
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "training"))
    import entrenar
    from chess.bots.caracteristicas import N_EXTRAS
    from chess.bots.evaluacion_ml import a_codigos, cargar_extras
    from chess.bots.motor_rapido import Buscador, Posicion, tablas_de_pesos

    mg, eg = cargar_pesos()
    ex_mg, ex_eg = cargar_extras()
    pesos = np.zeros((2, 6, 64))
    for i, tipo in enumerate(TIPOS):
        pesos[0, i] = mg[LETRAS[tipo]]
        pesos[1, i] = eg[LETRAS[tipo]]
    pesos = np.concatenate([pesos.reshape(768), ex_mg, ex_eg]).astype(float)

    evaluador = EvaluadorAprendido()
    buscador = Buscador(pesos_extras=(ex_mg, ex_eg))
    tablas = tablas_de_pesos(mg, eg)
    for fen in [
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "8/5k2/8/8/3K4/8/4P3/8 w - - 0 1",
        "r3k2r/pp3ppp/2n1b3/3q4/3P4/2N2N2/PP3PPP/R2QR1K1 b kq - 0 1",
        "8/1P3pk1/6p1/8/5P2/2p3P1/1r4K1/R7 w - - 0 1",
    ]:
        game = Game.desde_fen(fen)
        fila = np.array([a_codigos(game.board)], dtype=np.int8)
        turno = np.array([1 if game.turno == WHITE else 0])
        del_entrenamiento = (entrenar.construir_caracteristicas(fila, turno) @ pesos)[0]
        de_referencia = evaluador.evaluar(game.board, game.turno)
        pos = Posicion.desde_fen(fen, tablas)
        del_motor = buscador.evaluar(pos)
        if game.turno != WHITE:
            del_motor = -del_motor
        assert abs(de_referencia - del_entrenamiento) < 1.0
        assert abs(del_motor - del_entrenamiento) < 2.0


def test_los_pesos_incluyen_las_caracteristicas_contadas():
    from chess.bots.caracteristicas import N_EXTRAS
    from chess.bots.evaluacion_ml import cargar_extras
    mg, eg = cargar_extras()
    assert len(mg) == len(eg) == N_EXTRAS
    # Lo basico del ajedrez, aprendido de las partidas: peones doblados y
    # aislados son malos; tener el turno y la torre en columna abierta, buenos.
    assert mg[1] < 0 and mg[2] < 0
    assert mg[14] > 0 and mg[9] > 0


# ---------- El bot ----------

def test_ml_bot_elige_una_jugada_legal():
    game = Game()
    bot = MLBot(profundidad=2)
    assert bot.choose_move(game) in game.jugadas_legales()


def test_ml_bot_toma_una_dama_gratis():
    # Las blancas pueden capturar la dama negra sin que les cueste nada.
    game = Game.desde_fen("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1")
    jugada = MLBot(profundidad=2).choose_move(game)
    assert str(jugada.destino) == "d5"


def test_ml_bot_da_mate_en_uno():
    game = Game.desde_fen("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1")
    bot = MLBot(profundidad=2)
    game.jugar(bot.choose_move(game.copy()))
    assert game.esta_terminada() and game.ganador() == WHITE


def test_ml_bot_esta_en_el_catalogo():
    assert "ml-2" in BOTS and BOTS["ml-2"]().name == "ml-2"
