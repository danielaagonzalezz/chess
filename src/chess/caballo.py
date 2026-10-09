"""
Movimientos del caballo.
 
La funcion recibe el tablero, la casilla donde esta el caballo, y el
color de esa pieza, y devuelve una lista de casillas a las que se
puede mover (sin tener en cuenta el jaque todavia, eso lo añadiremos
mas adelante en otro archivo).
 
Las demas piezas (peon, alfil, torre, dama, rey) tendran cada una su
propio archivo parecido a este.
"""
 
# Los 8 desplazamientos en forma de L que puede hacer un caballo.
# Cada pareja es (cuanto se mueve en columnas, cuanto se mueve en filas).
DESPLAZAMIENTOS_CABALLO = [
    (1, 2),
    (2, 1),
    (2, -1),
    (1, -2),
    (-1, -2),
    (-2, -1),
    (-2, 1),
    (-1, 2),
]
 
 
def obtener_movimientos_caballo(board, square, color):
    """
    Devuelve la lista de casillas a las que se puede mover un caballo
    de color 'color' que esta en la casilla 'square', en el tablero 'board'.
    """
    destinos_posibles = []
 
    for delta_columna, delta_fila in DESPLAZAMIENTOS_CABALLO:
        destino = square.offset(delta_columna, delta_fila)
 
        if destino is None:
            # Esta posicion se sale del tablero, la descartamos.
            continue
 
        pieza_en_destino = board.get_piece(destino)
 
        if pieza_en_destino is None:
            # La casilla esta vacia: el caballo puede ir ahi.
            destinos_posibles.append(destino)
        elif pieza_en_destino.color != color:
            # Hay una pieza del otro color: el caballo puede capturarla.
            destinos_posibles.append(destino)
        # Si hay una pieza del MISMO color, no hacemos nada:
        # no se puede ir a una casilla ocupada por tu propia pieza.
 
    return destinos_posibles