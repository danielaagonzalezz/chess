"""
Movimientos del rey.

El rey se mueve una sola casilla en cualquier direccion: arriba, abajo,
izquierda, derecha y las cuatro diagonales (8 casillas alrededor de el).
Funciona como el caballo: son desplazamientos fijos, no camina en linea.

De momento NO tiene en cuenta el jaque (no comprueba si la casilla de
destino esta atacada) ni el enroque. Eso se anadira mas adelante.
"""

# Los 8 desplazamientos posibles del rey.
# Cada pareja es (cuanto se mueve en columnas, cuanto se mueve en filas).
DESPLAZAMIENTOS_REY = [
    (0, 1),    # arriba
    (1, 1),    # arriba-derecha
    (1, 0),    # derecha
    (1, -1),   # abajo-derecha
    (0, -1),   # abajo
    (-1, -1),  # abajo-izquierda
    (-1, 0),   # izquierda
    (-1, 1),   # arriba-izquierda
]


def obtener_movimientos_rey(board, square, color):
    """
    Devuelve la lista de casillas a las que se puede mover un rey
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.
    """
    destinos_posibles = []

    for delta_columna, delta_fila in DESPLAZAMIENTOS_REY:
        destino = square.offset(delta_columna, delta_fila)

        if destino is None:
            # Se sale del tablero: la descartamos.
            continue

        pieza_en_destino = board.get_piece(destino)

        if pieza_en_destino is None:
            destinos_posibles.append(destino)
        elif pieza_en_destino.color != color:
            # Pieza del otro color: el rey puede capturarla.
            destinos_posibles.append(destino)
        # Si hay una pieza del MISMO color, no puede ir ahi.

    return destinos_posibles