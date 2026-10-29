# `game.py` — la partida completa

La clase `Game` junta todo lo anterior y guarda lo que le falta a un
tablero para ser una partida: de quién es el turno, qué enroques quedan,
la casilla de captura al paso, el historial y el resultado.

Es la clase que usarán la **interfaz web** y los **bots**: se le pregunta
qué jugadas son legales y se le dice cuál se juega.

## Uso básico

```python
from chess.game import Game

game = Game()
game.jugar("e2e4")          # también acepta un objeto Move
game.jugar("e7e5")
print(game.board)
print(game.turno)           # "white"
print(game.jugadas_legales())
```

Las jugadas se escriben como `e2e4`, y con la pieza al promocionar: `e7e8q`
(`q` dama, `r` torre, `b` alfil, `n` caballo).

## Qué guarda un `Game`

| Atributo | Significado |
|---|---|
| `board` | El tablero |
| `turno` | `WHITE` o `BLACK`: quién mueve |
| `derechos_enroque` | Conjunto de letras `"KQkq"` |
| `casilla_al_paso` | Casilla de captura al paso, o `None` |
| `medios_movimientos` | Jugadas desde la última captura o movimiento de peón |
| `numero_jugada` | Número de jugada (empieza en 1, sube tras mover las negras) |
| `historial` | Lista de `Move` jugadas |
| `resultado` | `None` si sigue; `"1-0"`, `"0-1"` o `"1/2-1/2"` |
| `motivo` | Por qué terminó (jaque mate, ahogado...) |

## Métodos

| Código | Qué hace |
|---|---|
| `Game()` | Partida nueva en la posición inicial |
| `Game.desde_fen(fen)` | Partida a partir de una posición en FEN |
| `jugar(jugada)` | Juega una jugada (`Move` o texto). Lanza `InvalidMoveError` si es ilegal y `GameOverError` si la partida ya terminó. Si falla, la partida no cambia |
| `jugadas_legales()` | Lista de jugadas legales (vacía si la partida terminó) |
| `esta_en_jaque()` | `True` si quien mueve está en jaque |
| `esta_terminada()` | `True` si la partida ha terminado |
| `ganador()` | `WHITE`, `BLACK` o `None` (sigue o tablas) |
| `clave_posicion()` | Identifica la posición (piezas, turno, enroques y captura al paso posible); la usan la triple repetición y los bots |
| `copy()` | Copia independiente: los bots pueden probar jugadas sin tocar la partida real |
| `fen()` | La posición actual en FEN |

## Final de partida

| Motivo | Resultado | Cuándo |
|---|---|---|
| Jaque mate | Gana el otro bando | Sin jugadas legales y en jaque |
| Ahogado | Tablas | Sin jugadas legales y sin jaque |
| Material insuficiente | Tablas | Rey solo, rey y un caballo o alfil, o solo alfiles del mismo color |
| Triple repetición | Tablas | La misma posición (piezas, turno, enroques y al paso posible) por tercera vez |
| Regla de los 50 movimientos | Tablas | 100 medios movimientos sin captura ni movimiento de peón |

!!! note "Decisiones de diseño"
    Las tablas por triple repetición y por 50 movimientos se declaran
    **automáticamente** (en el ajedrez de torneo hay que reclamarlas). Así
    una partida entre bots siempre termina. Si en la última jugada se da
    jaque mate, el mate manda sobre cualquier tabla.

## FEN

FEN es el formato estándar para guardar una posición en una línea de texto.
La posición inicial es:

```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

Una posición FEN mal formada lanza `InvalidFenError`.

## Ejemplo: el mate del loco

```python
from chess.game import Game

game = Game()
for jugada in ["f2f3", "e7e5", "g2g4", "d8h4"]:
    game.jugar(jugada)

print(game.resultado)   # 0-1
print(game.motivo)      # jaque mate
print(game.ganador())   # black
```
