import time

from chess.bots import BOTS, MonteCarloBot, RandomBot
from chess.game import Game


def bot(**opciones):
    """Un bot repetible: se limita por iteraciones (no por tiempo) y con semilla."""
    opciones.setdefault("iteraciones", 300)
    return MonteCarloBot(seed=1, **opciones)


def test_esta_en_el_catalogo():
    assert BOTS["montecarlo"] is MonteCarloBot
    assert isinstance(BOTS["montecarlo"](), MonteCarloBot)


def test_elige_una_jugada_legal():
    game = Game()
    assert bot().choose_move(game) in game.jugadas_legales()


def test_no_modifica_la_partida():
    game = Game()
    fen = game.fen()
    bot().choose_move(game)
    assert game.fen() == fen


def test_con_la_misma_semilla_juega_igual():
    assert bot().choose_move(Game()) == bot().choose_move(Game())


def test_con_una_sola_jugada_legal_la_juega():
    # Rey negro en h8 acorralado: solo puede ir a g8.
    game = Game.desde_fen("7k/8/6K1/8/8/8/8/R7 b - - 0 1")
    assert len(game.jugadas_legales()) == 1
    assert bot().choose_move(game) == game.jugadas_legales()[0]


def test_da_mate_en_una():
    # Mate del loco: las negras ganan con Dd8-h4.
    game = Game.desde_fen("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2")
    assert str(bot(iteraciones=10).choose_move(game)) == "d8h4"


def test_captura_una_dama_sin_defender():
    # La dama negra en d5 esta sin defender y el caballo blanco la ataca.
    game = Game.desde_fen("4k3/8/8/3q4/8/2N5/8/4K3 w - - 0 1")
    assert str(bot().choose_move(game)) == "c3d5"


def test_no_deja_que_le_den_mate_en_una():
    # Mate del pastor: las blancas amenazan Dxf7#. Sea cual sea la jugada elegida,
    # las blancas no pueden dar mate en la siguiente.
    game = Game.desde_fen("r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3")
    jugada = bot(iteraciones=500).choose_move(game)
    despues = game.copy()
    despues.jugar(jugada)
    for respuesta in despues.jugadas_legales():
        siguiente = despues.copy()
        siguiente.jugar(respuesta)
        assert not (siguiente.esta_terminada() and siguiente.ganador() == "white")


def test_gana_al_aleatorio():
    game = Game()
    mc, azar = bot(iteraciones=60), RandomBot(seed=2)
    while not game.esta_terminada() and len(game.historial) < 120:
        jugador = mc if game.turno == "white" else azar
        game.jugar(jugador.choose_move(game.copy()))
    assert game.ganador() in ("white", None)


def test_respeta_el_limite_de_tiempo():
    inicio = time.perf_counter()
    MonteCarloBot(tiempo=0.2, seed=1).choose_move(Game())
    assert time.perf_counter() - inicio < 1.0
