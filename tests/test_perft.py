"""
Tests "perft": validan TODO el generador de jugadas a la vez.

Perft cuenta cuantas posiciones distintas se pueden alcanzar jugando
N jugadas legales seguidas desde una posicion. Para unas posiciones muy
conocidas, el numero correcto esta publicado (chessprogramming.org).
Si nuestro motor da exactamente esos numeros, las reglas de movimiento,
jaque, enroque, captura al paso y promocion son correctas.
"""

import pytest

from chess.game import Game


def perft(game, profundidad):
    jugadas = game.jugadas_legales()
    if profundidad == 1:
        return len(jugadas)
    total = 0
    for jugada in jugadas:
        copia = game.copy()
        copia.jugar(jugada)
        total += perft(copia, profundidad - 1)
    return total


POSICIONES = [
    # (nombre, FEN, profundidad, nodos esperados)
    ("inicial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 1, 20),
    ("inicial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 2, 400),
    ("inicial", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3, 8902),
    # Kiwipete: muchos enroques, clavadas y capturas.
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 1, 48),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),
    # Final de torres y peones: captura al paso y jaques descubiertos.
    ("final", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),
    ("final", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 4, 43238),
    # Promociones y enroques bajo ataque.
    ("promociones", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 3, 9467),
    ("promociones", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 2, 1486),
]


@pytest.mark.parametrize("nombre, fen, profundidad, esperado", POSICIONES)
def test_perft(nombre, fen, profundidad, esperado):
    assert perft(Game.desde_fen(fen), profundidad) == esperado
