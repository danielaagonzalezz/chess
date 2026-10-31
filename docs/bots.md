# `bots/` — los jugadores automáticos

Un **bot** es un jugador automático. Mira la partida y devuelve la jugada
que quiere hacer. No necesita tocar el código del juego.

## Cómo se escribe un bot

1. Heredar de `Bot`.
2. Poner un `name`.
3. Escribir `choose_move(game)`, que devuelve una jugada **legal**.

```python
from chess.bots import Bot


class PrimerBot(Bot):
    name = "primero"

    def choose_move(self, game):
        return game.jugadas_legales()[0]
```

## Reglas del contrato

- `choose_move` recibe una **copia** de la partida: el bot puede probar
  jugadas sobre ella (`game.jugar(...)`) sin afectar a la partida real.
- Debe devolver una `Move` que esté en `game.jugadas_legales()`.
- Solo se llama cuando la partida no ha terminado, así que siempre hay al
  menos una jugada legal.

## Bots disponibles

| Nombre | Clase | Qué hace |
|---|---|---|
| `aleatorio` | `RandomBot` | Elige una jugada legal al azar |
| `1-paso` | `GreedyBot` | Mira una jugada por delante y elige la que mejor deja el tablero |
| `minimax-2` | `MinimaxBot(2)` | Piensa 2 jugadas por delante (rápido) |
| `minimax-3` | `MinimaxBot(3)` | Piensa 3 jugadas por delante (juega bien) |
| `minimax-4` | `MinimaxBot(4, tiempo=5)` | Hasta 4 jugadas por delante, con un máximo de 5 segundos por jugada |
| `ml-2`, `ml-4`, `ml-6` | `MLBot(profundidad=N)` | Evaluación **aprendida** de partidas reales + búsqueda rápida, N jugadas por delante |
| `ml-3s` | `MLBot(tiempo=3, libro=True)` | Lo mismo, pensando hasta 3 segundos por jugada y con libro de aperturas aprendido. El más fuerte |

El catálogo `BOTS` (en `chess/bots/__init__.py`) asocia cada nombre con una
función que crea el bot. La interfaz web lo usa para ofrecer los rivales.

## La evaluación (`evaluacion.py`)

Para decidir sin llegar al final de la partida hace falta estimar si una
posición es buena. `evaluar(board)` devuelve un número en *centipeones*
(100 = un peón): **positivo si van mejor las blancas**, negativo si van
mejor las negras. Suma dos cosas:

- **Material**: peón 100, caballo 320, alfil 330, torre 500, dama 900.
- **Posición**: un bonus según la casilla de cada pieza (un caballo en el
  centro vale más que en la esquina; un peón avanzado, más que uno
  atrasado). Son las tablas de la *Simplified Evaluation Function* de
  Tomasz Michniewski.

En los finales, el rey va al centro en vez de esconderse, y si un bando va
muy por delante se premia arrinconar al rey rival: sin esto, el bot no sabría
cómo dar mate con una dama o una torre.

## `GreedyBot` (`1-paso`) — el codicioso

Para cada jugada legal, la prueba en una copia y evalúa el tablero que
queda. Elige la mejor (al azar entre empates) y siempre da mate si puede.
Captura todo lo que puede, pero **no piensa en la respuesta del rival**:
puede capturar un peón defendido con la dama y perderla.

## `MinimaxBot` — piensa por adelantado

**Minimax.** Se construye un árbol de jugadas: cada nivel es un turno. En
las hojas se evalúa el tablero. Yo elijo la jugada que me deja lo mejor
posible *suponiendo que el rival responderá lo mejor posible*.

**Negamax.** Como en el ajedrez lo que gana uno lo pierde el otro, basta
una sola función: el valor para quien mueve es el máximo de *menos* el
valor de cada respuesta.

**Poda alfa-beta.** Si ya hay una rama mejor, no se sigue mirando una peor.
Da exactamente el mismo resultado que minimax, pero mira muchas menos
posiciones, sobre todo si se prueban primero las capturas más prometedoras
(*move ordering*).

**Búsqueda de capturas (quiescencia).** Al llegar a la profundidad máxima se
siguen mirando solo las capturas hasta que la posición se calma. Evita el
error de creer que se gana un peón cuando en la jugada siguiente te capturan
la dama.

**Profundización iterativa.** Se busca con profundidad 1, luego 2, luego 3...
y cada vuelta empieza por la mejor jugada de la anterior, así que la poda
corta mucho más. Permite además un **límite de tiempo** (`tiempo=5`): si se
acaba, el bot juega lo mejor de la última vuelta completa.

**Tabla de transposición.** La misma posición se alcanza por caminos
distintos (`1.e4 e5 2.Cf3` o `1.Cf3 e5 2.e4`). Se guarda el valor de cada
posición ya analizada para no calcularlo dos veces. Cada entrada dice si el
valor es exacto o solo una cota (por la poda). `Game.clave_posicion()`
identifica cada posición.

**Killer moves.** Una jugada tranquila que ha provocado una poda en una rama
probablemente vuelva a podar en las vecinas, así que se prueba pronto.

**Mates.** Un mate vale `PUNTOS_MATE` menos el número de jugadas que
cuesta, así que prefiere el mate más rápido y retrasa su propia derrota.

### Qué sabemos de su nivel

- Da mate en una y mate en dos, y no cae en la trampa de capturar un peón
  defendido con la dama (el codicioso sí).
- Gana a `aleatorio` y a `1-paso` jugando con blancas y con negras.
- Da mate con rey y dama contra rey.
- Con profundidad 3 tarda entre 0,2 y 4 s por jugada (Python puro). La
  profundidad 4 puede tardar bastante más en posiciones con mucha táctica,
  por eso `minimax-4` lleva un límite de tiempo.

Es un buen rival para un jugador casual o principiante; un jugador de club
con experiencia o un motor profesional le ganarían.

## `MLBot` — evaluación aprendida de partidas reales

El código está en `ml_bot.py`, `motor_rapido.py`, `evaluacion_ml.py`,
`caracteristicas.py` y `libro.py`; el entrenamiento, en `training/` (con su
propio `README.md`, que explica cómo reproducirlo).

**Qué se aprende.** En vez de escribir a mano cuánto vale cada pieza en cada
casilla, un modelo lo **ajusta con partidas reales de Lichess**. De unas 79 000
partidas de jugadores de 1600 Elo o más se sacaron 780 000 posiciones
tranquilas, cada una con el resultado final de su partida. Una **regresión
logística** busca los pesos para que
`P(ganan blancas) = sigmoide(evaluación / escala)` prediga bien esos resultados.
La evaluación es una suma de pesos:

- por **pieza y casilla**, con un juego para el medio juego y otro para el final
  que se mezclan según el material que queda (así el rey aprende solo a esconderse
  al principio y a ir al centro al final);
- por **característica contada** (`caracteristicas.py`): peones doblados, aislados,
  pasados (según la fila), conectados, pareja de alfiles, torre en columna abierta o
  semiabierta, torre en séptima, escudo de peones del rey y tener el turno.

Los pesos parten de la evaluación a mano y el valor medio de cada pieza
(1, 3, 3, 5, 9) se deja fijo: lo que aprende de las partidas es *dónde está mejor
cada pieza* y cuánto valen esas características (peón doblado: unos −23 cp, torre en
columna abierta: unos +50 cp, tener el turno: unos +18 cp...). Sin fijar el material,
el modelo lo infravaloraba (en la apertura casi siempre está igualado) y el bot
regalaba piezas.

**Un libro de aperturas aprendido.** `training/crear_libro.py` cuenta qué jugada se
hace en cada posición de las primeras 16 medias jugadas y se queda con las más
frecuentes. `ml-3s` juega una al azar, ponderada por frecuencia: conoce aperturas
reales y no repite siempre la misma partida. Fuera del libro, piensa.

**Un motor de búsqueda rápido.** Las jugadas legales de `game.py` se calculan
probando cada jugada, y cuestan ~1 ms por posición. `motor_rapido.py` es un segundo
motor *solo para buscar*: tablero como lista de 64 enteros, jugadas que se hacen y se
deshacen sobre el mismo tablero, generación con tablas precalculadas y hash de
Zobrist incremental. Hace unas 60 000–100 000 posiciones por segundo (el motor
anterior, unas 3 700) y llega a profundidad 7–10 en 3 s. Sobre ese motor, la búsqueda
usa las mejoras de los motores de ajedrez reales: negamax con poda alfa-beta,
profundización iterativa con límite de tiempo, tabla de transposición, búsqueda de
capturas, extensión por jaque, **poda por jugada nula**, **reducción de jugadas
tardías (LMR)**, búsqueda de variante principal, killers e historial.

**Las reglas siguen siendo las de `game.py`.** El bot convierte la partida al motor
rápido (con `game.fen()`), busca, y comprueba la jugada contra
`game.jugadas_legales()` antes de devolverla. Los tests comparan los dos motores:
mismas jugadas legales y mismo hash en miles de posiciones de partidas aleatorias,
y el recuento `perft` en las posiciones de referencia de la comunidad.

### Qué sabemos de su nivel

Todas las medidas son partidas entre bots, con colores alternados y aperturas
aleatorias (`training/duelo.py`):

| Enfrentamiento | Resultado |
|---|---|
| `ml` 1 s por jugada contra `minimax-4` (hasta 5 s) | **11 victorias, 0 tablas, 1 derrota** (92 %) |
| `ml-4` contra `minimax-3` | 10 − 3 − 3 (72 %) |
| Con características contadas contra solo tablas, 0,4 s por jugada | 10 − 6 − 4 (65 %, unos +108 Elo) |

Con tan pocas partidas el margen de error es grande, pero la diferencia con los bots
anteriores es clara. No se ha medido contra jugadores humanos ni motores externos.

## Hacer jugar a dos bots

```python
from chess.bots import GreedyBot, MinimaxBot
from chess.game import Game

game = Game()
blancas, negras = MinimaxBot(3, seed=1), GreedyBot(seed=1)
while not game.esta_terminada():
    bot = blancas if game.turno == "white" else negras
    game.jugar(bot.choose_move(game.copy()))
print(game.resultado, game.motivo)
```
