# `move.py` y `movimientos.py` — las jugadas

Hasta ahora cada pieza sabía **a dónde puede ir**, pero nadie la movía de
verdad. Estos dos módulos dan el paso que falta: elegir una jugada y
aplicarla al tablero.

## `movimientos.py` — "a dónde puede ir la pieza de esta casilla"

Junta las funciones de todas las piezas. Le dices una casilla y él se
fija en qué pieza hay y llama a la función correcta.

| Código | Qué hace |
|---|---|
| `obtener_movimientos(board, square)` | Lista de casillas a las que puede ir la pieza que hay en `square` (lista vacía si no hay pieza) |
| `obtener_movimientos(board, square, casilla_al_paso)` | Igual, permitiendo la captura al paso de un peón |

Son movimientos **pseudo-legales**: siguen las reglas de cada pieza, pero
todavía no comprueban si dejan al propio rey en jaque.

## `move.py` — las jugadas

### La clase `Move`

Una jugada es "mueve la pieza de esta casilla a esta otra":

```python
from chess.move import Move
from chess.pieces import square_from_algebraic, QUEEN

jugada = Move(square_from_algebraic("e2"), square_from_algebraic("e4"))
print(jugada)  # e2e4

# Si un peón llega al final, hay que decir en qué se convierte:
promocion = Move(square_from_algebraic("e7"), square_from_algebraic("e8"), QUEEN)
print(promocion)  # e7e8q
```

La promoción puede ser `QUEEN`, `ROOK`, `BISHOP` o `KNIGHT`.

### Aplicar una jugada

| Código | Qué hace |
|---|---|
| `aplicar_jugada(board, move)` | Mueve la pieza en el tablero y devuelve la pieza capturada (o `None`) |
| `aplicar_jugada(board, move, casilla_al_paso)` | Igual, permitiendo la captura al paso |
| `calcular_casilla_al_paso(board, move)` | Dice si, tras esta jugada, el rival podrá capturar al paso |

`aplicar_jugada` se encarga de los casos especiales:

- **Captura**: la pieza capturada desaparece y se devuelve.
- **Captura al paso**: el peón capturado no está en la casilla de destino
  sino a su lado, y `aplicar_jugada` lo quita de ahí.
- **Promoción**: el peón se sustituye por la pieza elegida.

Lanza `InvalidMoveError` si la jugada no es posible (no hay pieza en el
origen, la pieza no puede ir al destino, falta la promoción o se indica
una donde no corresponde). Si da error, **el tablero no cambia**.

### Cómo se usa la captura al paso

La captura al paso depende de la jugada anterior, así que hay que
recordarla entre turnos:

```python
from chess.board import create_initial_board
from chess.move import Move, aplicar_jugada, calcular_casilla_al_paso
from chess.pieces import square_from_algebraic as sq

board = create_initial_board()

jugada = Move(sq("e2"), sq("e4"))
al_paso = calcular_casilla_al_paso(board, jugada)  # e3  (llamar ANTES de aplicar)
aplicar_jugada(board, jugada)

# En el turno siguiente se le pasa al_paso a aplicar_jugada:
# aplicar_jugada(board, otra_jugada, casilla_al_paso=al_paso)
```

Cuando exista la clase `Game`, será ella quien guarde esta casilla.

## Lo que todavía no hace

- Comprobar **de quién es el turno**.
- Comprobar que la jugada **no deja al propio rey en jaque**.
- El **enroque**.

## Tests

### `test_movimientos.py`

| Test | Qué comprueba |
|---|---|
| `test_casilla_vacia_no_tiene_movimientos` | Una casilla vacía devuelve lista vacía |
| `test_cada_pieza_usa_sus_propios_movimientos` | Cada tipo de pieza da el número de destinos correcto |
| `test_el_color_de_la_pieza_se_toma_del_tablero` | Un peón negro baja aunque no se indique el color |
| `test_posicion_inicial_blancas_tienen_20_movimientos` | En la posición inicial las blancas tienen 20 jugadas |
| `test_casilla_al_paso_llega_hasta_el_peon` | La casilla al paso se pasa bien hasta el peón |

### `test_move.py`

| Test | Qué comprueba |
|---|---|
| `test_move_se_imprime_como_origen_y_destino` | `e2e4` |
| `test_move_con_promocion_se_imprime_con_letra` | `e7e8q`, `a2a1n` |
| `test_dos_moves_iguales_son_iguales` | Comparación con `==` |
| `test_move_es_hashable` | Se puede meter en un `set` |
| `test_move_con_promocion_invalida_da_error` | No se promociona a rey ni a peón |
| `test_mover_peon_inicial_dos_casillas` | Movimiento normal de peón |
| `test_mover_caballo_inicial` | Movimiento normal de caballo |
| `test_captura_devuelve_la_pieza_capturada_y_la_quita_del_tablero` | Captura normal |
| `test_captura_al_paso_quita_el_peon_de_al_lado` | Captura al paso blanca |
| `test_captura_al_paso_de_peon_negro` | Captura al paso negra |
| `test_sin_casilla_al_paso_no_se_puede_capturar_al_paso` | Sin casilla al paso es ilegal |
| `test_calcular_casilla_al_paso_tras_doble_avance` | e2e4 → e3, d7d5 → d6 |
| `test_calcular_casilla_al_paso_es_none_si_no_es_doble_avance` | Otras jugadas → `None` |
| `test_partida_corta_con_captura_al_paso` | 1. e4 a6 2. e5 d5 3. exd6 al paso |
| `test_peon_blanco_promociona_a_dama` | Promoción blanca |
| `test_peon_negro_promociona_a_caballo` | Promoción negra |
| `test_promocion_con_captura` | Promocionar capturando |
| `test_llegar_al_final_sin_elegir_promocion_da_error` | Falta elegir pieza |
| `test_promocionar_fuera_del_final_da_error` | Promoción donde no toca |
| `test_una_pieza_que_no_es_peon_no_puede_promocionar` | Solo los peones promocionan |
| `test_mover_desde_casilla_vacia_da_error` | No hay pieza en el origen |
| `test_jugada_ilegal_da_error_y_no_cambia_el_tablero` | Jugada ilegal, tablero intacto |
| `test_no_se_puede_capturar_pieza_propia` | No se captura pieza propia |