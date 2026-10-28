"""
Movimientos del peon.

El peon es la pieza mas particular, porque NO captura como se mueve:

- Avanza hacia delante (recto) una casilla, pero solo si esta vacia.
  No puede capturar hacia delante.
- Si esta en su fila inicial, puede avanzar dos casillas de golpe, si
  las dos casillas de delante estan vacias.
- Captura en diagonal hacia delante, y solo si hay una pieza enemiga.
- Captura al paso (en passant): captura en diagonal una casilla vacia
  si el rival acaba de avanzar un peon dos casillas justo a su lado.

Los peones blancos avanzan hacia arriba (rank sube) y los negros hacia
abajo (rank baja).

Nota: la PROMOCION (cuando el peon llega al final) no cambia a donde
puede ir el peon, sino en que se convierte al llegar. Eso se gestionara
mas adelante, cuando exista la clase de jugada (Move).
"""

from chess.pieces import WHITE


def _direccion(color):
    """Devuelve +1 si el peon sube por el tablero (blanco), -1 si baja (negro)."""
    if color == WHITE:
        return 1
    return -1


def _fila_inicial(color):
    """Fila (rank 0-7) donde empiezan los peones de ese color."""
    if color == WHITE:
        return 1  # fila 2
    return 6      # fila 7


def obtener_movimientos_peon(board, square, color, casilla_al_paso=None):
    """
    Devuelve la lista de casillas a las que se puede mover un peon
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.

    'casilla_al_paso' es opcional: si el rival acaba de mover un peon dos
    casillas, es la casilla "por la que ha pasado" (por ejemplo d6 si un
    peon negro acaba de ir de d7 a d5). Si se la pasas, el peon puede
    capturar al paso.
    """
    destinos_posibles = []
    sentido = _direccion(color)

    # ---- Avance recto (solo a casillas vacias) ----
    una_casilla = square.offset(0, sentido)
    if una_casilla is not None and board.is_empty(una_casilla):
        destinos_posibles.append(una_casilla)

        # Doble avance: solo desde la fila inicial y con las dos libres.
        if square.rank == _fila_inicial(color):
            dos_casillas = square.offset(0, 2 * sentido)
            if dos_casillas is not None and board.is_empty(dos_casillas):
                destinos_posibles.append(dos_casillas)

    # ---- Capturas en diagonal ----
    for delta_columna in (-1, 1):
        diagonal = square.offset(delta_columna, sentido)
        if diagonal is None:
            continue

        pieza_en_destino = board.get_piece(diagonal)

        if pieza_en_destino is not None and pieza_en_destino.color != color:
            # Pieza enemiga en la diagonal: se puede capturar.
            destinos_posibles.append(diagonal)
        elif pieza_en_destino is None and diagonal == casilla_al_paso:
            # Captura al paso: la casilla esta vacia, pero es la casilla
            # por la que acaba de pasar el peon rival.
            destinos_posibles.append(diagonal)

    return destinos_posibles