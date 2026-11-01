"""
Tests automaticos de la plataforma de bots.

- Todos los bots de BOTS se validan solos: quien anade un bot al catalogo
  no tiene que escribir ningun test para que se compruebe.
- Se comprueba tambien que la validacion detecta los bots que hacen mal las
  cosas (jugada ilegal, excepcion, tipo equivocado...).
"""

import pytest

from chess.bots import BOTS, Bot, RandomBot
from chess.bots.validacion import (
    POSICIONES, BotInvalidoError, main, validar_bot,
)
from chess.game import Game
from chess.move import Move
from chess.pieces import square_from_algebraic as sq


# ---------- Todos los bots del catalogo ----------

@pytest.mark.parametrize("nombre", list(BOTS))
def test_los_bots_del_catalogo_cumplen_el_contrato(nombre):
    # Una sola jugada propia por color: basta para pillar errores y los
    # bots con limite de tiempo no alargan demasiado los tests.
    validar_bot(BOTS[nombre](), jugadas_de_partida=1)


def test_las_posiciones_de_prueba_son_validas():
    for descripcion, fen in POSICIONES:
        game = Game.desde_fen(fen)
        assert game.jugadas_legales(), descripcion


# ---------- La validacion detecta bots incorrectos ----------

class _BotBase(Bot):
    name = "malo"

    def choose_move(self, game):
        return game.jugadas_legales()[0]


def test_un_bot_correcto_pasa_la_validacion():
    assert isinstance(validar_bot(_BotBase()), Bot)
    validar_bot(RandomBot(seed=0))


def test_detecta_que_no_es_un_bot():
    with pytest.raises(BotInvalidoError, match="heredar"):
        validar_bot(object())


@pytest.mark.parametrize("nombre", ["", "   ", None, 3])
def test_detecta_nombre_invalido(nombre):
    class Sinnombre(_BotBase):
        pass

    Sinnombre.name = nombre
    with pytest.raises(BotInvalidoError, match="name"):
        validar_bot(Sinnombre())


def test_detecta_jugada_ilegal():
    class Tramposo(_BotBase):
        def choose_move(self, game):
            return Move(sq("a1"), sq("a8"))

    with pytest.raises(BotInvalidoError, match="ilegal"):
        validar_bot(Tramposo())


def test_detecta_que_no_devuelve_una_move():
    class Texto(_BotBase):
        def choose_move(self, game):
            return "e2e4"

    with pytest.raises(BotInvalidoError, match="Move"):
        validar_bot(Texto())


def test_detecta_que_devuelve_none():
    class Nada(_BotBase):
        def choose_move(self, game):
            return None

    with pytest.raises(BotInvalidoError, match="Move"):
        validar_bot(Nada())


def test_detecta_excepciones_del_bot():
    class Roto(_BotBase):
        def choose_move(self, game):
            raise RuntimeError("boom")

    with pytest.raises(BotInvalidoError, match="RuntimeError"):
        validar_bot(Roto())


def test_detecta_bots_demasiado_lentos():
    import time

    class Lento(_BotBase):
        def choose_move(self, game):
            time.sleep(0.05)
            return game.jugadas_legales()[0]

    with pytest.raises(BotInvalidoError, match="tardo"):
        validar_bot(Lento(), tiempo_maximo=0.01)


def test_detecta_jugadas_que_no_son_de_la_posicion():
    # Una jugada legal en la posicion inicial pero no en otra.
    class Fija(_BotBase):
        def choose_move(self, game):
            return Move(sq("e2"), sq("e4"))

    with pytest.raises(BotInvalidoError, match="ilegal"):
        validar_bot(Fija())


def test_un_bot_puede_modificar_su_copia_sin_afectar_a_la_partida():
    class Curioso(_BotBase):
        def choose_move(self, game):
            jugada = game.jugadas_legales()[0]
            game.jugar(jugada)  # solo toca su copia
            return jugada

    validar_bot(Curioso())


# ---------- Linea de comandos ----------

def test_cli_valida_un_bot_del_catalogo(capsys):
    assert main(["aleatorio"]) == 0
    assert "OK" in capsys.readouterr().out


def test_cli_sin_argumentos_muestra_la_ayuda(capsys):
    assert main([]) == 2
    assert "validacion" in capsys.readouterr().out


def test_cli_informa_de_un_bot_que_falla(capsys, monkeypatch):
    class Roto(_BotBase):
        name = "roto"

        def choose_move(self, game):
            raise ValueError("x")

    monkeypatch.setitem(BOTS, "roto", Roto)
    assert main(["roto"]) == 1
    assert "FALLA" in capsys.readouterr().out


def test_cli_con_un_nombre_desconocido_sale_con_error():
    with pytest.raises(SystemExit):
        main(["no-existe"])
