"""
Movimientos del alfil.

Igual que la torre, el alfil camina en linea recta tantas casillas
como quiera, hasta chocar con el borde del tablero o con otra pieza.
La unica diferencia es la direccion: la torre camina recto (arriba,
abajo, izquierda, derecha), el alfil camina en diagonal.
"""

# Las 4 diagonales en las que puede caminar un alfil.
DIRECCIONES_ALFIL = [
    (1, 1),    # diagonal arriba-derecha
    (1, -1),   # diagonal abajo-derecha
    (-1, 1),   # diagonal arriba-izquierda
    (-1, -1),  # diagonal abajo-izquierda
]


def obtener_movimientos_alfil(board, square, color):
    """
    Devuelve la lista de casillas a las que se puede mover un alfil
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.
    """
    destinos_posibles = []

    for delta_columna, delta_fila in DIRECCIONES_ALFIL:
        casilla_actual = square

        while True:
            casilla_actual = casilla_actual.offset(delta_columna, delta_fila)

            if casilla_actual is None:
                # Nos hemos salido del tablero: paramos en esta diagonal.
                break

            pieza_en_destino = board.get_piece(casilla_actual)

            if pieza_en_destino is None:
                destinos_posibles.append(casilla_actual)
            elif pieza_en_destino.color != color:
                destinos_posibles.append(casilla_actual)
                break
            else:
                break

    return destinos_posibles