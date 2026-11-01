# chess

Juego de ajedrez hecho en Python, como práctica de la asignatura de
Inteligencia Artificial. El objetivo final es tener un juego completo,
una página web donde jugar contra un bot, y una plataforma para que
cualquiera pueda programar su propio bot de ajedrez.

## Estado actual del proyecto

- [x] Piezas y casillas del tablero (`pieces.py`)
- [x] Tablero y posición inicial (`board.py`)
- [x] Movimientos del caballo (`caballo.py`)
- [x] Movimientos de la torre (`movimientos_torre.py`)
- [x] Movimientos del alfil (`movimientos_alfil.py`)
- [x] Movimientos de la dama (`movimientos_dama.py`)
- [x] Movimientos del rey (`movimientos_rey.py`)
- [x] Movimientos del peón (`movimientos_peon.py`)
- [x] Jugadas (`Move`) y aplicarlas al tablero: capturas, captura al paso y promoción (`move.py`)
- [x] Jaque, jugadas legales y enroque (`reglas.py`)
- [x] Jaque mate y tablas, y partida completa jugable desde código (`game.py`)
- [x] Interfaz web con Streamlit (`web/app.py`)
- [x] Web estática publicada en GitHub Pages (`web_static/`)
- [x] Plataforma de bots: API (`Bot`, catálogo `BOTS`), validación automática y [tutorial](subir-un-bot.md) (`bots/`)
- [x] Bots: aleatorio, 1-paso y minimax con poda alfa-beta (`bots/`)
- [x] Bots con IA: evaluación aprendida de partidas de Lichess y libro de aperturas (`MLBot`)
- [ ] Torneo y clasificación automática

## Estructura del proyecto

```
chess/
├── src/
│   └── chess/
│       ├── pieces.py             (colores, tipos de pieza, casillas)
│       ├── board.py              (el tablero)
│       ├── caballo.py            (movimientos del caballo)
│       ├── movimientos_torre.py  (movimientos de la torre)
│       ├── movimientos_alfil.py  (movimientos del alfil)
│       ├── movimientos_dama.py   (movimientos de la dama)
│       ├── movimientos_rey.py    (movimientos del rey)
│       ├── movimientos_peon.py   (movimientos del peón)
│       ├── movimientos.py        (movimientos de cualquier pieza)
│       ├── move.py               (jugadas y cómo aplicarlas)
│       ├── reglas.py             (jaque, jugadas legales, enroque)
│       └── game.py               (la partida completa)
├── tests/                        (los tests automáticos)
└── pyproject.toml
```

Si quieres programar tu propio bot, empieza por el [tutorial](subir-un-bot.md).

Consulta el menú de la izquierda para ver la documentación de cada módulo.