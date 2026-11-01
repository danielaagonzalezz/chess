# Tutorial: sube tu propio bot

De principio a fin: desde clonar el repositorio hasta tener tu bot
fusionado y jugando en la web. Necesitas Python 3.9+ y `git`.

Al terminar tendrás un bot propio, validado automáticamente, listo para
que lo juegue cualquiera desde la [web](web-estatica.md).

## 1. Prepara el repositorio

Haz un *fork* del repositorio en GitHub (botón **Fork**) y clónalo:

```bash
git clone https://github.com/TU-USUARIO/chess.git
cd chess
python -m pip install -e . pytest
python -m pytest        # todo debe pasar antes de empezar
```

Crea una rama para tu bot (no se trabaja en `main`, que está protegida):

```bash
git checkout -b bot/mi-bot
```

## 2. Escribe el bot

Crea el fichero `src/chess/bots/mi_bot.py`. Un bot hereda de `Bot`, tiene un
`name` y escribe `choose_move`. Este ejemplo prefiere capturar la pieza de
más valor que pueda y, si no hay capturas, juega al azar:

```python
"""Mi bot: captura lo mas valioso que pueda."""

import random

from chess.bots.base import Bot


class MiBot(Bot):
    """Prefiere la captura de mayor valor; si no hay, al azar."""

    name = "mi-bot"

    def __init__(self, seed=None):
        self._azar = random.Random(seed)

    def choose_move(self, game):
        mejor, valor_mejor = [], 0
        for jugada in game.jugadas_legales():
            pieza = game.board.get_piece(jugada.destino)
            valor = pieza.value() if pieza is not None else 0
            if valor > valor_mejor:
                mejor, valor_mejor = [jugada], valor
            elif valor == valor_mejor and valor > 0:
                mejor.append(jugada)
        if mejor:
            return self._azar.choice(mejor)
        return self._azar.choice(game.jugadas_legales())
```

Reglas del contrato (todas en la [referencia del API](api-bots.md)):

- `choose_move` recibe una **copia** de la partida: puedes probar jugadas en
  ella con `game.jugar(...)` sin afectar a la real.
- Debe devolver una `Move` de `game.jugadas_legales()`.
- El constructor debe poder llamarse sin argumentos.
- No toques ningún fichero del juego: tu bot solo añade un fichero nuevo.

## 3. Regístralo en el catálogo

Abre `src/chess/bots/__init__.py`, importa tu clase y añádela a `BOTS`:

```python
from chess.bots.mi_bot import MiBot
...
BOTS = {
    ...
    MiBot.name: MiBot,
}
```

Y añádela a `__all__` al final del fichero. Con esto el bot **aparece solo
en la web y entra en los tests y en el torneo**.

## 4. Valídalo

```bash
python -m chess.bots.validacion mi-bot
```

Si todo va bien verás `OK  mi-bot`. Si no, el mensaje te dice qué ha fallado
y en qué posición (jugada ilegal, excepción, tiempo excesivo...). Esta
validación es la misma que ejecutan los tests del repositorio, así que si
pasa aquí, pasará en el *pull request*.

Para ver cómo juega, enfréntalo a otro bot:

```python
from chess.bots import BOTS
from chess.game import Game

game = Game()
blancas, negras = BOTS["mi-bot"](), BOTS["minimax-2"]()
while not game.esta_terminada():
    bot = blancas if game.turno == "white" else negras
    game.jugar(bot.choose_move(game.copy()))
print(game.resultado, game.motivo)
```

## 5. Tests propios (opcional, recomendable)

La validación general se aplica sola. Si tu bot tiene un comportamiento
concreto, pruébalo en `tests/test_mi_bot.py`:

```python
from chess.bots.mi_bot import MiBot
from chess.game import Game


def test_captura_la_dama_si_puede():
    game = Game.desde_fen("4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1")
    assert str(MiBot(seed=0).choose_move(game)) == "e4d5"
```

```bash
python -m pytest
```

## 6. Abre el pull request

```bash
git add src/chess/bots/mi_bot.py src/chess/bots/__init__.py tests/test_mi_bot.py
git commit -m "Añade MiBot"
git push -u origin bot/mi-bot
```

En GitHub, abre un *pull request* hacia `main` del repositorio original. La
plantilla del PR trae una lista de comprobación. Al abrirlo, GitHub Actions
ejecuta **todos los tests**, incluida la validación de tu bot. Si falla,
corrige, haz otro `commit` y `push`: el PR se actualiza solo.

Un revisor mirará que el bot cumple el contrato, que no modifica el código
del juego y que no hace trampas (por ejemplo, no debe leer ficheros ni usar
internet). Cuando se apruebe, se fusiona y tu bot ya está en el repositorio.

## Resumen rápido

| Paso | Comando / fichero |
|---|---|
| Rama | `git checkout -b bot/mi-bot` |
| Bot | `src/chess/bots/mi_bot.py` (`Bot`, `name`, `choose_move`) |
| Registro | `src/chess/bots/__init__.py` → `BOTS` |
| Validación | `python -m chess.bots.validacion mi-bot` |
| Tests | `python -m pytest` |
| Entrega | `git push` y *pull request* a `main` |

## Problemas frecuentes

| Mensaje | Causa |
|---|---|
| `jugada ilegal` | Devuelves una jugada que no está en `game.jugadas_legales()`. |
| `choose_move debe devolver una Move` | Devuelves un texto como `"e2e4"` o `None`. Usa `Move`. |
| `choose_move lanzó ...` | Una excepción dentro de tu bot. El mensaje dice cuál. |
| `tardó N s` | Tu búsqueda es demasiado lenta; añade un límite de tiempo o profundidad. |
| `TypeError` al crear el bot | El constructor pide argumentos obligatorios o falta `choose_move`. |
