import random
import time

import pytest

from chess.bots.evaluacion_ml import cargar_pesos
from chess.bots.ml_bot import MLBot, hash_de_clave
from chess.bots.motor_rapido import Buscador, Posicion, jugada_a_texto, tablas_de_pesos
from chess.game import Game

TABLAS = tablas_de_pesos(*cargar_pesos())
INICIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Posiciones clasicas para comprobar un generador de jugadas (chessprogramming.org/Perft_Results)
# con enroques, captura al paso, promociones y clavadas.
PERFT = [
    (INICIAL, [20, 400, 8902]),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", [48, 2039, 97862]),
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", [14, 191, 2812, 43238]),
    ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", [6, 264, 9467]),
    ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", [44, 1486, 62379]),
]


# ---------- Las reglas del motor rapido ----------

@pytest.mark.parametrize("fen, esperados", PERFT)
def test_perft(fen, esperados):
    pos = Posicion.desde_fen(fen, TABLAS)
    for profundidad, esperado in enumerate(esperados, start=1):
        assert pos.perft(profundidad) == esperado


def test_motor_y_game_coinciden_en_partidas_aleatorias():
    """En cada posicion: mismas jugadas legales, mismo hash, y deshacer lo deja todo igual."""
    azar = random.Random(7)
    for _ in range(8):
        game = Game()
        pos = Posicion.desde_fen(game.fen(), TABLAS)
        for _ in range(120):
            if game.esta_terminada():
                break
            assert sorted(jugada_a_texto(m) for m in pos.legales()) == \
                sorted(str(m) for m in game.jugadas_legales())
            assert pos.h == pos.calcular_hash() == hash_de_clave(game.clave_posicion())
            jugada = azar.choice(game.jugadas_legales())
            game.jugar(jugada)
            pos.hacer(next(m for m in pos.legales() if jugada_a_texto(m) == str(jugada)))
        while pos.pila:
            pos.deshacer()
        inicial = Posicion.desde_fen(INICIAL, TABLAS)
        assert (pos.b, pos.h, pos.mg, pos.eg, pos.phase, pos.rights) == \
            (inicial.b, inicial.h, inicial.mg, inicial.eg, inicial.phase, inicial.rights)


def test_la_jugada_nula_se_deshace():
    pos = Posicion.desde_fen("r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4", TABLAS)
    antes = (list(pos.b), pos.h, pos.side, pos.ep, pos.half)
    pos.hacer_nulo()
    assert pos.side == 1
    pos.deshacer_nulo()
    assert (list(pos.b), pos.h, pos.side, pos.ep, pos.half) == antes


# ---------- La busqueda ----------

def buscar(fen, **opciones):
    pos = Posicion.desde_fen(fen, TABLAS)
    buscador = Buscador(**opciones)
    return jugada_a_texto(buscador.buscar(pos)), buscador


def test_da_mate_en_uno():
    jugada, buscador = buscar("6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1", profundidad=3, tiempo=5)
    assert jugada == "a1a8"
    assert buscador.valor > 90000


def test_da_mate_en_dos():
    # Dama y rey contra rey: mate forzado en dos jugadas (mate en el tercer ply).
    for fen, primera in [
        ("5Q2/8/8/8/1K6/8/8/k7 w - - 0 1", "b4b3"),
        ("2K5/k7/8/8/8/8/8/5Q2 w - - 0 1", "f1f6"),
    ]:
        jugada, buscador = buscar(fen, profundidad=4, tiempo=10)
        assert jugada == primera
        assert buscador.valor == 100000 - 3


def test_toma_la_dama_gratis():
    jugada, _ = buscar("4k3/8/8/3q4/8/8/8/3RK3 w - - 0 1", profundidad=3, tiempo=5)
    assert jugada == "d1d5"


def test_no_regala_la_dama():
    # La dama blanca puede tomar un peon defendido; no debe hacerlo.
    jugada, _ = buscar("4k3/8/2p5/3p4/8/8/3Q4/4K3 w - - 0 1", profundidad=4, tiempo=5)
    assert jugada != "d2d5"


def test_no_ahoga_cuando_va_ganando():
    # Con dama contra rey hay jugadas que ahogan (tablas); las evita.
    game = Game.desde_fen("7k/8/5K2/8/8/8/8/6Q1 w - - 0 1")
    jugada, _ = buscar(game.fen(), profundidad=4, tiempo=5)
    game.jugar(jugada)
    assert game.resultado != "1/2-1/2"


def test_respeta_el_limite_de_tiempo():
    inicio = time.perf_counter()
    buscar("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", tiempo=0.4)
    assert time.perf_counter() - inicio < 1.5


def test_con_profundidad_fija_es_determinista():
    fen = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    assert buscar(fen, profundidad=4, tiempo=30)[0] == buscar(fen, profundidad=4, tiempo=30)[0]


def test_ve_la_repeticion_como_tablas_y_la_evita_si_va_ganando():
    fen = "4k3/8/8/8/8/8/R7/R3K3 w - - 0 1"
    pos = Posicion.desde_fen(fen, TABLAS)
    primera = Buscador(profundidad=3, tiempo=10).buscar(pos)
    pos.hacer(primera)
    hash_tras_primera = pos.h
    pos.deshacer()
    # Si esa posicion ya ocurrio en la partida, la jugada que la repite vale "tablas" y se descarta.
    segunda = Buscador(profundidad=3, tiempo=10).buscar(pos, {hash_tras_primera: 1})
    assert segunda != primera


# ---------- El bot completo ----------

def jugar(blancas, negras, maximo=400):
    game = Game()
    while not game.esta_terminada() and len(game.historial) < maximo:
        bot = blancas if game.turno == "white" else negras
        game.jugar(bot.choose_move(game.copy()))
    return game


def test_ml_bot_gana_a_un_bot_aleatorio():
    from chess.bots import RandomBot
    for semilla in range(2):
        game = jugar(MLBot(profundidad=3), RandomBot(seed=semilla))
        assert game.ganador() == "white"
        game = jugar(RandomBot(seed=semilla), MLBot(profundidad=3))
        assert game.ganador() == "black"
