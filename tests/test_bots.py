import pytest

from chess.bots import BOTS, Bot, RandomBot
from chess.game import Game


def jugar_partida(blancas, negras, max_jugadas=2000):
    """Hace jugar a dos bots entre si hasta que la partida termine."""
    game = Game()
    while not game.esta_terminada() and len(game.historial) < max_jugadas:
        bot = blancas if game.turno == "white" else negras
        game.jugar(bot.choose_move(game.copy()))
    return game


# ---------- La clase base ----------

def test_bot_no_se_puede_instanciar_sin_choose_move():
    with pytest.raises(TypeError):
        Bot()


def test_un_bot_nuevo_solo_necesita_choose_move():
    class PrimerBot(Bot):
        name = "primero"

        def choose_move(self, game):
            return game.jugadas_legales()[0]

    game = Game()
    jugada = PrimerBot().choose_move(game)
    assert jugada in game.jugadas_legales()


# ---------- RandomBot ----------

def test_random_bot_elige_una_jugada_legal():
    game = Game()
    bot = RandomBot(seed=1)
    for _ in range(30):
        assert bot.choose_move(game) in game.jugadas_legales()


def test_random_bot_con_la_misma_semilla_juega_igual():
    a = RandomBot(seed=42).choose_move(Game())
    b = RandomBot(seed=42).choose_move(Game())
    assert a == b


def test_random_bot_no_modifica_la_partida():
    game = Game()
    fen = game.fen()
    RandomBot(seed=3).choose_move(game)
    assert game.fen() == fen


# ---------- Catalogo ----------

def test_el_catalogo_contiene_bots_validos():
    assert len(BOTS) >= 1
    for nombre, clase in BOTS.items():
        bot = clase()
        assert isinstance(bot, Bot)
        assert bot.name == nombre


# ---------- Partidas completas entre bots ----------

@pytest.mark.parametrize("semilla", range(5))
def test_partida_aleatoria_termina_sin_errores(semilla):
    game = jugar_partida(RandomBot(seed=semilla), RandomBot(seed=semilla + 100))
    assert game.esta_terminada()
    assert game.resultado in ("1-0", "0-1", "1/2-1/2")
    assert game.motivo is not None
