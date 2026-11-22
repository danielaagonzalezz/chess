"""
Bot Monte Carlo (MCTS): decide jugando muchas partidas rapidas "a medias".

LA IDEA
-------
Un bot minimax mira TODAS las respuestas hasta cierta profundidad. Este bot
hace lo contrario: no mira todo, MUESTREA. Desde la posicion actual juega
miles de continuaciones cortas (con algo de sentido comun) y se queda con la
jugada que, de media, termina mejor. Cuantas mas muestras tiene una jugada,
mas se fia de su media.

Es la busqueda de arbol de Monte Carlo (MCTS, con la formula UCT). Cada
iteracion hace cuatro pasos:

  1. SELECCION. Se baja por el arbol que ya se ha construido, eligiendo en cada
     nivel el hijo con mejor puntuacion UCB1:

         media + C * raiz( ln(visitas del padre) / visitas del hijo )

     La "media" explota lo que ya funciona; el segundo termino explora las
     jugadas poco probadas. C regula el equilibrio.
  2. EXPANSION. Al llegar a una posicion con jugadas sin probar, se prueba una
     (las capturas primero) y se anade al arbol.
  3. SIMULACION (rollout). Desde ahi se juegan unas cuantas jugadas con una
     politica barata: casi siempre captura lo mas valioso que puede, sin regalar
     piezas, y si no, una jugada al azar.
  4. RETROPROPAGACION. El resultado se suma a todas las posiciones del camino,
     cada una desde el punto de vista de quien jugo para llegar a ella.

LO QUE SE ADAPTA AL AJEDREZ
---------------------------
En un juego pequeno se juega cada simulacion hasta el final. En ajedrez eso no
sirve: una partida al azar tarda cientos de jugadas en acabar y casi nunca se
da jaque mate. Por eso:

  - La simulacion se CORTA tras 'profundidad_rollout' jugadas y la posicion se
    evalua (material + casillas de las piezas, la evaluacion del motor rapido).
    Esa evaluacion en centipeones se convierte en una probabilidad de ganar
    con la curva logistica 1 / (1 + 10^(-cp/400)), la misma del Elo.
  - Antes de evaluar se RESUELVEN LAS CAPTURAS pendientes (busqueda de capturas,
    como en el minimax): si no, se evaluaria a mitad de un cambio y se creeria
    ganar una pieza que en realidad nos van a quitar.
  - Si en el camino hay jaque mate o ahogado, se usa el resultado real
    (1, 0 o 0.5) en lugar de la evaluacion.
  - Un mate en una jugada se juega directamente, y se descartan las jugadas tras
    las cuales el rival puede dar mate en una (las simulaciones, tan cortas, no
    lo verian).

El bot NO toca las reglas: convierte la partida al motor rapido de
motor_rapido.py (que hace y deshace jugadas sobre el mismo tablero, sin copiar)
solo para ir deprisa, y la jugada elegida se comprueba contra
game.jugadas_legales() antes de devolverla.

Se limita por tiempo ('tiempo', segundos por jugada) o, para repetir
resultados (tests), por 'iteraciones'.
"""

import math
import random
import time

from chess.bots.base import Bot
from chess.bots.evaluacion_ml import cargar_pesos
from chess.bots.motor_rapido import (
    FASE_TOTAL, Posicion, VALOR_ORDEN, jugada_a_texto, tablas_de_pesos,
)
from chess.move import jugada_desde_texto

_tablas_por_defecto = None

# Mas que cualquier evaluacion posible (para los limites de la busqueda de capturas).
INFINITO = 1000000

# Tipo de pieza (1 peon .. 6 rey) y valor en centipeones, por codigo del motor
# (0 = casilla vacia, 1..6 blancas, 7..12 negras).
_TIPO = [0, 1, 2, 3, 4, 5, 6, 1, 2, 3, 4, 5, 6]
_VALOR = [0, 100, 320, 330, 500, 900, 20000]


def _tablas():
    """Las tablas de pieza-casilla del motor rapido (se cargan una vez)."""
    global _tablas_por_defecto
    if _tablas_por_defecto is None:
        _tablas_por_defecto = tablas_de_pesos(*cargar_pesos())
    return _tablas_por_defecto


# ---------------------------------------------------------
# Funciones auxiliares sobre la posicion del motor rapido
# ---------------------------------------------------------

def _prob_blancas(pos, profundidad_captura):
    """
    Probabilidad (0..1) de que ganen las blancas en 'pos': se evalua la posicion
    tras resolver las capturas y se pasa de centipeones a probabilidad con la
    curva logistica del Elo.
    """
    if profundidad_captura > 0:
        centipeones = _quiescencia(pos, -INFINITO, INFINITO, profundidad_captura)
        if pos.side == 1:
            centipeones = -centipeones
    else:
        fase = min(pos.phase, FASE_TOTAL)
        centipeones = (pos.mg * fase + pos.eg * (FASE_TOTAL - fase)) / FASE_TOTAL
    centipeones = max(-2000.0, min(2000.0, centipeones))
    return 1.0 / (1.0 + 10.0 ** (-centipeones / 400.0))


def _centipeones(pos):
    """Evaluacion estatica en centipeones para quien tiene el turno (material + casillas)."""
    fase = min(pos.phase, FASE_TOTAL)
    blancas = (pos.mg * fase + pos.eg * (FASE_TOTAL - fase)) // FASE_TOTAL
    return blancas if pos.side == 0 else -blancas


def _quiescencia(pos, alfa, beta, profundidad):
    """
    Evaluacion que "deja terminar los cambios": en vez de evaluar justo a mitad de
    una captura (y creer que ganamos una pieza que nos van a quitar), sigue mirando
    SOLO las capturas hasta que la posicion se calme. Devuelve centipeones para
    quien tiene el turno. Es la misma idea de la busqueda de capturas del minimax.
    """
    mejor = _centipeones(pos)             # "stand pat": siempre se puede no capturar
    if mejor >= beta or profundidad == 0:
        return mejor
    if mejor > alfa:
        alfa = mejor
    capturas = pos.generar(capturas=True)
    capturas.sort(key=lambda j: _valor_captura(pos, j), reverse=True)
    for jugada in capturas:
        pos.hacer(jugada)
        if pos.legal_tras_hacer():
            valor = -_quiescencia(pos, -beta, -alfa, profundidad - 1)
            pos.deshacer()
            if valor > mejor:
                mejor = valor
                if mejor >= beta:
                    break
                if mejor > alfa:
                    alfa = mejor
        else:
            pos.deshacer()
    return mejor


def _valor_captura(pos, jugada):
    """
    Cuanto "mola" una jugada para ordenar: capturas de pieza valiosa con
    atacante barato primero (MVV-LVA). 0 si no es captura ni promocion.
    """
    destino = (jugada >> 6) & 63
    victima = pos.b[destino]
    if victima == 0 and (jugada >> 15) != 1:
        # Ni captura normal ni al paso: solo cuenta una promocion.
        return 900 if ((jugada >> 12) & 7) == 5 else 0
    valor_victima = VALOR_ORDEN[victima if victima < 7 else victima - 6] if victima else 100
    atacante = pos.b[jugada & 63]
    valor_atacante = VALOR_ORDEN[atacante if atacante < 7 else atacante - 6]
    return 10 * valor_victima - min(valor_atacante, 2000) // 10


def _legales_ordenadas(pos):
    """Jugadas legales, las capturas buenas al final (se sacan con pop(), asi se prueban antes)."""
    legales = []
    for jugada in pos.generar():
        pos.hacer(jugada)
        if pos.legal_tras_hacer():
            legales.append(jugada)
        pos.deshacer()
    legales.sort(key=lambda j: _valor_captura(pos, j))
    return legales


class _Nodo:
    """Una posicion del arbol de busqueda."""

    __slots__ = ("jugada", "padre", "hijos", "sin_probar", "visitas", "puntos",
                 "mueven_blancas", "terminal")

    def __init__(self, jugada, padre, mueven_blancas):
        self.jugada = jugada                  # la jugada que llevo hasta aqui
        self.padre = padre
        self.hijos = []
        self.sin_probar = None                # se rellena la primera vez que se visita
        self.visitas = 0
        self.puntos = 0.0                     # suma de resultados para quien JUGO esa jugada
        self.mueven_blancas = mueven_blancas  # True si la jugada que llego aqui la hicieron las blancas
        self.terminal = None                  # None, o el resultado para las blancas (1, 0.5, 0)


class MonteCarloBot(Bot):
    """
    Bot MCTS (Monte Carlo + UCT) con simulaciones cortas y evaluacion al final.

    - 'tiempo': segundos maximos por jugada.
    - 'iteraciones': si se da, manda en lugar del tiempo (resultado repetible).
    - 'profundidad_rollout': jugadas que dura cada simulacion antes de evaluar.
    - 'profundidad_captura': capturas seguidas que se resuelven al evaluar
      (0 = evaluacion directa).
    - 'exploracion': la constante C de UCB1 (mas alta = prueba mas jugadas distintas).
    - 'prob_captura': probabilidad de que el rollout capture si puede.
    - 'prob_seguridad': probabilidad de que el rollout descarte una jugada que
      regala la pieza.
    - 'seed': semilla del azar (para repetir partidas).
    """

    name = "montecarlo"

    def __init__(self, tiempo=1.0, iteraciones=None, profundidad_rollout=2, profundidad_captura=6,
                 exploracion=0.5, prob_captura=0.9, prob_seguridad=0.9, seed=None, name=None):
        if name is not None:
            self.name = name
        self.tiempo = tiempo
        self.iteraciones = iteraciones
        self.profundidad_rollout = profundidad_rollout
        self.profundidad_captura = profundidad_captura
        self.exploracion = exploracion
        self.prob_captura = prob_captura
        self.prob_seguridad = prob_seguridad
        self._azar = random.Random(seed)
        # Datos de la ultima busqueda (para mostrar o depurar).
        self.simulaciones = 0
        self.valor = 0.5          # probabilidad estimada de ganar de la jugada elegida

    # -----------------------------------------------------
    # Elegir la jugada
    # -----------------------------------------------------

    def choose_move(self, game):
        legales = game.jugadas_legales()
        if len(legales) == 1:
            return legales[0]

        limite = time.perf_counter() + self.tiempo
        pos = Posicion.desde_fen(game.fen(), _tablas())
        raiz = _Nodo(0, None, mueven_blancas=(pos.side == 1))   # "los que movieron antes" = el rival
        self._abrir(raiz, pos)

        # Un mate en una jugada se juega sin buscar. Y se descartan las jugadas tras las
        # cuales el rival da mate en una: las simulaciones son cortas y no lo verian.
        seguras = []
        for jugada in raiz.sin_probar:
            pos.hacer(jugada)
            if self._resultado_terminal(pos) is not None and pos.en_jaque():
                pos.deshacer()
                return self._a_move(jugada, legales)
            if not self._rival_da_mate(pos):
                seguras.append(jugada)
            pos.deshacer()
        if seguras:
            seguras.sort(key=lambda j: _valor_captura(pos, j))
            raiz.sin_probar = seguras
        if len(raiz.sin_probar) == 1:
            return self._a_move(raiz.sin_probar[0], legales)

        self.simulaciones = 0
        while True:
            if self.iteraciones is not None:
                if self.simulaciones >= self.iteraciones:
                    break
            elif time.perf_counter() >= limite:
                break
            self._iteracion(raiz, pos)
            self.simulaciones += 1

        # La jugada elegida es la MAS VISITADA (no la de mejor media): es la mas
        # robusta, porque una media sacada de pocas muestras puede ser suerte.
        mejor = max(raiz.hijos, key=lambda h: (h.visitas, h.puntos))
        self.valor = mejor.puntos / mejor.visitas if mejor.visitas else 0.5
        return self._a_move(mejor.jugada, legales)

    def _a_move(self, jugada, legales):
        move = jugada_desde_texto(jugada_a_texto(jugada))
        if move in legales:
            return move
        return legales[0]   # no deberia pasar: por si el motor se equivocara

    # -----------------------------------------------------
    # Las cuatro fases de una iteracion
    # -----------------------------------------------------

    def _abrir(self, nodo, pos):
        """Calcula las jugadas legales de un nodo la primera vez que se llega a el."""
        nodo.sin_probar = _legales_ordenadas(pos)
        if not nodo.sin_probar:
            # Sin jugadas: mate (pierde quien mueve) o ahogado (tablas).
            if pos.en_jaque():
                nodo.terminal = 0.0 if pos.side == 0 else 1.0
            else:
                nodo.terminal = 0.5
        elif pos.half >= 100 or pos.material_insuficiente():
            nodo.terminal = 0.5
            nodo.sin_probar = []

    def _rival_da_mate(self, pos):
        """True si quien mueve en 'pos' tiene una jugada que da jaque mate."""
        for jugada in pos.generar():
            pos.hacer(jugada)
            if pos.legal_tras_hacer() and pos.en_jaque() and self._resultado_terminal(pos) is not None:
                pos.deshacer()
                return True
            pos.deshacer()
        return False

    def _resultado_terminal(self, pos):
        """Resultado para las blancas si la partida acabo en 'pos' (sin jugadas), si no None."""
        for jugada in pos.generar():
            pos.hacer(jugada)
            legal = pos.legal_tras_hacer()
            pos.deshacer()
            if legal:
                return None
        if pos.en_jaque():
            return 0.0 if pos.side == 0 else 1.0
        return 0.5

    def _iteracion(self, raiz, pos):
        nodo = raiz
        hechas = 0

        # 1. SELECCION: bajar mientras todas las jugadas del nodo esten probadas.
        while nodo.terminal is None and not nodo.sin_probar and nodo.hijos:
            nodo = self._mejor_hijo(nodo)
            pos.hacer(nodo.jugada)
            hechas += 1

        # 2. EXPANSION: probar una jugada nueva.
        if nodo.terminal is None and nodo.sin_probar:
            jugada = nodo.sin_probar.pop()
            pos.hacer(jugada)
            hechas += 1
            hijo = _Nodo(jugada, nodo, mueven_blancas=(pos.side == 1))
            nodo.hijos.append(hijo)
            nodo = hijo
            self._abrir(nodo, pos)

        # 3. SIMULACION: resultado (para las blancas) de seguir desde aqui.
        if nodo.terminal is not None:
            resultado = nodo.terminal
        else:
            resultado = self._rollout(pos)

        # 4. RETROPROPAGACION.
        while nodo is not None:
            nodo.visitas += 1
            nodo.puntos += resultado if nodo.mueven_blancas else 1.0 - resultado
            nodo = nodo.padre

        for _ in range(hechas):
            pos.deshacer()

    def _mejor_hijo(self, nodo):
        """El hijo con mayor UCB1 (media + bonus de exploracion)."""
        log_padre = math.log(nodo.visitas + 1)
        c = self.exploracion
        mejor, mejor_valor = None, -1.0
        for hijo in nodo.hijos:
            valor = hijo.puntos / hijo.visitas + c * math.sqrt(log_padre / hijo.visitas)
            if valor > mejor_valor:
                mejor, mejor_valor = hijo, valor
        return mejor

    def _rollout(self, pos):
        """
        Juega unas jugadas con la politica barata y devuelve la probabilidad de que
        ganen las blancas. Deja la posicion como estaba.
        """
        azar = self._azar
        hechas = 0
        resultado = None
        for _ in range(self.profundidad_rollout):
            jugada = self._jugada_de_rollout(pos, azar)
            if jugada == 0:
                # No hay jugadas legales: mate o ahogado.
                resultado = self._resultado_terminal(pos)
                break
            pos.hacer(jugada)
            hechas += 1
            if pos.half >= 100:
                resultado = 0.5
                break
        if resultado is None:
            resultado = _prob_blancas(pos, self.profundidad_captura)
        for _ in range(hechas):
            pos.deshacer()
        return resultado

    def _jugada_de_rollout(self, pos, azar):
        """
        Una jugada LEGAL para el rollout (o 0 si no hay).

        Con probabilidad 'prob_captura' se prefieren las capturas (la de mas valor
        primero, MVV-LVA); si no, el orden es al azar. Una jugada que deja la pieza
        en una casilla atacada por el rival, regalandola (la pieza vale bastante mas
        que lo que captura), se descarta casi siempre: sin esto las simulaciones
        pierden piezas por nada y el bot se fia de partidas absurdas.
        """
        pseudo = pos.generar()
        azar.shuffle(pseudo)
        if azar.random() < self.prob_captura:
            pseudo.sort(key=lambda j: _valor_captura(pos, j), reverse=True)
        primera_legal = 0
        for jugada in pseudo:
            pieza = pos.b[jugada & 63]
            capturada = pos.b[(jugada >> 6) & 63]
            pos.hacer(jugada)
            legal = pos.legal_tras_hacer()
            if legal:
                if not primera_legal:
                    primera_legal = jugada
                regala = (
                    _TIPO[pieza] != 6   # el rey no cuenta: ya se comprobo que no deja jaque
                    and _VALOR[_TIPO[pieza]] > _VALOR[_TIPO[capturada]] + 100
                    and pos.atacado((jugada >> 6) & 63, pos.side)
                )
                if regala and azar.random() < self.prob_seguridad:
                    legal = False
            pos.deshacer()
            if legal:
                return jugada
        return primera_legal
