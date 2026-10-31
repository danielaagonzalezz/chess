# Bot con aprendizaje automático (`ml-2`, `ml-4`, `ml-6`, `ml-3s`)

Este directorio contiene todo lo necesario para **reproducir el aprendizaje**
del bot a partir de partidas reales de [Lichess](https://database.lichess.org).
La explicación del bot está en `docs/bots.md`; aquí, cómo se entrena y qué
resultados da.

## Qué se aprende

1. **La función de evaluación.** De cada partida (jugadores de ≥ 1600 Elo,
   terminada de forma normal) se guardan unas posiciones "tranquilas" (sin jaque
   ni captura reciente), cada una con el **resultado final** de su partida. Una
   **regresión logística** ajusta los pesos para que
   `P(ganan blancas) = sigmoide(evaluación / escala)` prediga bien ese resultado.
   La evaluación suma:
   - un peso por **(fase, pieza, casilla)**: 2 × 6 × 64 = 768 números (medio juego
     y final, mezclados según el material que queda);
   - un peso por **característica contada** y fase (`src/chess/bots/caracteristicas.py`):
     peones doblados/aislados/pasados/conectados, pareja de alfiles, torre en
     columna abierta o semiabierta o en séptima, escudo de peones del rey y tener
     el turno.
2. **Un libro de aperturas.** Se cuenta qué jugada se hace en cada posición de las
   primeras 16 medias jugadas y se guardan las más frecuentes.

El modelo **parte de la evaluación a mano** y aprende una corrección. El valor
*medio* de cada pieza (1, 3, 3, 5, 9) se deja fijo: lo que aprende de las partidas
es **dónde está mejor cada pieza** y **cuánto valen las características**. Se hace así
porque en la apertura casi siempre hay material igualado y, sin esa restricción, el
modelo infravaloraba las piezas y el bot las regalaba (ver *Resultados*). Las
características raras se frenan con una regularización propia, porque si no se
desbocan (una torre en séptima llegó a salir con −1250 cp).

Los pesos y el libro viajan dentro del paquete (`src/chess/bots/pesos_eval.json` y
`libro_aperturas.json`) y se usan **sin numpy**.

## Cómo reproducirlo

```bash
# 1. Descarga un mes de partidas (.pgn.zst) de https://database.lichess.org
#    y déjalo, por ejemplo, en data/ (esa carpeta no se sube a git).

# 2. Preparar posiciones y libro. Necesitan python-chess, que se importa también
#    como "chess" y CHOCA con este proyecto: usa un entorno virtual aparte.
python -m venv .venv-datos
.venv-datos/bin/python -m pip install -r training/requirements-datos.txt   # Windows: .venv-datos\Scripts\python
.venv-datos/bin/python training/preparar_datos.py data/lichess_2013-09.pgn.zst \
    --salida data/posiciones.npz --elo-minimo 1600 --por-partida 10
.venv-datos/bin/python training/crear_libro.py data/lichess_2013-09.pgn.zst \
    --salida src/chess/bots/libro_aperturas.json --min-cuota 0.12

# 3. Entrenar (en el entorno normal del proyecto; tarda unos minutos)
python -m pip install -e ".[train]"
python training/entrenar.py data/posiciones.npz --l2 1e-6 --l2-extras 1e-3

# 4. Medir contra otro bot (también con pesos alternativos: ml@ruta.json@0.4)
python training/duelo.py ml-2 minimax-2 --parejas 10
python training/duelo.py ml@data/pesos_nuevos.json@1 minimax-4 --parejas 6
```

## Resultados (septiembre de 2013: 79 193 partidas → 780 795 posiciones)

**Predecir quién gana**, en posiciones *no usadas* para entrenar (error = entropía
cruzada, menor es mejor):

| Evaluación | Error | Acierto |
|---|---|---|
| Sin información | 0.6931 | 47.7 % |
| A mano (`evaluacion.py`) | 0.6025 | 65.0 % |
| Aprendida, solo tablas por casilla | 0.5854 | 67.2 % |
| Aprendida, con características contadas | **0.5833** | **67.4 %** |

**Fuerza de juego** (partidas entre bots, colores alternados, aperturas aleatorias):

| Prueba | Resultado |
|---|---|
| Entrenar solo con datos, sin partir de la evaluación a mano (`ml-2` contra `minimax-2`) | 8.0 / 20 |
| Partiendo de la evaluación a mano, material libre | 5.5 / 20 |
| Partiendo de la evaluación a mano, material fijo (`ml-2` contra `minimax-2`) | 9.5 / 20 |
| Con motor rápido (solo tablas), `ml-4` contra `minimax-3` | 11.5 / 16 |
| Con características contadas contra solo tablas, 0,4 s por jugada | 13.0 / 20 |
| **`ml` 1 s por jugada contra `minimax-4` (hasta 5 s)** | **11 – 0 – 1 (11.0 / 12)** |

Lectura honesta:

- Cambiar *solo la evaluación* (mismo minimax, misma profundidad) dejaba al bot **a la
  par** del minimax a mano, aunque predijera mejor los resultados: una suma de pesos
  por pieza y casilla no basta.
- El salto grande viene de **dos cosas**: un motor de búsqueda unas 20 veces más rápido
  (que mira 7–10 jugadas por delante en vez de 3–4) y la evaluación con características
  contadas (unos +100 Elo a igual tiempo).
- Con 12–20 partidas por prueba, el margen de error es de decenas de puntos de Elo:
  son medidas para comparar, no cifras absolutas. No se ha medido contra jugadores
  humanos ni motores externos.
- Limitaciones: una sola mensualidad de datos (partidas de 2013, nivel medio ~1500),
  sin movilidad de piezas ni seguridad del rey más allá del escudo de peones, y un
  motor en Python (un motor en C haría 100 veces más posiciones por segundo).
