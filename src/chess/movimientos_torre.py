"""
Movimientos de la torre.

A diferencia del caballo, la torre no salta a posiciones fijas: camina
en linea recta (arriba, abajo, izquierda, derecha) tantas casillas
como quiera, hasta que choca con el borde del tablero o con otra pieza.
"""

# Las 4 direcciones en las que puede caminar una torre.
# Cada pareja es (cuanto avanza en columnas, cuanto avanza en filas)
# POR CADA PASO, no el desplazamiento total.
DIRECCIONES_TORRE = [
    (0, 1),   # hacia arriba
    (0, -1),  # hacia abajo
    (1, 0),   # hacia la derecha
    (-1, 0),  # hacia la izquierda
]


def obtener_movimientos_torre(board, square, color):
    """
    Devuelve la lista de casillas a las que se puede mover una torre
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.
    """
    destinos_posibles = []

    for delta_columna, delta_fila in DIRECCIONES_TORRE:
        casilla_actual = square

        # Vamos dando pasos en esta direccion, uno detras de otro,
        # hasta que algo nos obligue a parar.
        while True:
            casilla_actual = casilla_actual.offset(delta_columna, delta_fila)

            if casilla_actual is None:
                # Nos hemos salido del tablero: paramos en esta direccion.
                break

            pieza_en_destino = board.get_piece(casilla_actual)

            if pieza_en_destino is None:
                # Casilla vacia: podemos ir ahi, Y podemos seguir caminando
                # mas alla en la misma direccion.
                destinos_posibles.append(casilla_actual)
            elif pieza_en_destino.color != color:
                # Pieza del otro color: podemos capturarla, pero ahi se
                # para el camino, no podemos saltarla ni seguir mas alla.
                destinos_posibles.append(casilla_actual)
                break
            else:
                # Pieza de nuestro propio color: no podemos ir ahi, y
                # tampoco podemos seguir caminando mas alla.
                break

    return destinos_posibles
