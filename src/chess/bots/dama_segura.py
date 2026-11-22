"""
Bot "dama-segura": minimax con poda alfa-beta sobre el material y la posicion.

Autores: equipo de Tic-Tac-Toe Arena (Antonio Orteu, Alvaro Domingo y Maria Sanz).

LA IDEA
-------
Cada pieza vale puntos: peon 5, caballo 15, alfil 16, torre 25, dama 45.
Antes de mover, el bot se pregunta: "despues de la mejor respuesta del
rival (y de la mia, y de la suya...), cuanto material me queda?". Elige la
jugada que deja mejor resultado en el peor caso (minimax). Asi no regala
ninguna pieza (ni la dama ni las demas) y aprovecha las que el rival deja
sin defender.

  - Jaque mate: vale mas que cualquier material (y cuanto antes, mejor).
  - Tablas (ahogado, repeticion...): valen 0. Si voy ganando, las evito.
  - El rey no tiene valor: en ajedrez nunca se come, la partida acaba antes.

POSICION
--------
Con el material igualado (por ejemplo, en la apertura) todas las jugadas
valdrian lo mismo. Para desempatar se suman premios pequenos, siempre
menores que un peon: caballos y alfiles cerca del centro, peones que
avanzan (sobre todo los centrales) y un castigo a los caballos y alfiles
que siguen sin salir de su primera fila.

PODA ALFA-BETA
--------------
Da el mismo resultado que minimax, pero deja de mirar una rama en cuanto
se sabe que es peor que otra ya vista. Funciona mejor si se prueban
primero las mejores jugadas: por eso se ordenan poniendo delante las
capturas de pieza valiosa con pieza barata.

CAPTURAS AL FINAL (quiescencia)
-------------------------------
Si la busqueda se corta justo despues de que mi torre coma un peon, el
bot creeria que ha ganado un peon sin ver que le comen la torre. Por eso,
al llegar al final, sigue mirando solo capturas hasta que no quede
ninguna.

REMATAR
-------
El torneo corta las partidas largas y las da por tablas, asi que ir
ganando no basta: hay que dar mate. Cuando un bando va muy por delante y
al rival casi no le quedan piezas, se premia empujar al rey rival al borde
del tablero y acercar el rey propio, que es como se dan los mates.

RELOJ
-----
Busca primero a 1 jugada vista, luego a 2, a 3... y cuando se acaba el
tiempo (2 segundos por defecto) juega la mejor jugada de la ultima
busqueda completa. Asi responde a tiempo tambien en la web, que es mas
lenta.
"""

import time

from chess.bots.base import Bot
from chess.pieces import BISHOP, BLACK, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE

VALOR = {PAWN: 5, KNIGHT: 15, BISHOP: 16, ROOK: 25, QUEEN: 45, KING: 0}

# Mayor que cualquier diferencia de material.
MATE = 100000

# Rematar: el rival tiene como mucho una torre (sin contar peones) y yo le
# saco al menos una torre de ventaja.
REMATE_MATERIAL_RIVAL = 25
REMATE_VENTAJA = 25


class SinTiempo(Exception):
    """Se ha acabado el tiempo de esta jugada."""


def _cercania_al_centro(indice):
    """0 en el borde del tablero, 3 en las cuatro casillas centrales."""
    columna, fila = indice % 8, indice // 8
    return 3 - int(max(abs(columna - 3.5), abs(fila - 3.5)))


class DamaSegura(Bot):
    """Minimax con alfa-beta, capturas al final y remate, con limite de tiempo."""

    name = "dama-segura"

    def __init__(self, tiempo=2.0):
        self.tiempo = tiempo

    # -----------------------------------------------------
    # Elegir jugada
    # -----------------------------------------------------

    def choose_move(self, game):
        self._limite = time.time() + self.tiempo
        jugadas = self._ordenar(game, game.jugadas_legales())
        mejor = jugadas[0]
        profundidad = 1
        while True:
            try:
                valor, jugada = self._buscar_raiz(game, jugadas, profundidad)
            except SinTiempo:
                break
            mejor = jugada
            # La proxima vuelta empieza por la mejor jugada de esta.
            jugadas.remove(jugada)
            jugadas.insert(0, jugada)
            if abs(valor) > MATE - 1000:
                break  # ya ve un mate: no hace falta mirar mas
            profundidad += 1
        return mejor

    def _buscar_raiz(self, game, jugadas, profundidad):
        alfa, mejor = -2 * MATE, jugadas[0]
        for jugada in jugadas:
            hijo = game.copy()
            hijo.jugar(jugada)
            valor = -self._minimax(hijo, profundidad - 1, -2 * MATE, -alfa, 1)
            if valor > alfa:
                alfa, mejor = valor, jugada
        return alfa, mejor

    # -----------------------------------------------------
    # Buscar (negamax: el valor siempre es para quien mueve)
    # -----------------------------------------------------

    def _minimax(self, game, profundidad, alfa, beta, ply):
        self._mirar_reloj()
        if game.esta_terminada():
            if game.ganador() is None:
                return 0  # tablas
            return -(MATE - ply)  # me han dado mate: cuanto antes, peor
        if profundidad <= 0:
            return self._capturas(game, alfa, beta, ply)
        for jugada in self._ordenar(game, game.jugadas_legales()):
            hijo = game.copy()
            hijo.jugar(jugada)
            valor = -self._minimax(hijo, profundidad - 1, -beta, -alfa, ply + 1)
            if valor >= beta:
                return valor  # poda: el rival no me dejara llegar aqui
            alfa = max(alfa, valor)
        return alfa

    def _capturas(self, game, alfa, beta, ply):
        """Quiescencia: sigue mirando solo capturas hasta que no quede ninguna."""
        sin_capturar = self._evaluar(game)
        if sin_capturar >= beta:
            return sin_capturar
        alfa = max(alfa, sin_capturar)
        capturas = [j for j in game.jugadas_legales() if self._es_captura(game, j)]
        for jugada in self._ordenar(game, capturas):
            self._mirar_reloj()
            hijo = game.copy()
            hijo.jugar(jugada)
            if hijo.esta_terminada():
                valor = 0 if hijo.ganador() is None else MATE - ply
            else:
                valor = -self._capturas(hijo, -beta, -alfa, ply + 1)
            if valor >= beta:
                return valor
            alfa = max(alfa, valor)
        return alfa

    def _mirar_reloj(self):
        if time.time() > self._limite:
            raise SinTiempo

    # -----------------------------------------------------
    # Ordenar jugadas: primero comer lo valioso con lo barato
    # -----------------------------------------------------

    @staticmethod
    def _es_captura(game, jugada):
        return (game.board.get_piece(jugada.destino) is not None
                or jugada.promocion is not None)

    @staticmethod
    def _ordenar(game, jugadas):
        def prioridad(jugada):
            victima = game.board.get_piece(jugada.destino)
            if victima is None:
                return -VALOR[QUEEN] if jugada.promocion is not None else 0
            atacante = game.board.get_piece(jugada.origen)
            return -(10 * VALOR[victima.piece_type] - VALOR[atacante.piece_type])

        return sorted(jugadas, key=prioridad)

    # -----------------------------------------------------
    # Evaluar: material + posicion (+ remate), para quien mueve
    # -----------------------------------------------------

    def _evaluar(self, game):
        total = 0.0
        piezas = {WHITE: 0, BLACK: 0}  # material sin contar peones
        reyes = {}
        for indice, pieza in enumerate(game.board.squares):
            if pieza is None:
                continue
            tipo = pieza.piece_type
            if tipo == KING:
                reyes[pieza.color] = indice
                continue
            signo = 1 if pieza.color == WHITE else -1
            # Fila contada desde mi lado: 0 = mi primera fila.
            fila = indice // 8 if pieza.color == WHITE else 7 - indice // 8

            # Material
            total += signo * VALOR[tipo]
            if tipo != PAWN:
                piezas[pieza.color] += VALOR[tipo]

            # Posicion (premios siempre menores que un peon)
            if tipo == KNIGHT:
                total += signo * 0.4 * _cercania_al_centro(indice)  # hasta +1.2
            elif tipo == BISHOP:
                total += signo * 0.2 * _cercania_al_centro(indice)  # hasta +0.6
            elif tipo == PAWN:
                total += signo * 0.15 * (fila - 1)  # peon que avanza
                if 2 <= indice % 8 <= 5 and fila >= 3:
                    total += signo * 0.4  # peon central adelantado
            if tipo in (KNIGHT, BISHOP) and fila == 0:
                total -= signo * 0.5  # pieza sin sacar

        total += self._rematar(piezas, reyes)
        return total if game.turno == WHITE else -total

    @staticmethod
    def _rematar(piezas, reyes):
        """Si un bando va muy por delante, premia acorralar al rey rival."""
        for yo, rival in ((WHITE, BLACK), (BLACK, WHITE)):
            if (piezas[rival] <= REMATE_MATERIAL_RIVAL
                    and piezas[yo] - piezas[rival] >= REMATE_VENTAJA):
                mi_rey, su_rey = reyes[yo], reyes[rival]
                distancia = max(abs(mi_rey % 8 - su_rey % 8),
                                abs(mi_rey // 8 - su_rey // 8))
                bonus = (3 - _cercania_al_centro(su_rey)) + 0.5 * (7 - distancia)
                return bonus if yo == WHITE else -bonus
        return 0