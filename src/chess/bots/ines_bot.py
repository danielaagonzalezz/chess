"""InesBot: learned evaluation, opening book and a longer search budget."""

from chess.bots.ml_bot import MLBot

TIEMPO_POR_JUGADA = 4.0
SEMILLA_LIBRO = 2026


class InesBot(MLBot):
    """MLBot configured to search longer and use a reproducible opening book."""

    name = "ines"

    def __init__(self):
        super().__init__(
            tiempo=TIEMPO_POR_JUGADA,
            name=self.name,
            libro=True,
            seed=SEMILLA_LIBRO,
        )
