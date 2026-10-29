"""
Reglas: jaque, jugadas legales y enroque.

Los archivos de movimientos (caballo.py, movimientos_torre.py...) solo
calculan a donde puede ir cada pieza segun como se mueve ("pseudo-legal").
Este archivo anade lo que falta para que una jugada sea de verdad legal:

- Una jugada es ilegal si deja al propio rey en jaque.
- El enroque, que es una jugada especial del rey con condiciones propias.

La idea para saber si una jugada es legal es sencilla: la probamos en una
COPIA del tablero y miramos si nuestro rey queda en jaque. Si queda, la
jugada es ilegal. Asi no hace falta tratar por separado los clavados, los
jaques descubiertos, la captura al paso, etc.: todo sale solo.

Los "derechos de enroque" son un conjunto de letras (como en FEN):
    "K" = el blanco puede enrocar corto    "Q" = el blanco puede enrocar largo
    "k" = el negro puede enrocar corto     "q" = el negro puede enrocar largo
"""

from chess.board import Board
from chess.exceptions import InvalidMoveError
from chess.move import Move, aplicar_jugada, PIEZAS_DE_PROMOCION
from chess.movimientos import obtener_movimientos
from chess.pieces import (
    Piece, Square, opposite_color,
    WHITE, PAWN, ROOK, KING,
)


def copiar_tablero(board):
    """
    Devuelve un tablero nuevo con las mismas piezas que 'board'.

    Las piezas (Piece) nunca se modifican, solo se mueven de casilla,
    asi que basta con copiar la lista de casillas.
    """
    copia = Board()
    copia.squares = list(board.squares)
    return copia


def _sentido_del_peon(color):
    """+1 si el peon sube por el tablero (blanco), -1 si baja (negro)."""
    if color == WHITE:
        return 1
    return -1


# =========================================================
# CASILLAS ATACADAS Y JAQUE
# =========================================================

def encontrar_rey(board, color):
    """Devuelve la casilla del rey de ese color, o None si no hay ninguno."""
    for casilla, pieza in board.all_pieces():
        if pieza.piece_type == KING and pieza.color == color:
            return casilla
    return None


def casilla_atacada(board, casilla, por_color):
    """
    True si alguna pieza de 'por_color' ataca esa casilla.

    Una pieza ataca las casillas a las que podria mover para capturar.
    Para casi todas las piezas eso coincide con sus movimientos. La
    excepcion es el peon: avanza recto pero ataca en diagonal, asi que
    lo tratamos aparte.
    """
    for origen, pieza in board.all_pieces():
        if pieza.color != por_color:
            continue

        if pieza.piece_type == PAWN:
            sentido = _sentido_del_peon(por_color)
            for delta_columna in (-1, 1):
                if origen.offset(delta_columna, sentido) == casilla:
                    return True
        else:
            if casilla in obtener_movimientos(board, origen):
                return True

    return False


def esta_en_jaque(board, color):
    """True si el rey de ese color esta siendo atacado."""
    casilla_rey = encontrar_rey(board, color)
    if casilla_rey is None:
        return False
    return casilla_atacada(board, casilla_rey, opposite_color(color))


# =========================================================
# ENROQUE
# =========================================================

def _fila_trasera(color):
    """Fila (rank 0-7) donde empiezan rey y torres de ese color."""
    if color == WHITE:
        return 0
    return 7


def jugadas_de_enroque(board, color, derechos_enroque):
    """
    Devuelve las jugadas de enroque que puede hacer 'color' ahora mismo.

    Un enroque se escribe como la jugada del rey: e1g1 (corto) o e1c1
    (largo), y en negras e8g8 y e8c8. Para poder hacerlo hace falta:
      1. Que ese enroque no se haya perdido (rey y torre sin moverse).
      2. Que el rey y la torre sigan en su sitio.
      3. Que las casillas entre ellos esten vacias.
      4. Que el rey no este en jaque, ni pase por una casilla atacada,
         ni acabe en una casilla atacada.
    """
    fila = _fila_trasera(color)
    rival = opposite_color(color)
    casilla_rey = Square(4, fila)

    if board.get_piece(casilla_rey) != Piece(KING, color):
        return []
    if casilla_atacada(board, casilla_rey, rival):
        return []

    jugadas = []
    torre = Piece(ROOK, color)

    # ---- Enroque corto: el rey va a la columna g, la torre de la h a la f ----
    letra_corto = "K" if color == WHITE else "k"
    if letra_corto in derechos_enroque and board.get_piece(Square(7, fila)) == torre:
        f = Square(5, fila)
        g = Square(6, fila)
        libres = board.is_empty(f) and board.is_empty(g)
        if libres and not casilla_atacada(board, f, rival) \
                and not casilla_atacada(board, g, rival):
            jugadas.append(Move(casilla_rey, g))

    # ---- Enroque largo: el rey va a la columna c, la torre de la a a la d ----
    letra_largo = "Q" if color == WHITE else "q"
    if letra_largo in derechos_enroque and board.get_piece(Square(0, fila)) == torre:
        b = Square(1, fila)
        c = Square(2, fila)
        d = Square(3, fila)
        libres = board.is_empty(b) and board.is_empty(c) and board.is_empty(d)
        # La casilla b puede estar atacada: solo la cruza la torre, no el rey.
        if libres and not casilla_atacada(board, c, rival) \
                and not casilla_atacada(board, d, rival):
            jugadas.append(Move(casilla_rey, c))

    return jugadas


def actualizar_derechos_enroque(derechos_enroque, move):
    """
    Devuelve los derechos de enroque que quedan despues de hacer 'move'.

    Truco: se pierde un derecho cuando se toca (sale o es capturada) una
    de las casillas "clave": las esquinas de las torres y la casilla
    inicial del rey. Asi cubrimos de golpe que el rey se mueva, que se
    mueva una torre o que capturen una torre sin haberse movido.
    """
    casillas_clave = {
        "a1": "Q", "h1": "K", "e1": "KQ",
        "a8": "q", "h8": "k", "e8": "kq",
    }
    nuevos = set(derechos_enroque)
    for casilla in (str(move.origen), str(move.destino)):
        if casilla in casillas_clave:
            for letra in casillas_clave[casilla]:
                nuevos.discard(letra)
    return nuevos


def aplicar_jugada_completa(board, move, casilla_al_paso=None):
    """
    Como aplicar_jugada (move.py), pero ademas entiende el enroque.

    Si el rey se mueve dos columnas, es un enroque: mueve tambien la
    torre. En cualquier otro caso, delega en aplicar_jugada.

    OJO: no comprueba que la jugada sea legal (jaques, derechos de
    enroque...). Para eso esta jugadas_legales; la clase Game se encarga
    de llamar a esta funcion solo con jugadas legales.
    """
    pieza = board.get_piece(move.origen)

    es_enroque = (
        pieza is not None
        and pieza.piece_type == KING
        and abs(move.destino.file - move.origen.file) == 2
    )
    if not es_enroque:
        return aplicar_jugada(board, move, casilla_al_paso)

    fila = move.origen.rank
    if move.destino.file == 6:   # enroque corto
        torre_origen = Square(7, fila)
        torre_destino = Square(5, fila)
    else:                        # enroque largo
        torre_origen = Square(0, fila)
        torre_destino = Square(3, fila)

    torre = board.get_piece(torre_origen)
    if torre is None or torre.piece_type != ROOK:
        raise InvalidMoveError("Enroque imposible: no hay torre en " + str(torre_origen))

    board.remove_piece(move.origen)
    board.set_piece(move.destino, pieza)
    board.remove_piece(torre_origen)
    board.set_piece(torre_destino, torre)
    return None


# =========================================================
# JUGADAS LEGALES
# =========================================================

def _llega_al_final(pieza, destino):
    """True si es un peon que llega a la ultima fila (va a promocionar)."""
    if pieza.piece_type != PAWN:
        return False
    if pieza.color == WHITE:
        return destino.rank == 7
    return destino.rank == 0


def jugadas_pseudolegales(board, color, casilla_al_paso=None):
    """
    Todas las jugadas que siguen las reglas de movimiento de las piezas
    de 'color', sin mirar si dejan al rey en jaque y sin enroque.

    Un peon que llega al final genera cuatro jugadas: una por cada pieza
    en la que puede promocionar.
    """
    jugadas = []
    for origen, pieza in board.all_pieces():
        if pieza.color != color:
            continue
        for destino in obtener_movimientos(board, origen, casilla_al_paso):
            if _llega_al_final(pieza, destino):
                for promocion in PIEZAS_DE_PROMOCION:
                    jugadas.append(Move(origen, destino, promocion))
            else:
                jugadas.append(Move(origen, destino))
    return jugadas


def jugadas_legales(board, color, casilla_al_paso=None, derechos_enroque=()):
    """
    Todas las jugadas legales de 'color' en esta posicion.

    - 'casilla_al_paso': casilla de captura al paso, o None.
    - 'derechos_enroque': conjunto de letras "KQkq" (ver arriba).
    """
    legales = []

    for jugada in jugadas_pseudolegales(board, color, casilla_al_paso):
        # Probamos la jugada en una copia y miramos si el rey queda en jaque.
        copia = copiar_tablero(board)
        aplicar_jugada(copia, jugada, casilla_al_paso)
        if not esta_en_jaque(copia, color):
            legales.append(jugada)

    # El enroque ya comprueba por si mismo que no deja al rey en jaque.
    legales.extend(jugadas_de_enroque(board, color, derechos_enroque))
    return legales
