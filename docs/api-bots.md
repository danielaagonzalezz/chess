# Referencia del API de bots

Todo lo que necesita un bot para jugar. Un bot **solo mira** la partida y
devuelve una jugada: nunca hace falta tocar el código del juego.

```python
from chess.bots import Bot
from chess.game import Game
from chess.move import Move
```

## `Bot`

`chess.bots.Bot` es la clase base (abstracta) de todos los bots.

| Miembro | Tipo | Descripción |
|---|---|---|
| `name` | atributo de clase (`str`) | Nombre único del bot. Es el que sale en la web y en el catálogo. |
| `choose_move(game)` | método **obligatorio** | Recibe una partida y devuelve la jugada que quiere hacer. |

### Contrato de `choose_move(game)`

- **Entrada.** `game` es una **copia** de la partida real: se pueden probar
  jugadas sobre ella (`game.jugar(...)`) sin afectar a la partida.
- **Salida.** Una `Move` que esté en `game.jugadas_legales()`. Devolver una
  jugada ilegal, `None`, un texto, o lanzar una excepción es un error.
- **Cuándo se llama.** Solo si la partida no ha terminado, así que siempre
  hay al menos una jugada legal.
- **Tiempo.** Ten cuidado con las búsquedas largas: la web y el torneo
  esperan una respuesta. Un límite de unos segundos por jugada es lo razonable
  (la validación falla si pasa de 30 s).
- **Constructor.** Debe poder crearse **sin argumentos** (`MiBot()`), porque
  el catálogo y la validación lo crean así. Los parámetros opcionales con
  valor por defecto están permitidos (por ejemplo `seed=None`).

## `Game`: lo que puede mirar un bot

| Miembro | Descripción |
|---|---|
| `game.jugadas_legales()` | Lista de `Move` legales para quien tiene el turno. |
| `game.turno` | `"white"` o `"black"`: de quién es el turno. |
| `game.board` | El `Board` actual (ver más abajo). |
| `game.esta_en_jaque()` | `True` si quien mueve está en jaque. |
| `game.esta_terminada()` | `True` si la partida ha acabado. |
| `game.resultado` / `game.motivo` | `"1-0"`, `"0-1"`, `"1/2-1/2"` o `None`; y por qué terminó. |
| `game.ganador()` | `"white"`, `"black"` o `None`. |
| `game.historial` | Lista de `Move` jugadas hasta ahora. |
| `game.jugar(jugada)` | Juega una `Move` (o un texto como `"e2e4"`). Lanza `InvalidMoveError` si es ilegal. |
| `game.copy()` | Copia independiente de la partida. |
| `game.fen()` | La posición en notación FEN. `Game.desde_fen(fen)` la reconstruye. |
| `game.clave_posicion()` | Identificador de la posición (sirve para tablas de transposición). |

## `Move`

Una jugada: `Move(origen, destino, promocion=None)`.

| Miembro | Descripción |
|---|---|
| `origen`, `destino` | `Square` de salida y de llegada. |
| `promocion` | `None`, o `QUEEN`, `ROOK`, `BISHOP`, `KNIGHT` si es una promoción. |
| `str(jugada)` | Notación de coordenadas: `"e2e4"`, `"e7e8q"`. |

Se pueden comparar con `==` y usar en conjuntos y diccionarios.

## `Board`, `Piece` y `Square`

```python
from chess.pieces import square_from_algebraic as sq

pieza = game.board.get_piece(sq("e1"))   # Piece o None
pieza.piece_type, pieza.color            # p. ej. KING, "white"
pieza.value()                            # 1, 3, 3, 5, 9 (el rey, 0)

for casilla, pieza in game.board.all_pieces():   # todas las piezas
    ...
```

- `Board.get_piece(square)` → `Piece` o `None`; `Board.all_pieces()` → lista de
  `(Square, Piece)`.
- Tipos de pieza: `PAWN`, `KNIGHT`, `BISHOP`, `ROOK`, `QUEEN`, `KING`
  (en `chess.pieces`). Colores: `WHITE`, `BLACK`.
- `square_from_algebraic("e4")` crea una casilla; `str(casilla)` la escribe.

## Catálogo `BOTS`

`chess.bots.BOTS` es un diccionario `nombre → función que crea el bot`. La
interfaz web y los tests de validación lo usan: **un bot que está en `BOTS`
aparece solo en la web y se valida solo en los tests.**

```python
from chess.bots import BOTS

bot = BOTS["minimax-3"]()
jugada = bot.choose_move(game)
```

## Validación: `chess.bots.validacion`

`validar_bot(bot)` comprueba que un bot cumple el contrato. Lanza
`BotInvalidoError` con un mensaje claro si no lo cumple. Prueba el bot en
posiciones difíciles (jaque con una única respuesta, enroque, captura al
paso, promoción, finales) con blancas y con negras, y en unas jugadas de
partida real contra `RandomBot`.

```bash
python -m chess.bots.validacion mi_modulo.MiBot   # una clase tuya
python -m chess.bots.validacion minimax-2         # un bot del catálogo
python -m chess.bots.validacion --todos           # todo el catálogo
```

```python
from chess.bots.validacion import validar_bot
validar_bot(MiBot())
```

## Errores

Todos heredan de `chess.exceptions.ChessError`:

| Excepción | Cuándo |
|---|---|
| `InvalidMoveError` | Se juega una jugada ilegal. |
| `GameOverError` | Se juega en una partida ya terminada. |
| `InvalidFenError` | Un FEN mal escrito. |
| `InvalidSquareError` | Una casilla fuera del tablero. |
