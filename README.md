# chess

[![Jugar al ajedrez](https://img.shields.io/badge/%E2%99%9E%20Jugar-contra%20los%20bots-2f6f5b?style=for-the-badge)](https://danielaagonzalezz.github.io/chess/)
[![Tests](https://github.com/danielaagonzalezz/chess/actions/workflows/tests.yml/badge.svg)](https://github.com/danielaagonzalezz/chess/actions/workflows/tests.yml)
[![Documentación](https://readthedocs.org/projects/chess-ia/badge/?version=latest)](https://chess-ia.readthedocs.io/)

Motor de ajedrez en Python, hecho como práctica de la asignatura de
Inteligencia Artificial. El objetivo final es tener:

1. Un **juego de ajedrez completo**, con una página web para jugar contra un bot.
2. Una **plataforma de bots**, para que cualquiera pueda programar su propio bot de ajedrez.
3. **Bots propios** con distintas estrategias, y un torneo entre ellos.

## Estado del proyecto

- [x] **Juego completo**: piezas, jugadas legales, jaque, enroque, captura al paso,
  promoción, jaque mate y tablas (`src/chess/`), con tests (incluido `perft`)
- [x] **Partida jugable desde código**, sin interfaz (`Game`)
- [x] **Interfaz web** para jugar contra un bot, sin instalar nada: [jugar](https://danielaagonzalezz.github.io/chess/)
- [x] **Plataforma de bots**: API (`Bot`, catálogo `BOTS`), validación automática de
  bots nuevos y [tutorial](docs/subir-un-bot.md)
- [x] **Bots propios**: aleatorio, 1-paso, minimax con poda alfa-beta y `MLBot`
  (evaluación aprendida de partidas de Lichess + libro de aperturas)
- [ ] Torneo entre bots y clasificación automática

## Instalación

Necesitas Python 3.9 o superior.

```bash
git clone https://github.com/danielaagonzalezz/chess.git
cd chess
python -m pip install -e . pytest
```

## Ejecutar los tests

```bash
python -m pytest
```

## Ejemplo de uso

```python
from chess.board import create_initial_board
from chess.move import Move, aplicar_jugada
from chess.movimientos import obtener_movimientos
from chess.pieces import square_from_algebraic as sq

board = create_initial_board()

# ¿A dónde puede ir el caballo de g1?
destinos = obtener_movimientos(board, sq("g1"))
print(sorted(str(d) for d in destinos))  # ['f3', 'h3']

# Jugar 1. e4
aplicar_jugada(board, Move(sq("e2"), sq("e4")))
print(board)
```

Salida de `print(board)`:

```
8  r n b q k b n r
7  p p p p p p p p
6  . . . . . . . .
5  . . . . . . . .
4  . . . . P . . .
3  . . . . . . . .
2  P P P P . P P P
1  R N B Q K B N R
   a b c d e f g h
```

Las piezas blancas se escriben en mayúscula y las negras en minúscula.

## Crear tu propio bot

Un bot es una clase con un `name` y un método `choose_move` que recibe la
partida y devuelve una jugada legal:

```python
from chess.bots import Bot


class PrimerBot(Bot):
    name = "primero"

    def choose_move(self, game):
        return game.jugadas_legales()[0]
```

Para comprobar que cumple el contrato (jugadas legales, sin excepciones, sin
colgarse):

```bash
python -m chess.bots.validacion mi_modulo.PrimerBot
```

El tutorial completo, hasta el *pull request*, está en
[docs/subir-un-bot.md](docs/subir-un-bot.md), y la referencia del API en
[docs/api-bots.md](docs/api-bots.md). Al abrir un PR, GitHub Actions valida
automáticamente todos los bots del catálogo.

## Estructura del proyecto

```
chess/
├── src/chess/
│   ├── pieces.py, board.py       piezas, casillas y tablero
│   ├── movimientos*.py, caballo.py   movimientos de cada pieza
│   ├── move.py                   jugadas y cómo aplicarlas
│   ├── reglas.py                 jaque, jugadas legales, enroque
│   ├── game.py                   la partida completa (Game)
│   └── bots/                     API de bots, catálogo BOTS, validación y bots
├── web/                          interfaz web con Streamlit
├── web_static/                   web estática (Pyodide), publicada en GitHub Pages
├── training/                     entrenamiento del bot aprendido
├── tests/                        tests automáticos (pytest)
├── docs/                         documentación (MkDocs)
└── pyproject.toml
```

## Documentación

   La documentación está publicada en <https://chess-ia.readthedocs.io/es/latest/>. Para verla en tu ordenador:
   
```bash
python -m pip install -r docs/requirements.txt
python -m mkdocs serve
```

y abre <http://127.0.0.1:8000>.

## Cómo trabajamos

- La rama `main` está protegida: los cambios se hacen en una rama y se
  fusionan con un *pull request*.
- Cada PR ejecuta los tests automáticamente con GitHub Actions.

## Licencia

MIT. Consulta el archivo [LICENSE](LICENSE).
