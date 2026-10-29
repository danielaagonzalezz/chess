# chess

Motor de ajedrez en Python, hecho como práctica de la asignatura de
Inteligencia Artificial. El objetivo final es tener:

1. Un **juego de ajedrez completo**, con una página web para jugar contra un bot.
2. Una **plataforma de bots**, para que cualquiera pueda programar su propio bot de ajedrez.
3. **Bots propios** con distintas estrategias, y un torneo entre ellos.

## Estado del proyecto

- [x] Piezas, casillas y tablero con la posición inicial
- [x] Movimientos de las seis piezas (caballo, torre, alfil, dama, rey y peón)
- [x] Jugadas (`Move`) y cómo aplicarlas: capturas, captura al paso y promoción
- [ ] Jaque y jugadas legales
- [ ] Enroque
- [ ] Jaque mate y tablas
- [ ] Partida completa jugable desde código
- [ ] Interfaz web
- [ ] Plataforma de bots
- [ ] Bots propios y torneo

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

## Estructura del proyecto

```
chess/
├── src/chess/
│   ├── pieces.py             colores, tipos de pieza y casillas
│   ├── board.py              el tablero
│   ├── caballo.py            movimientos del caballo
│   ├── movimientos_torre.py  movimientos de la torre
│   ├── movimientos_alfil.py  movimientos del alfil
│   ├── movimientos_dama.py   movimientos de la dama
│   ├── movimientos_rey.py    movimientos del rey
│   ├── movimientos_peon.py   movimientos del peón
│   ├── movimientos.py        movimientos de cualquier pieza
│   ├── move.py               jugadas y cómo aplicarlas
│   └── exceptions.py         errores del motor
├── tests/                    tests automáticos (pytest)
├── docs/                     documentación (MkDocs)
└── pyproject.toml
```

## Documentación

La documentación de cada módulo está en la carpeta `docs/` y se publica
con MkDocs en Read the Docs. Para verla en tu ordenador:

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
