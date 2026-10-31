"""
Evaluacion APRENDIDA: una funcion de evaluacion cuyos numeros salen de
entrenar con partidas reales, en vez de escribirse a mano.

LA IDEA
-------
La evaluacion de evaluacion.py usa unas tablas de bonus por casilla
escritas por una persona. Aqui la forma de la funcion es la misma (una
tabla de puntos por cada tipo de pieza y casilla), pero los puntos los
aprende un modelo: se le dan cientos de miles de posiciones de partidas
reales de Lichess, cada una con quien termino ganando, y se ajustan las
tablas para que la evaluacion prediga bien ese resultado (regresion
logistica). El entrenamiento esta en training/entrenar.py.

Hay dos juegos de tablas, uno para la APERTURA/MEDIO JUEGO ('mg') y otro
para el FINAL ('eg'), y se mezclan segun cuanto material queda en el
tablero (la "fase" de la partida, de 24 = todas las piezas a 0 = solo
reyes y peones). Asi el rey aprende por si solo a esconderse al principio
y a ir al centro al final.

Ademas de las tablas por casilla, el modelo aprende el valor de unas
cuantas CARACTERISTICAS contadas (peones doblados, aislados o pasados,
pareja de alfiles, torre en columna abierta, escudo de peones del rey...
ver caracteristicas.py) y la ventaja de tener el turno.

El modelo es un producto escalar, asi que evaluar es rapido y NO hace
falta numpy para usarlo: los pesos se guardan en pesos_eval.json como
listas de numeros.

Esta clase es la version "de referencia", sobre el Board del proyecto: es
la forma mas facil de leer lo que calcula el modelo. El bot usa la misma
formula dentro del motor rapido (motor_rapido.py); los tests comprueban
que dan lo mismo.

El resultado esta en centipeones y es positivo si van mejor las blancas.
"""

import json
from pathlib import Path

from chess.bots.caracteristicas import N_EXTRAS, extras
from chess.pieces import WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

RUTA_PESOS = Path(__file__).with_name("pesos_eval.json")

# Orden de las piezas en el fichero de pesos y en el entrenamiento.
TIPOS = [PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING]
LETRAS = {PAWN: "P", KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K"}

# Cuanto aporta cada pieza a la "fase" de la partida (suma 24 con todas).
PESO_FASE = {PAWN: 0, KNIGHT: 1, BISHOP: 1, ROOK: 2, QUEEN: 4, KING: 0}
FASE_TOTAL = 24


def cargar_pesos(ruta=RUTA_PESOS):
    """Lee el fichero de pesos. Devuelve {"mg": {"P": [64 numeros], ...}, "eg": {...}}."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return datos["mg"], datos["eg"]


def cargar_extras(ruta=RUTA_PESOS):
    """
    Pesos de las caracteristicas contadas: (lista_mg, lista_eg) de N_EXTRAS
    numeros cada una. Si el fichero no las tiene, todo ceros.
    """
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    return (list(datos.get("extras_mg", [0] * N_EXTRAS)),
            list(datos.get("extras_eg", [0] * N_EXTRAS)))


def a_codigos(board):
    """El Board del proyecto como lista de 64 codigos (0 vacia, 1..6 blancas, 7..12 negras)."""
    codigos = [0] * 64
    for i, pieza in enumerate(board.squares):
        if pieza is not None:
            codigos[i] = TIPOS.index(pieza.piece_type) + 1 + (0 if pieza.color == WHITE else 6)
    return codigos


def _preparar_tablas(mg, eg):
    """
    Deja los pesos listos para evaluar rapido: para cada color y tipo de
    pieza, una lista de 64 numeros ya con el signo puesto (las negras
    restan) y con la casilla "dada la vuelta" para las negras.
    """
    tablas_mg = {WHITE: {}, BLACK: {}}
    tablas_eg = {WHITE: {}, BLACK: {}}
    for tipo in TIPOS:
        letra = LETRAS[tipo]
        tablas_mg[WHITE][tipo] = list(mg[letra])
        tablas_eg[WHITE][tipo] = list(eg[letra])
        # Casilla simetrica verticalmente: indice ^ 56 (a1 <-> a8, e2 <-> e7...).
        tablas_mg[BLACK][tipo] = [-mg[letra][i ^ 56] for i in range(64)]
        tablas_eg[BLACK][tipo] = [-eg[letra][i ^ 56] for i in range(64)]
    return tablas_mg, tablas_eg


class EvaluadorAprendido:
    """Evalua tableros con unos pesos concretos (los del fichero, por defecto)."""

    def __init__(self, mg=None, eg=None, extras_mg=None, extras_eg=None):
        if mg is None or eg is None:
            mg, eg = cargar_pesos()
            extras_mg, extras_eg = cargar_extras()
        self._mg, self._eg = _preparar_tablas(mg, eg)
        self._extras_mg = extras_mg if extras_mg is not None else [0] * N_EXTRAS
        self._extras_eg = extras_eg if extras_eg is not None else [0] * N_EXTRAS

    def __call__(self, board):
        return self.evaluar(board)

    def fase(self, board):
        """24 = todas las piezas en el tablero ... 0 = solo reyes y peones."""
        fase = 0
        for pieza in board.squares:
            if pieza is not None:
                fase += PESO_FASE[pieza.piece_type]
        return min(fase, FASE_TOTAL)

    def evaluar(self, board, turno=None):
        """
        Evaluacion en centipeones desde el punto de vista de las blancas.
        'turno' (WHITE o BLACK) es opcional: si se da, cuenta la ventaja de
        tener el turno.
        """
        tablas_mg = self._mg
        tablas_eg = self._eg
        suma_mg = 0
        suma_eg = 0
        fase = 0
        squares = board.squares
        for indice in range(64):
            pieza = squares[indice]
            if pieza is None:
                continue
            tipo = pieza.piece_type
            color = pieza.color
            suma_mg += tablas_mg[color][tipo][indice]
            suma_eg += tablas_eg[color][tipo][indice]
            fase += PESO_FASE[tipo]
        if fase > FASE_TOTAL:
            fase = FASE_TOTAL
        valores = extras(a_codigos(board), turno != BLACK)
        if turno is None:
            valores[-1] = 0
        for i in range(N_EXTRAS):
            suma_mg += self._extras_mg[i] * valores[i]
            suma_eg += self._extras_eg[i] * valores[i]
        return int((suma_mg * fase + suma_eg * (FASE_TOTAL - fase)) / FASE_TOTAL)


_evaluador_por_defecto = None


def evaluar_ml(board):
    """Evalua con los pesos de pesos_eval.json (se cargan la primera vez)."""
    global _evaluador_por_defecto
    if _evaluador_por_defecto is None:
        _evaluador_por_defecto = EvaluadorAprendido()
    return _evaluador_por_defecto.evaluar(board)
