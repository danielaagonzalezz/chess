# `movimientos_dama.py` — la dama

La dama se mueve como una **torre y un alfil a la vez**: en línea recta
(arriba, abajo, izquierda, derecha) y en diagonal, tantas casillas como
quiera, hasta chocar con el borde del tablero o con otra pieza.

Por eso no repite código: reutiliza `obtener_movimientos_torre` y
`obtener_movimientos_alfil` y junta sus resultados.

## Qué puedes hacer

| Código | Qué hace |
|---|---|
| `obtener_movimientos_dama(board, square, color)` | Devuelve la lista de casillas a las que se puede mover la dama de ese color que está en `square` |

Igual que el resto de piezas, de momento **no tiene en cuenta el jaque**
(eso se añadirá más adelante).

## Ejemplo

```python
from chess.board import create_initial_board
from chess.pieces import square_from_algebraic, WHITE
from chess.movimientos_dama import obtener_movimientos_dama

board = create_initial_board()
destinos = obtener_movimientos_dama(board, square_from_algebraic("d1"), WHITE)
print(destinos)  # []  (al empezar está rodeada de sus piezas)
```

## Tests (`test_movimientos_dama.py`)

| Test | Qué comprueba |
|---|---|
| `test_dama_sola_en_tablero_vacio_desde_d4_tiene_27_movimientos` | Desde d4 en un tablero vacío hay 27 destinos |
| `test_dama_en_esquina_tiene_21_movimientos` | Desde a1 hay 21 destinos |
| `test_dama_se_mueve_recto_y_en_diagonal` | Llega en recto y en diagonal, pero no en "L" |
| `test_dama_se_para_al_chocar_con_pieza_propia` | No entra en una casilla con pieza propia ni la salta |
| `test_dama_puede_capturar_pero_no_saltar_pieza_enemiga` | Captura la pieza enemiga pero no pasa de ella |
| `test_dama_d1_en_posicion_inicial_no_tiene_movimientos` | La dama inicial está bloqueada |
| `test_dama_no_devuelve_casillas_repetidas` | No hay destinos duplicados |