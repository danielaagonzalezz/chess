"""Tests del bot dama-segura: que ve lo que tiene que ver."""

import time

from chess.bots import BOTS, DamaSegura
from chess.game import Game


def elige(fen, tiempo=0.5):
    """La jugada que elige el bot en la posicion 'fen', como texto (p. ej. 'a1a8')."""
    return str(DamaSegura(tiempo=tiempo).choose_move(Game.desde_fen(fen)))


def test_esta_en_el_catalogo():
    assert isinstance(BOTS["dama-segura"](), DamaSegura)


def test_da_mate_en_una():
    # Mate del pasillo: la torre llega a la octava fila y el rey no puede salir.
    assert elige("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1") == "a1a8"


def test_come_una_dama_sin_defender():
    assert elige("4k3/8/8/3q4/8/4N3/8/4K3 w - - 0 1") == "e3d5"


def test_no_come_un_peon_defendido_con_la_dama():
    # Dxd5 gana un peon pero el peon de e6 se come la dama.
    assert elige("4k3/8/4p3/3p4/8/8/8/3QK3 w - - 0 1") != "d1d5"


def test_no_come_un_peon_defendido_con_la_torre():
    # Lo mismo con la torre: proteger solo la dama no basta.
    assert elige("4k3/8/4p3/3p4/8/8/8/3RK3 w - - 0 1") != "d1d5"


def test_respeta_el_tiempo():
    inicio = time.time()
    DamaSegura(tiempo=0.5).choose_move(Game())
    assert time.time() - inicio < 2


def test_remata_con_dama_y_rey():
    # Dama y rey contra rey: tiene que dar mate antes de 60 medias jugadas
    # (el limite del torneo en GitHub). El rival es el propio bot.
    game = Game.desde_fen("8/8/8/4k3/8/8/8/3QK3 w - - 0 1")
    bot = DamaSegura(tiempo=0.3)
    while not game.esta_terminada() and len(game.historial) < 60:
        game.jugar(bot.choose_move(game.copy()))
    assert game.ganador() == "white"