"""
Tests de la interfaz web (web/app.py) con el simulador de Streamlit.

AppTest ejecuta la app sin abrir un navegador: podemos "pulsar botones"
y mirar el estado de la partida. Si Streamlit no esta instalado, estos
tests se saltan (se instala con: python -m pip install -e ".[web]").
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from chess.game import Game  # noqa: E402
from chess.pieces import (  # noqa: E402
    Piece, square_from_algebraic, BLACK, KNIGHT, PAWN, WHITE,
)

RUTA_APP = str(Path(__file__).resolve().parents[1] / "web" / "app.py")


def sq(texto):
    return square_from_algebraic(texto)


def abrir_app():
    return AppTest.from_file(RUTA_APP, default_timeout=30).run()


def pulsar(at, *casillas):
    for casilla in casillas:
        at.button(key="sq_" + casilla).click().run()


def poner_posicion(at, fen, humano=WHITE):
    at.session_state["game"] = Game.desde_fen(fen)
    at.session_state["humano"] = humano
    at.session_state["seleccion"] = None
    at.session_state["mensaje"] = ""
    at.run()


def test_la_app_abre_sin_errores_y_dibuja_64_casillas():
    at = abrir_app()
    assert not at.exception
    casillas = [b for b in at.button if b.key and b.key.startswith("sq_")]
    assert len(casillas) == 64


def test_jugar_e2e4_y_el_bot_responde():
    at = abrir_app()
    pulsar(at, "e2", "e4")
    game = at.session_state["game"]
    assert not at.exception
    assert str(game.historial[0]) == "e2e4"
    assert len(game.historial) == 2          # tu jugada y la respuesta del bot
    assert game.turno == WHITE                # vuelve a ser tu turno


def test_pulsar_una_pieza_la_selecciona_y_otra_vez_la_deselecciona():
    at = abrir_app()
    pulsar(at, "e2")
    assert at.session_state["seleccion"] == sq("e2")
    pulsar(at, "e2")
    assert at.session_state["seleccion"] is None


def test_cambiar_de_pieza_seleccionada():
    at = abrir_app()
    pulsar(at, "e2", "d2")
    assert at.session_state["seleccion"] == sq("d2")


def test_jugada_ilegal_muestra_mensaje_y_no_cambia_nada():
    at = abrir_app()
    pulsar(at, "e2", "e5")
    assert at.session_state["mensaje"] == "Esa jugada no es legal."
    assert at.session_state["game"].historial == []


def test_no_se_puede_elegir_una_pieza_del_rival():
    at = abrir_app()
    pulsar(at, "e7")
    assert at.session_state["seleccion"] is None
    assert "tuya" in at.session_state["mensaje"]


def test_jugando_con_negras_el_bot_mueve_primero():
    at = abrir_app()
    at.sidebar.radio(key="color_elegido").set_value("negras").run()
    at.sidebar.button[0].click().run()          # "Empezar partida"
    game = at.session_state["game"]
    assert at.session_state["humano"] == BLACK
    assert len(game.historial) == 1             # ya ha movido el bot (blancas)
    assert game.turno == BLACK


def test_promocion_a_la_pieza_elegida():
    at = abrir_app()
    poner_posicion(at, "8/P6k/8/8/8/8/8/K7 w - - 0 1")
    at.sidebar.selectbox(key="promocion").select("Caballo").run()
    pulsar(at, "a7", "a8")
    game = at.session_state["game"]
    assert game.board.get_piece(sq("a8")) == Piece(KNIGHT, WHITE)


def test_promocion_por_defecto_es_dama():
    at = abrir_app()
    poner_posicion(at, "8/P6k/8/8/8/8/8/K7 w - - 0 1")
    pulsar(at, "a7", "a8")
    game = at.session_state["game"]
    assert str(game.historial[0]) == "a7a8q"


def test_ganar_muestra_el_mensaje_de_victoria():
    at = abrir_app()
    poner_posicion(at, "7k/8/6K1/8/8/8/8/R7 w - - 0 1")
    pulsar(at, "a1", "a8")
    assert at.session_state["game"].esta_terminada()
    assert len(at.success) == 1
    assert "ganado" in at.success[0].value


def test_perder_muestra_el_mensaje_de_derrota():
    at = abrir_app()
    # Posicion de jaque mate contra las negras (el humano).
    poner_posicion(at, "R6k/8/6K1/8/8/8/8/8 b - - 0 1", humano=BLACK)
    assert len(at.error) == 1
    assert "perdido" in at.error[0].value


def test_no_se_puede_mover_con_la_partida_terminada():
    at = abrir_app()
    poner_posicion(at, "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", humano=BLACK)  # ahogado
    assert at.session_state["game"].esta_terminada()
    pulsar(at, "h8")
    assert at.session_state["seleccion"] is None


def test_nueva_partida_reinicia_el_tablero():
    at = abrir_app()
    pulsar(at, "e2", "e4")
    at.sidebar.button[0].click().run()
    assert at.session_state["game"].historial == []


def test_jugar_contra_minimax():
    at = abrir_app()
    at.sidebar.selectbox(key="bot_elegido").select("minimax-2").run()
    at.sidebar.button[0].click().run()          # "Empezar partida" con ese rival
    pulsar(at, "e2", "e4")
    game = at.session_state["game"]
    assert not at.exception
    assert at.session_state["bot"].name == "minimax-2"
    assert len(game.historial) == 2
