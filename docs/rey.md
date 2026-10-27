# `movimientos_rey.py` — el rey

El rey se mueve **una sola casilla** en cualquier dirección: arriba,
abajo, izquierda, derecha y las cuatro diagonales (las 8 casillas que
tiene alrededor).

Funciona como el caballo: son desplazamientos fijos, no camina en línea
recta. Puede capturar una pieza enemiga, pero no ir a una casilla con
una pieza de su mismo color.

## Qué puedes hacer

| Código | Qué hace |
|---|---|
| `obtener_movimientos_rey(board, square, color)` | Devuelve la lista de casillas a las que se puede mover el rey de ese color que está en `square` |

De momento **no tiene en cuenta el jaque** (no comprueba si la casilla de
destino está atacada) **ni el enroque**. Eso se añadirá más adelante.

## Ejemplo

```python
from chess.board import Board
from chess.pieces import Piece, square_from_algebraic, WHITE, KING
from chess.movimientos_rey import obtener_movimientos_rey

board = Board()
casilla = square_from_algebraic("d4")
board.set_piece(casilla, Piece(KING, WHITE))

destinos = obtener_movimientos_rey(board, casilla, WHITE)
print(len(destinos))  # 8
```

## Tests (`test_movimientos_rey.py`)

| Test | Qué comprueba |
|---|---|
| `test_rey_solo_en_el_centro_tiene_8_movimientos` | En el centro de un tablero vacío hay 8 destinos |
| `test_rey_en_esquina_tiene_3_movimientos` | Desde a1 solo hay 3 destinos |
| `test_rey_en_borde_tiene_5_movimientos` | Desde e1 hay 5 destinos |
| `test_rey_solo_se_mueve_una_casilla` | No llega a casillas a dos de distancia |
| `test_rey_no_puede_ir_a_casilla_con_pieza_propia` | No entra en una casilla con pieza propia |
| `test_rey_puede_capturar_pieza_enemiga` | Sí puede capturar una pieza enemiga |
| `test_rey_e1_en_posicion_inicial_no_tiene_movimientos` | El rey inicial está bloqueado |