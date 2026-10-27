# `board.py` — el tablero

El tablero guarda **qué pieza hay en cada casilla**. Por dentro es solo
un diccionario de 64 casillas (de la 0 a la 63), cada una vacía (`None`)
o con una `Piece` encima.

## Qué puedes hacer con un tablero

| Código | Qué hace |
|---|---|
| `board = Board()` | Crea un tablero vacío, las 64 casillas sin piezas |
| `board = create_initial_board()` | Crea un tablero ya con las 32 piezas colocadas para empezar una partida |
| `board.get_piece(square)` | Te dice qué pieza hay en esa casilla (o `None` si está vacía) |
| `board.set_piece(square, piece)` | Coloca una pieza en esa casilla (borra lo que hubiera antes) |
| `board.remove_piece(square)` | Vacía esa casilla |
| `board.is_empty(square)` | `True` o `False`: ¿está vacía esa casilla? |
| `board.all_pieces()` | Te da una lista con todas las piezas del tablero y en qué casilla está cada una |
| `print(board)` | Dibuja el tablero en texto, para verlo |

## Ejemplo

```python
from chess.board import create_initial_board
from chess.pieces import square_from_algebraic

board = create_initial_board()
print(board)

pieza = board.get_piece(square_from_algebraic("e1"))
print(pieza)  # K  (el rey blanco)
```

## Tests (`test_board.py`)

| Test | Qué comprueba |
|---|---|
| `test_new_board_is_empty` | Un tablero recién creado no tiene ninguna pieza |
| `test_set_and_get_piece` | Si colocas una pieza, luego la puedes leer de vuelta tal cual |
| `test_remove_piece` | Si quitas una pieza, la casilla queda vacía |
| `test_set_piece_overwrites_previous_piece` | Colocar una pieza donde ya había otra, la sustituye |
| `test_empty_board_has_no_pieces` | Un tablero vacío devuelve una lista vacía de piezas |
| `test_initial_board_white_back_rank` | La fila 1 tiene las piezas blancas en el orden correcto |
| `test_initial_board_black_back_rank` | Lo mismo con piezas negras de la fila 8 |
| `test_initial_board_pawns` | Las filas 2 y 7 están llenas de peones |
| `test_initial_board_middle_is_empty` | El centro del tablero está vacío al empezar |
| `test_initial_board_has_32_pieces` | Hay exactamente 32 piezas al empezar |
| `test_board_str_has_9_lines` | Al imprimir el tablero salen 9 líneas |
| `test_board_str_contains_column_letters` | Aparece la línea `a b c d e f g h` |
| `test_board_str_shows_white_rook_on_a1` | La torre blanca aparece en su sitio |
