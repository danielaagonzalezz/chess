"""Excepciones personalizadas para el motor de ajedrez (chessarena)."""


class ChessError(Exception):
    """Excepción base para cualquier error del motor de ajedrez."""


class InvalidSquareError(ChessError):
    """Se lanza al crear o acceder a una casilla fuera del tablero (fuera de a1-h8)."""


class InvalidMoveError(ChessError):
    """Se lanza cuando un movimiento es ilegal según las reglas del ajedrez."""


class GameOverError(ChessError):
    """Se lanza al intentar hacer un movimiento en una partida ya finalizada."""
