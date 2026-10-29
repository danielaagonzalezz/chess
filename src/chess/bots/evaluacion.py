"""
Evaluacion de posiciones: cuanto "vale" una posicion para las blancas.

Un bot que piensa necesita poder decir si una posicion es buena o mala
sin llegar al final de la partida. Esa estimacion es la funcion de
evaluacion. Aqui usamos dos ideas clasicas:

  1. MATERIAL: cada pieza vale puntos (peon 100, caballo 320, alfil 330,
     torre 500, dama 900). Los puntos son "centipeones": 100 = un peon.
  2. POSICION: una pieza vale mas o menos segun la casilla donde esta.
     Un caballo en el centro es mejor que en una esquina; un peon
     avanzado es mejor que uno atrasado. Se mide con unas tablas de
     bonus por casilla ("piece-square tables").

Las tablas son las de la "Simplified Evaluation Function" de Tomasz
Michniewski, muy conocida y publicada en chessprogramming.org.

El resultado es positivo si van mejor las blancas y negativo si van
mejor las negras.
"""

from chess.pieces import WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

# Puntuacion enorme que representa "jaque mate" (mucho mayor que cualquier
# diferencia de material).
PUNTOS_MATE = 100000

VALOR_PIEZA = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 0,
}

# Cada tabla se escribe como se ve el tablero: la primera fila es la fila 8
# y la ultima es la fila 1, vista desde las BLANCAS (columna a a la izquierda).
_TABLA_PEON = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0,
]
_TABLA_CABALLO = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50,
]
_TABLA_ALFIL = [
   -20,-10,-10,-10,-10,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5, 10, 10,  5,  0,-10,
   -10,  5,  5, 10, 10,  5,  5,-10,
   -10,  0, 10, 10, 10, 10,  0,-10,
   -10, 10, 10, 10, 10, 10, 10,-10,
   -10,  5,  0,  0,  0,  0,  5,-10,
   -20,-10,-10,-10,-10,-10,-10,-20,
]
_TABLA_TORRE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0,
]
_TABLA_DAMA = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -10,  0,  5,  5,  5,  5,  0,-10,
    -5,  0,  5,  5,  5,  5,  0, -5,
     0,  0,  5,  5,  5,  5,  0, -5,
   -10,  5,  5,  5,  5,  5,  0,-10,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20,
]
# El rey en la partida (esconderse en una esquina)...
_TABLA_REY_PARTIDA = [
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -30,-40,-40,-50,-50,-40,-40,-30,
   -20,-30,-30,-40,-40,-30,-30,-20,
   -10,-20,-20,-20,-20,-20,-20,-10,
    20, 20,  0,  0,  0,  0, 20, 20,
    20, 30, 10,  0,  0, 10, 30, 20,
]
# ...y en el final (ir al centro y ayudar).
_TABLA_REY_FINAL = [
   -50,-40,-30,-20,-20,-30,-40,-50,
   -30,-20,-10,  0,  0,-10,-20,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-30,  0,  0,  0,  0,-30,-30,
   -50,-30,-30,-30,-30,-30,-30,-50,
]


def _a_indices_de_casilla(tabla):
    """
    Pasa una tabla escrita "como se ve el tablero" (fila 8 arriba) a una
    lista indexada por Square.to_index() (a1=0, h1=7, a2=8 ... h8=63).
    """
    resultado = [0] * 64
    for fila_escrita in range(8):
        rank = 7 - fila_escrita
        for file in range(8):
            resultado[rank * 8 + file] = tabla[fila_escrita * 8 + file]
    return resultado


TABLAS = {
    PAWN: _a_indices_de_casilla(_TABLA_PEON),
    KNIGHT: _a_indices_de_casilla(_TABLA_CABALLO),
    BISHOP: _a_indices_de_casilla(_TABLA_ALFIL),
    ROOK: _a_indices_de_casilla(_TABLA_TORRE),
    QUEEN: _a_indices_de_casilla(_TABLA_DAMA),
}
TABLA_REY_PARTIDA = _a_indices_de_casilla(_TABLA_REY_PARTIDA)
TABLA_REY_FINAL = _a_indices_de_casilla(_TABLA_REY_FINAL)


def _indice_espejo(indice):
    """Casilla simetrica verticalmente: sirve para leer la tabla de las negras."""
    rank = indice // 8
    file = indice % 8
    return (7 - rank) * 8 + file


def _distancia_al_centro(indice):
    """Cuanto se aleja una casilla del centro (0 = centro, 6 = esquina)."""
    file = indice % 8
    rank = indice // 8
    dist_columna = max(3 - file, file - 4)
    dist_fila = max(3 - rank, rank - 4)
    return dist_columna + dist_fila


def evaluar(board):
    """
    Evalua el tablero en "centipeones" desde el punto de vista de las blancas.

    Positivo: mejor para las blancas. Negativo: mejor para las negras.
    """
    material = {WHITE: 0, BLACK: 0}      # todo el material de cada bando
    piezas = {WHITE: 0, BLACK: 0}        # material sin contar los peones
    reyes = {}
    total = 0

    for indice in range(64):
        pieza = board.squares[indice]
        if pieza is None:
            continue

        if pieza.piece_type == KING:
            reyes[pieza.color] = indice
            continue

        # Casilla en la tabla: las negras la leen "dada la vuelta".
        if pieza.color == WHITE:
            bonus = TABLAS[pieza.piece_type][indice]
        else:
            bonus = TABLAS[pieza.piece_type][_indice_espejo(indice)]

        valor = VALOR_PIEZA[pieza.piece_type]
        material[pieza.color] += valor
        if pieza.piece_type != PAWN:
            piezas[pieza.color] += valor
        if pieza.color == WHITE:
            total += valor + bonus
        else:
            total -= valor + bonus

    # ---- Los reyes: tabla de partida o de final ----
    # Estamos en un final cuando a cada bando le quedan pocas piezas
    # (como mucho una dama y un alfil, o dos torres): entonces el rey ya
    # no tiene que esconderse, sino ir al centro y ayudar.
    es_final = piezas[WHITE] <= 1300 and piezas[BLACK] <= 1300
    tabla_rey = TABLA_REY_FINAL if es_final else TABLA_REY_PARTIDA
    if WHITE in reyes:
        total += tabla_rey[reyes[WHITE]]
    if BLACK in reyes:
        total -= tabla_rey[_indice_espejo(reyes[BLACK])]

    # ---- Final ganado: empujar al rey rival a una esquina ----
    # Sin esto, el bot no sabe como dar mate con dama o torre (la
    # evaluacion no cambia al acercarse al mate). Si un bando va muy por
    # delante en material y estamos en un final, premiamos que el rey
    # rival este lejos del centro y que los dos reyes esten cerca.
    if es_final:
        diferencia = material[WHITE] - material[BLACK]
        if abs(diferencia) >= 300 and WHITE in reyes and BLACK in reyes:
            if diferencia > 0:
                rey_perdedor, rey_ganador = reyes[BLACK], reyes[WHITE]
            else:
                rey_perdedor, rey_ganador = reyes[WHITE], reyes[BLACK]
            distancia_reyes = (
                abs(rey_perdedor % 8 - rey_ganador % 8)
                + abs(rey_perdedor // 8 - rey_ganador // 8)
            )
            bonus = 10 * _distancia_al_centro(rey_perdedor) + 4 * (14 - distancia_reyes)
            total += bonus if diferencia > 0 else -bonus

    return total
