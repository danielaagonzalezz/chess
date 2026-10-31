"""
Libro de aperturas aprendido de partidas reales de Lichess.

El fichero libro_aperturas.json lo genera training/crear_libro.py: para cada
posicion muy repetida de las primeras jugadas, las jugadas que mas se
hicieron y cuantas veces. Aqui se usa para jugar la apertura: se elige una
jugada al azar con probabilidad proporcional a lo frecuente que fue, de modo
que el bot juega aperturas "de verdad" y no repite siempre la misma partida.

Si la posicion no esta en el libro, no devuelve nada y el bot piensa.
"""

import json
import random
from pathlib import Path

from chess.move import jugada_desde_texto

RUTA_LIBRO = Path(__file__).with_name("libro_aperturas.json")


class Libro:
    """Jugadas de apertura frecuentes, por posicion."""

    def __init__(self, entradas=None, seed=None):
        if entradas is None:
            with open(RUTA_LIBRO, encoding="utf-8") as f:
                entradas = json.load(f)
        self.entradas = entradas
        self._azar = random.Random(seed)

    @staticmethod
    def clave(game):
        """Colocacion + turno + enroques: los tres primeros campos del FEN."""
        return " ".join(game.fen().split()[:3])

    def __len__(self):
        return len(self.entradas)

    def jugadas(self, game):
        """[(Move, veces)] de las jugadas del libro para esta posicion (solo las legales)."""
        legales = game.jugadas_legales()
        resultado = []
        for texto, veces in self.entradas.get(self.clave(game), []):
            jugada = jugada_desde_texto(texto)
            if jugada in legales:
                resultado.append((jugada, veces))
        return resultado

    def elegir(self, game):
        """Una jugada del libro (al azar, ponderada por frecuencia) o None si no hay."""
        opciones = self.jugadas(game)
        if not opciones:
            return None
        jugadas = [j for j, _ in opciones]
        pesos = [n for _, n in opciones]
        return self._azar.choices(jugadas, weights=pesos)[0]
