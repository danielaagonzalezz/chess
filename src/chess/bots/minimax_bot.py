"""
Bot minimax con poda alfa-beta: piensa varias jugadas por delante.

LA IDEA (minimax)
-----------------
Yo quiero la jugada que deje la mejor posicion DESPUES de que el rival
responda lo mejor que pueda, y despues de que yo vuelva a responder, etc.
Se construye un arbol: cada nivel es una jugada de un bando. En las hojas
se evalua el tablero (evaluacion.py) y los valores suben por el arbol:
yo escojo el maximo, el rival escoge el minimo.

NEGAMAX
-------
Como el ajedrez es de suma cero (lo que gano yo lo pierde el rival),
basta con una sola funcion: el valor de una posicion para quien mueve es
el MAXIMO de menos el valor de cada respuesta. Asi no hace falta escribir
una version para cada bando.

PODA ALFA-BETA
--------------
Si ya sabemos que una rama es peor que otra que ya hemos mirado, no hace
falta seguir mirandola. 'alfa' es lo mejor que puedo conseguir seguro y
'beta' lo mejor que el rival me va a permitir. Si alfa >= beta, corta.
Da EXACTAMENTE el mismo resultado que minimax, mucho mas rapido,
sobre todo si se prueban primero las mejores jugadas.

BUSQUEDA DE CAPTURAS (quiescencia)
----------------------------------
Si cortamos la busqueda justo despues de que mi dama capture un peon,
no veo que me la capturan en la jugada siguiente y creo que gane un peon.
Para evitarlo, al llegar a la profundidad maxima seguimos mirando SOLO
las capturas hasta que la posicion se calme.

MEJORAS PARA IR MAS RAPIDO
--------------------------
  - Profundizacion iterativa: se busca con profundidad 1, luego 2, luego
    3... y cada vez se empieza por la mejor jugada de la vuelta anterior
    (asi la poda corta mucho mas). Ademas permite poner un LIMITE DE
    TIEMPO: si se acaba, se juega lo mejor de la ultima vuelta completa.
  - Tabla de transposicion: la misma posicion se puede alcanzar por
    caminos distintos (1.e4 e5 2.Cf3 o 1.Cf3 e5 2.e4). Se guarda lo que ya
    se calculo de cada posicion para no repetirlo.
  - "Killer moves": una jugada tranquila que ha provocado una poda en una
    rama probablemente vuelva a podar en las ramas vecinas, asi que se
    prueba pronto.
  - Orden de jugadas: primero la jugada que recordaba la tabla, luego las
    capturas (victima valiosa con atacante barato), luego los killers.

JAQUE MATE
----------
Un mate vale PUNTOS_MATE menos el numero de jugadas que hacen falta
para darlo: asi prefiere el mate mas rapido y retrasa su propia derrota.
"""

import random
import time

from chess.bots.base import Bot
from chess.bots.evaluacion import PUNTOS_MATE, VALOR_PIEZA, evaluar
from chess.pieces import PAWN, QUEEN, WHITE

INFINITO = PUNTOS_MATE * 10

# Cuantas capturas seguidas se miran como maximo despues de la profundidad.
PROFUNDIDAD_QUIESCENCIA = 4

# Tipos de valor guardados en la tabla de transposicion.
EXACTO = 0     # el valor guardado es el valor real de la posicion
INFERIOR = 1   # el valor real es AL MENOS el guardado (hubo poda beta)
SUPERIOR = 2   # el valor real es COMO MUCHO el guardado (ninguna jugada mejoro alfa)

# Los valores de mate no se guardan en la tabla: dependen de a cuantas
# jugadas esta el mate y mezclarlos entre posiciones daria resultados raros.
UMBRAL_MATE = PUNTOS_MATE - 1000

# Puntos para ordenar jugadas (mayor = se prueba antes).
ORDEN_TABLA = 1000000
ORDEN_CAPTURA = 10000
ORDEN_KILLER = 9000


class _SinTiempo(Exception):
    """Se lanza dentro de la busqueda cuando se acaba el tiempo."""


class MinimaxBot(Bot):
    """
    Bot que busca con minimax (negamax) y poda alfa-beta.

    - 'profundidad': cuantas jugadas (de cada bando) mira como maximo:
      2 = juega rapido y regular, 3 = juega bien, 4 = mejor pero mas lento.
    - 'tiempo' (opcional): segundos maximos por jugada. Si se da, el bot
      busca cada vez mas profundo hasta que se acabe el tiempo o llegue a
      'profundidad'. Con un tiempo, el resultado puede variar de un
      ordenador a otro (depende de lo rapido que sea).
    - 'seed': semilla para elegir entre jugadas igual de buenas.
    """

    name = "minimax"

    def __init__(self, profundidad=3, seed=None, name=None, tiempo=None):
        self.profundidad = profundidad
        self.tiempo = tiempo
        self._azar = random.Random(seed)
        if name is not None:
            self.name = name
        self.nodos = 0                 # posiciones miradas en la ultima busqueda
        self.profundidad_alcanzada = 0  # profundidad de la ultima vuelta completa
        self._limite = None
        self._tabla = {}
        self._killers = []

    # -----------------------------------------------------
    # Elegir la jugada
    # -----------------------------------------------------

    def choose_move(self, game):
        self.nodos = 0
        self.profundidad_alcanzada = 0
        self._tabla = {}
        self._killers = [[None, None] for _ in range(self.profundidad + PROFUNDIDAD_QUIESCENCIA + 2)]
        self._limite = None if self.tiempo is None else time.perf_counter() + self.tiempo

        jugadas = game.jugadas_legales()
        # Mezclamos antes de ordenar: entre jugadas igual de buenas, el bot
        # no juega siempre lo mismo.
        self._azar.shuffle(jugadas)
        jugadas = self._ordenar(game, jugadas, None, 0)
        mejor_jugada = jugadas[0]

        try:
            for profundidad in range(1, self.profundidad + 1):
                mejor_jugada, valor = self._buscar_en_la_raiz(game, jugadas, profundidad)
                self.profundidad_alcanzada = profundidad

                # La mejor jugada de esta vuelta se prueba la primera en la siguiente.
                jugadas = [mejor_jugada] + [j for j in jugadas if j != mejor_jugada]

                if abs(valor) >= UMBRAL_MATE:
                    break  # ya hay un mate (a favor o en contra): no hace falta mas
        except _SinTiempo:
            pass  # nos quedamos con la mejor jugada de la ultima vuelta completa

        return mejor_jugada

    def _buscar_en_la_raiz(self, game, jugadas, profundidad):
        """Una vuelta completa de la busqueda. Devuelve (mejor jugada, su valor)."""
        mejor_jugada = jugadas[0]
        alfa = -INFINITO
        for jugada in jugadas:
            hijo = game.copy()
            hijo.jugar(jugada)
            valor = -self._negamax(hijo, profundidad - 1, -INFINITO, -alfa, 1)
            if valor > alfa:
                alfa = valor
                mejor_jugada = jugada
        return mejor_jugada, alfa

    # -----------------------------------------------------
    # La busqueda
    # -----------------------------------------------------

    def _comprobar_tiempo(self):
        if self._limite is not None and time.perf_counter() > self._limite:
            raise _SinTiempo()

    def _negamax(self, game, profundidad, alfa, beta, ply):
        """
        Valor de la posicion para QUIEN TIENE EL TURNO (positivo = va ganando).

        'ply' es cuantas jugadas llevamos desde la posicion de partida de
        la busqueda; se usa para preferir mates rapidos y para los killers.
        """
        self.nodos += 1
        self._comprobar_tiempo()

        if game.esta_terminada():
            return self._valor_final(game, ply)
        if profundidad == 0:
            return self._quiescencia(game, alfa, beta, ply, PROFUNDIDAD_QUIESCENCIA)

        # ---- Consultar la tabla de transposicion ----
        alfa_original = alfa
        clave = game.clave_posicion()
        jugada_de_la_tabla = None
        entrada = self._tabla.get(clave)
        if entrada is not None:
            profundidad_guardada, valor_guardado, tipo, jugada_de_la_tabla = entrada
            if profundidad_guardada >= profundidad:
                if tipo == EXACTO:
                    return valor_guardado
                if tipo == INFERIOR and valor_guardado > alfa:
                    alfa = valor_guardado
                elif tipo == SUPERIOR and valor_guardado < beta:
                    beta = valor_guardado
                if alfa >= beta:
                    return valor_guardado

        # ---- Probar las jugadas ----
        mejor = -INFINITO
        mejor_jugada = None
        for jugada in self._ordenar(game, game.jugadas_legales(), jugada_de_la_tabla, ply):
            hijo = game.copy()
            hijo.jugar(jugada)
            valor = -self._negamax(hijo, profundidad - 1, -beta, -alfa, ply + 1)

            if valor > mejor:
                mejor = valor
                mejor_jugada = jugada
            if mejor > alfa:
                alfa = mejor
            if alfa >= beta:
                # Poda. Si la jugada fue tranquila (no captura), es un killer.
                if not self._es_captura(game, jugada):
                    self._guardar_killer(ply, jugada)
                break

        # ---- Guardar en la tabla ----
        if abs(mejor) < UMBRAL_MATE:
            if mejor <= alfa_original:
                tipo = SUPERIOR
            elif mejor >= beta:
                tipo = INFERIOR
            else:
                tipo = EXACTO
            self._tabla[clave] = (profundidad, mejor, tipo, mejor_jugada)

        return mejor

    def _quiescencia(self, game, alfa, beta, ply, restante):
        """Sigue la busqueda solo con capturas hasta que la posicion se calme."""
        self.nodos += 1
        self._comprobar_tiempo()

        if game.esta_terminada():
            return self._valor_final(game, ply)

        # "Stand pat": siempre puedo decidir no capturar mas.
        estatica = self._evaluar_para_el_turno(game)
        if restante == 0 or estatica >= beta:
            return estatica
        if estatica > alfa:
            alfa = estatica

        capturas = [j for j in game.jugadas_legales() if self._es_captura(game, j)]
        for jugada in self._ordenar(game, capturas, None, ply, con_killers=False):
            hijo = game.copy()
            hijo.jugar(jugada)
            valor = -self._quiescencia(hijo, -beta, -alfa, ply + 1, restante - 1)

            if valor >= beta:
                return valor
            if valor > alfa:
                alfa = valor
        return alfa

    # -----------------------------------------------------
    # Valores
    # -----------------------------------------------------

    def _valor_final(self, game, ply):
        """Valor de una partida terminada para quien tenia el turno."""
        if game.ganador() is None:
            return 0                       # tablas
        # Si la partida acabo con ganador, el que tiene el turno es el que
        # ha sido mateado: pierde. Cuanto mas lejos el mate, menos malo.
        return -(PUNTOS_MATE - ply)

    def _evaluar_para_el_turno(self, game):
        """La evaluacion (desde las blancas) vista por quien tiene el turno."""
        valor = evaluar(game.board)
        if game.turno == WHITE:
            return valor
        return -valor

    # -----------------------------------------------------
    # Ordenar jugadas (para que la poda corte mas)
    # -----------------------------------------------------

    def _es_captura(self, game, jugada):
        if game.board.get_piece(jugada.destino) is not None:
            return True
        # Captura al paso: un peon que cambia de columna a una casilla vacia.
        pieza = game.board.get_piece(jugada.origen)
        return pieza.piece_type == PAWN and jugada.destino.file != jugada.origen.file

    def _guardar_killer(self, ply, jugada):
        killers = self._killers[ply]
        if killers[0] != jugada:
            killers[1] = killers[0]
            killers[0] = jugada

    def _ordenar(self, game, jugadas, jugada_de_la_tabla, ply, con_killers=True):
        """
        Ordena las jugadas de mejor a peor candidata: primero la de la tabla,
        luego las capturas (victima valiosa con atacante barato) y las
        promociones, luego los killers y por ultimo el resto.
        """
        killers = self._killers[ply] if con_killers and ply < len(self._killers) else (None, None)

        def puntos(jugada):
            if jugada == jugada_de_la_tabla:
                return ORDEN_TABLA
            board = game.board
            atacante = board.get_piece(jugada.origen)
            victima = board.get_piece(jugada.destino)

            total = 0
            if victima is not None:
                total = ORDEN_CAPTURA + 10 * VALOR_PIEZA[victima.piece_type] \
                    - VALOR_PIEZA[atacante.piece_type]
            elif atacante.piece_type == PAWN and jugada.destino.file != jugada.origen.file:
                total = ORDEN_CAPTURA + 10 * VALOR_PIEZA[PAWN] - VALOR_PIEZA[PAWN]  # al paso
            elif jugada == killers[0] or jugada == killers[1]:
                total = ORDEN_KILLER
            if jugada.promocion == QUEEN:
                total += VALOR_PIEZA[QUEEN]
            return total

        return sorted(jugadas, key=puntos, reverse=True)
