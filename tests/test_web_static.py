"""Tests del puente Python de la web estatica (web_static/bridge.py)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web_static"))

import bridge  # noqa: E402


def estado(texto):
    return json.loads(texto)


def test_la_lista_de_bots_viene_del_catalogo():
    assert "aleatorio" in estado(bridge.bots())


def test_partida_nueva():
    s = estado(bridge.nueva("white", "aleatorio"))
    assert s["turno"] == "white"
    assert len(s["legales"]) == 20
    assert s["casillas"][4] == "K" and s["casillas"][60] == "k"
    assert s["historial"] == []


def test_jugar_y_respuesta_del_bot():
    bridge.nueva("white", "aleatorio")
    s = estado(bridge.jugar("e2e4"))
    assert s["historial"] == ["e4"]
    assert s["turno"] == "black"
    s = estado(bridge.mover_bot())
    assert len(s["historial"]) == 2 and s["turno"] == "white"


def test_jugada_ilegal_da_error():
    bridge.nueva("white", "aleatorio")
    with pytest.raises(ValueError):
        bridge.jugar("e2e5")


def test_no_se_puede_jugar_fuera_de_turno():
    bridge.nueva("black", "aleatorio")
    with pytest.raises(ValueError):
        bridge.jugar("e7e5")


def test_deshacer_quita_tu_jugada_y_la_del_bot():
    bridge.nueva("white", "aleatorio")
    bridge.jugar("e2e4")
    bridge.mover_bot()
    s = estado(bridge.deshacer())
    assert s["historial"] == [] and s["turno"] == "white"


def test_notacion_de_jaque_mate_y_promocion():
    bridge.nueva("white", "aleatorio")
    for jugada in ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6"]:
        bridge._game.jugar(jugada)
    bridge._sans = []
    s = estado(bridge.jugar("h5f7"))
    assert s["historial"] == ["Qxf7#"]
    assert s["terminada"] and s["ganador"] == "white"

    s = estado(bridge.desde_fen("7k/P7/8/8/8/8/8/K7 w - - 0 1", "white", "aleatorio"))
    assert "a7a8q" in s["legales"] and "a7a8n" in s["legales"]
    assert estado(bridge.jugar("a7a8q"))["historial"] == ["a8=Q+"]


def test_enroque():
    bridge.desde_fen("4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1", "white", "aleatorio")
    assert estado(bridge.jugar("e1g1"))["historial"] == ["O-O"]


def test_dos_jugadores_se_turnan_sin_bot():
    s = estado(bridge.nueva("white", "humano"))
    assert s["dos"] and s["bot"] is None and s["humano"] == "white"
    s = estado(bridge.jugar("e2e4"))
    assert s["turno"] == "black" and s["humano"] == "black"   # ahora juegan negras
    s = estado(bridge.jugar("e7e5"))
    assert s["historial"] == ["e4", "e5"] and s["orientacion"] == "white"
    assert estado(bridge.mover_bot())["historial"] == ["e4", "e5"]  # no hay bot
    assert estado(bridge.deshacer())["historial"] == ["e4"]         # quita 1 jugada
