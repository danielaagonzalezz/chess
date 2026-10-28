# `movimientos_peon.py` — el peón

El peón es la pieza más particular, porque **no captura como se mueve**:

- **Avanza recto** una casilla, pero solo si está vacía. No puede
  capturar hacia delante.
- **Doble avance**: desde su fila inicial puede avanzar dos casillas de
  golpe, si las dos casillas de delante están vacías.
- **Captura en diagonal** hacia delante, y solo si hay una pieza enemiga.
- **Captura al paso** (*en passant*): si el rival acaba de avanzar un peón
  dos casillas y se ha quedado justo a su lado, puede capturarlo como si
  solo hubiera avanzado una.

Los peones **blancos suben** por el tablero y los **negros bajan**.

## Qué puedes hacer

| Código | Qué hace |
|---|---|
| `obtener_movimientos_peon(board, square, color)` | Devuelve la lista de casillas a las que se puede mover el peón de ese color que está en `square` |
| `obtener_movimientos_peon(board, square, color, casilla_al_paso=casilla)` | Igual, pero además permite la captura al paso sobre esa casilla |

`casilla_al_paso` es la casilla **por la que ha pasado** el peón rival al
avanzar dos (por ejemplo `d6` si el negro ha movido `d7` → `d5`). Quien
sabe cuál es es la partida (`Game`), porque hay que recordar la última
jugada; por eso se pasa desde fuera.

## Lo que todavía no hace

- **La promoción** (cuando el peón llega a la última fila y se convierte
  en otra pieza). No cambia a dónde puede ir el peón, sino en qué se
  convierte al llegar, así que se gestionará cuando exista la clase de
  jugada (`Move`).
- **El jaque**: igual que el resto de piezas, no comprueba si deja al rey
  en jaque.

## Ejemplo

```python
from chess.board import create_initial_board
from chess.pieces import square_from_algebraic, WHITE
from chess.movimientos_peon import obtener_movimientos_peon

board = create_initial_board()
destinos = obtener_movimientos_peon(board, square_from_algebraic("e2"), WHITE)
print([str(d) for d in destinos])  # ['e3', 'e4']
```

## Tests (`test_movimientos_peon.py`)

| Test | Qué comprueba |
|---|---|
| `test_peon_blanco_inicial_puede_avanzar_una_o_dos_casillas` | El peón blanco inicial llega a e3 y e4 |
| `test_peon_negro_inicial_puede_avanzar_una_o_dos_casillas` | El peón negro inicial llega a e6 y e5 |
| `test_peon_fuera_de_fila_inicial_solo_avanza_una_casilla` | Fuera de su fila inicial no hay doble avance |
| `test_peon_negro_avanza_hacia_abajo` | Los negros bajan por el tablero |
| `test_peon_bloqueado_por_pieza_delante_no_avanza` | No captura ni salta una pieza que tiene delante |
| `test_peon_no_puede_hacer_doble_avance_si_la_segunda_casilla_esta_ocupada` | El doble avance necesita las dos casillas libres |
| `test_peon_captura_en_diagonal_pieza_enemiga` | Captura a ambos lados en diagonal |
| `test_peon_no_captura_pieza_propia_en_diagonal` | No captura piezas de su color |
| `test_peon_no_se_mueve_en_diagonal_a_casilla_vacia` | Sin pieza enemiga, la diagonal no es un destino |
| `test_peon_negro_captura_en_diagonal_hacia_abajo` | Los negros capturan hacia abajo |
| `test_peon_en_columna_a_solo_captura_hacia_un_lado` | En el borde solo hay una diagonal |
| `test_peon_en_ultima_fila_no_tiene_movimientos` | Al final del tablero no hay casillas delante |
| `test_peon_blanco_captura_al_paso` | Captura al paso de un peón blanco |
| `test_peon_negro_captura_al_paso` | Captura al paso de un peón negro |
| `test_sin_casilla_al_paso_no_hay_captura_al_paso` | Sin `casilla_al_paso`, no hay captura al paso |
| `test_casilla_al_paso_lejana_no_afecta` | Una casilla al paso fuera de sus diagonales se ignora |