"""
Bot con evaluacion APRENDIDA de partidas reales y busqueda rapida.

Junta dos piezas:

  1. La FUNCION DE EVALUACION se aprende de partidas de Lichess
     (evaluacion_ml.py y training/): en lugar de escribir a mano cuanto vale
     cada pieza en cada casilla, un modelo lo ajusta para predecir quien
     gana las partidas.
  2. La BUSQUEDA es el motor rapido de motor_rapido.py: negamax con poda
     alfa-beta y las mejoras habituales (tabla de transposicion, jugada nula,
     reducciones...). Mira mucho mas lejos que MinimaxBot en el mismo tiempo.

Como todo bot, solo MIRA la partida (game) y devuelve una Move legal: las
reglas siguen siendo las de game.py. Internamente convierte la partida al
motor rapido (con su FEN), busca, y comprueba la jugada contra
game.jugadas_legales() antes de devolverla.

Se puede limitar por profundidad ('profundidad') o por tiempo ('tiempo',
en segundos por jugada). Con tiempo, el resultado depende de la velocidad
del ordenador.
"""

from chess.bots.base import Bot
from chess.bots.evaluacion_ml import cargar_extras, cargar_pesos
from chess.bots.libro import Libro
from chess.bots.motor_rapido import (
    Buscador, Posicion, Z_AL_PASO, Z_ENROQUE, Z_PIEZA, Z_TURNO,
    jugada_a_texto, tablas_de_pesos,
)
from chess.move import jugada_desde_texto
from chess.pieces import KING, WHITE, PAWN, KNIGHT, BISHOP, ROOK, QUEEN

_CODIGO = {PAWN: 1, KNIGHT: 2, BISHOP: 3, ROOK: 4, QUEEN: 5, KING: 6}
_tablas_por_defecto = None


def _pesos():
    """
    Los pesos del fichero, ya preparados para el motor (se cargan una vez):
    ((tablas mg, tablas eg), (extras mg, extras eg)).
    """
    global _tablas_por_defecto
    if _tablas_por_defecto is None:
        _tablas_por_defecto = (tablas_de_pesos(*cargar_pesos()), cargar_extras())
    return _tablas_por_defecto


def hash_de_clave(clave):
    """
    Hash del motor rapido para una clave de posicion de Game
    (ver Game.clave_posicion): piezas, turno, enroques y captura al paso.
    """
    casillas, turno, derechos, al_paso = clave
    h = 0
    for sq, pieza in enumerate(casillas):
        if pieza is not None:
            codigo = _CODIGO[pieza.piece_type] + (0 if pieza.color == WHITE else 6)
            h ^= Z_PIEZA[codigo][sq]
    if turno != WHITE:
        h ^= Z_TURNO
    mascara = 0
    for letra, bit in (("K", 1), ("Q", 2), ("k", 4), ("q", 8)):
        if letra in derechos:
            mascara |= bit
    h ^= Z_ENROQUE[mascara]
    if al_paso is not None:
        h ^= Z_AL_PASO["abcdefgh".index(al_paso[0])]
    return h


class MLBot(Bot):
    """
    Bot con evaluacion aprendida y busqueda rapida.

    - 'profundidad': profundidad maxima (None = solo manda el tiempo).
    - 'tiempo': segundos maximos por jugada (None = solo manda la profundidad).
    - 'libro': True para jugar las primeras jugadas con el libro de aperturas
      aprendido de partidas de Lichess (libro.py); fuera del libro, piensa.
    - 'seed': semilla del azar del libro (para repetir partidas).
    - 'pesos': (tablas, extras) alternativos, para experimentos (ver _pesos).
    """

    name = "ml"

    def __init__(self, profundidad=None, tiempo=None, name=None, pesos=None, libro=False, seed=None):
        if profundidad is None and tiempo is None:
            tiempo = 2.0
        if name is not None:
            self.name = name
        self.profundidad = profundidad
        self.tiempo = tiempo
        self._tablas, extras = pesos if pesos is not None else _pesos()
        self._buscador = Buscador(
            pesos_extras=extras,
            tiempo=tiempo if tiempo is not None else 3600.0,
            profundidad=profundidad if profundidad is not None else 64,
        )
        self._libro = Libro(seed=seed) if libro else None
        self.del_libro = False         # True si la ultima jugada salio del libro
        self._jugadas_vistas = 0
        # Datos de la ultima busqueda (para mostrar o depurar).
        self.profundidad_alcanzada = 0
        self.nodos = 0
        self.valor = 0

    def choose_move(self, game):
        legales = game.jugadas_legales()
        self.del_libro = False
        if len(legales) == 1:
            return legales[0]
        if self._libro is not None:
            jugada = self._libro.elegir(game)
            if jugada is not None:
                self.del_libro = True
                return jugada

        # Una partida nueva: la tabla de la anterior ya no sirve.
        if len(game.historial) < self._jugadas_vistas:
            self._buscador.tabla.clear()
        self._jugadas_vistas = len(game.historial)

        pos = Posicion.desde_fen(game.fen(), self._tablas)
        previas = {}
        for clave, veces in getattr(game, "_repeticiones", {}).items():
            previas[hash_de_clave(clave)] = veces

        movimiento = self._buscador.buscar(pos, previas)
        self.profundidad_alcanzada = self._buscador.profundidad_alcanzada
        self.nodos = self._buscador.nodos
        self.valor = self._buscador.valor

        if movimiento:
            jugada = jugada_desde_texto(jugada_a_texto(movimiento))
            if jugada in legales:
                return jugada
        return legales[0]  # no deberia pasar: por si el motor se equivocara
