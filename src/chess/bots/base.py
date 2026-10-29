"""
La clase base de todos los bots.

Un bot es un jugador automatico. Para crear uno nuevo solo hay que:

  1. Heredar de Bot.
  2. Poner un nombre en 'name'.
  3. Escribir el metodo choose_move, que recibe la partida y devuelve la
     jugada que quiere hacer.

No hace falta tocar el codigo del juego: el bot solo MIRA la partida
(game) y devuelve una jugada.

Ejemplo (un bot que siempre elige la primera jugada legal):

    class PrimerBot(Bot):
        name = "primero"

        def choose_move(self, game):
            return game.jugadas_legales()[0]
"""

from abc import ABC, abstractmethod


class Bot(ABC):
    """Un jugador automatico de ajedrez."""

    # Nombre con el que aparece el bot en la interfaz y el torneo.
    name = "bot"

    @abstractmethod
    def choose_move(self, game):
        """
        Elige una jugada para la partida 'game'.

        - Recibe una copia de la partida: se puede probar lo que se quiera
          sobre ella (game.jugar(...)) sin afectar a la partida real.
        - Debe devolver una Move que este en game.jugadas_legales().
        - Solo se llama cuando la partida no ha terminado, asi que siempre
          hay al menos una jugada legal.
        """
        raise NotImplementedError
