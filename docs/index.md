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
- [ ] Movimientos del peón
- [ ] Jaque, jaque mate y tablas
- [ ] Partida completa jugable desde código
- [ ] Interfaz web
- [ ] Plataforma de bots
- [ ] Bot propio con IA

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
│       └── movimientos_rey.py    (movimientos del rey)
├── tests/                        (los tests automáticos)
└── pyproject.toml
```

Consulta el menú de la izquierda para ver la documentación de cada módulo.