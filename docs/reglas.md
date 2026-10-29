# `reglas.py` — jaque, jugadas legales y enroque

Los módulos de movimientos solo saben **cómo se mueve cada pieza**. Este
módulo añade lo que falta para que una jugada sea de verdad legal:

- Una jugada es ilegal si **deja al propio rey en jaque**.
- El **enroque** es una jugada especial del rey con condiciones propias.

## La idea clave

Para saber si una jugada es legal, la **probamos en una copia del tablero**
y miramos si nuestro rey queda en jaque. Si queda, es ilegal. Así no hace
falta tratar por separado las piezas clavadas, los jaques descubiertos o
la captura al paso: todo sale solo de esa comprobación.

## Funciones

| Código | Qué hace |
|---|---|
| `copiar_tablero(board)` | Tablero nuevo e independiente con las mismas piezas |
| `encontrar_rey(board, color)` | Casilla del rey de ese color (o `None`) |
| `casilla_atacada(board, casilla, por_color)` | `True` si alguna pieza de `por_color` ataca la casilla |
| `esta_en_jaque(board, color)` | `True` si el rey de ese color está atacado |
| `jugadas_pseudolegales(board, color, casilla_al_paso)` | Jugadas que siguen el movimiento de las piezas (sin mirar el jaque) |
| `jugadas_legales(board, color, casilla_al_paso, derechos_enroque)` | Todas las jugadas legales, incluido el enroque |
| `jugadas_de_enroque(board, color, derechos_enroque)` | Solo los enroques posibles |
| `aplicar_jugada_completa(board, move, casilla_al_paso)` | Como `aplicar_jugada`, pero entiende el enroque |
| `actualizar_derechos_enroque(derechos, move)` | Derechos que quedan tras una jugada |

!!! note "El peón ataca distinto de como se mueve"
    El peón avanza recto pero ataca en diagonal. Por eso `casilla_atacada`
    trata a los peones aparte: una casilla delante de un peón **no** está
    atacada por él.

## El enroque

Se escribe como la jugada del rey: `e1g1` (corto) y `e1c1` (largo) para las
blancas, `e8g8` y `e8c8` para las negras. Para poder hacerlo:

1. El enroque no se ha perdido (rey y torre sin haberse movido).
2. El rey y la torre siguen en su sitio.
3. Las casillas entre ellos están vacías.
4. El rey **no está en jaque**, no pasa por una casilla atacada y no acaba
   en una casilla atacada.

En el enroque largo la casilla `b` puede estar atacada: solo la cruza la
torre, no el rey.

### Derechos de enroque

Son un conjunto de letras, como en FEN: `"K"` (blanco corto), `"Q"` (blanco
largo), `"k"` (negro corto) y `"q"` (negro largo). Se pierde un derecho
cuando se toca una casilla clave (esquinas de las torres y casilla inicial
del rey), ya sea moviendo esa pieza o capturando la torre:

```python
from chess.reglas import actualizar_derechos_enroque
from chess.move import jugada_desde_texto

derechos = {"K", "Q", "k", "q"}
print(actualizar_derechos_enroque(derechos, jugada_desde_texto("e1e2")))
# {'k', 'q'}   -> el rey blanco se movió: pierde los dos enroques
```

## Ejemplo

```python
from chess.board import create_initial_board
from chess.pieces import WHITE
from chess.reglas import jugadas_legales, esta_en_jaque

board = create_initial_board()
print(len(jugadas_legales(board, WHITE)))  # 20
print(esta_en_jaque(board, WHITE))         # False
```

## Cómo sabemos que es correcto

Además de los tests de cada regla, `tests/test_perft.py` usa **perft**:
cuenta cuántas posiciones se alcanzan jugando N jugadas legales seguidas
desde posiciones de referencia muy conocidas. Nuestro motor da exactamente
los números oficiales, lo que valida de golpe las reglas de jaque, enroque,
captura al paso y promoción.
