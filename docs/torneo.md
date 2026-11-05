# `torneo.py` — el torneo y la clasificación

El torneo enfrenta a **todos los bots del catálogo `BOTS`** y produce una
clasificación. Se ejecuta solo en GitHub Actions y se publica en la web, junto
al tablero para jugar, en `clasificacion.html`. Un bot nuevo entra en el torneo
en cuanto se registra en `BOTS`: no hay que hacer nada más.

## Cómo se juega

- **Todos contra todos.** Cada pareja de bots juega varias partidas (2 por
  defecto), la mitad con cada color.
- **Aperturas al azar.** Casi todos los bots son deterministas y repetirían
  siempre la misma partida. Por eso cada pareja empieza tras unas jugadas al
  azar (4 medias jugadas), **iguales para los dos bots de la pareja**, así que
  ninguno sale favorecido.
- **Puntuación.** Victoria 1, tablas ½, derrota 0.
- **Elo aproximado.** Se ajusta para que los resultados esperados coincidan
  con los reales. La media del torneo vale 1000. Un bot que lo gana todo tiene
  un Elo alto, pero finito.
- **Límite de jugadas.** Si una partida pasa de 160 medias jugadas (60 en
  GitHub Actions) se da por tablas, para acotar el tiempo del torneo.

## Un bot que falla no rompe el torneo

Cada bot juega **en su propio proceso**, y quien arbitra es el torneo, que
guarda la partida real y comprueba cada jugada. Por eso:

| Qué hace el bot | Qué pasa | Motivo en los resultados |
|---|---|---|
| Lanza una excepción | Pierde esa partida | `excepcion` |
| Devuelve una jugada ilegal, `None` o un texto | Pierde esa partida | `ilegal` |
| Tarda más del tiempo máximo (15 s por jugada) | Pierde esa partida y se mata su proceso | `tiempo` |
| Se cae del todo (`os._exit`, un fallo grave...) | Pierde esa partida | `caida` |
| No consigue crearse | Pierde esa partida | `arranque` |

El torneo sigue con el resto de partidas. Cada fallo se cuenta en la columna
**Fallos** de la clasificación. Si fallan los dos bots a la vez al arrancar, la
partida es de tablas. Los tests (`tests/test_torneo.py`) lo comprueban con bots
rotos, tramposos, colgados y que se caen.

## Ejecutarlo en tu ordenador

```bash
python -m chess.torneo                                   # todos los bots
python -m chess.torneo --bots aleatorio,1-paso,minimax-2 # solo algunos
python -m chess.torneo --partidas 4 --paralelo 4         # más partidas, 4 a la vez
python -m chess.torneo --salida resultados/              # carpeta de salida
```

| Opción | Por defecto | Significado |
|---|---|---|
| `--bots` | todos | Nombres de `BOTS` separados por comas. |
| `--partidas` | 2 | Partidas por pareja (siempre un número par). |
| `--paralelo` | 1 | Partidas jugadas a la vez. Usa como máximo el número de núcleos de tu ordenador: los bots con límite de tiempo piensan menos si van justos de CPU. |
| `--max-jugadas` | 160 | Medias jugadas máximas por partida. |
| `--tiempo` | 15 | Segundos máximos por jugada. |
| `--semilla` | 0 | Cambia las aperturas al azar. |
| `--salida` | `clasificacion` | Carpeta donde se escriben los resultados. |

Escribe tres ficheros en la carpeta de salida:

- `clasificacion.html`: la página que se publica.
- `clasificacion.md`: la tabla en markdown.
- `clasificacion.json`: todos los datos, con **todas las partidas** (jugadas
  en notación de coordenadas, para repetirlas o analizarlas).

## Desde Python

```python
from chess.torneo import jugar_torneo, a_markdown

torneo = jugar_torneo(paralelo=2)          # todos los bots de BOTS
print(a_markdown(torneo))

# O con tus propios bots: un diccionario {nombre: función que crea el bot}.
from chess.bots import RandomBot
torneo = jugar_torneo({"a": RandomBot, "b": RandomBot})
```

!!! note "Windows y macOS"
    Cada bot se lanza con `multiprocessing` en modo *spawn*. Los bots de
    `BOTS` funcionan sin más. Si pasas tus propios bots a `jugar_torneo`,
    deben poder enviarse a otro proceso: una clase o una función definida a
    nivel de módulo, no una `lambda`.

## Publicación automática

El workflow `.github/workflows/pages.yml` se ejecuta al fusionar algo en
`main`:

1. Prepara la web (`web_static/build.py`).
2. Juega el torneo (`python -m chess.torneo --partidas 2 --max-jugadas 60
   --paralelo 4`), **salvo que el código de `src/chess` no haya cambiado**: en
   ese caso reutiliza la clasificación anterior (caché), porque los resultados
   serían los mismos.
3. Copia `clasificacion.html` y `clasificacion.json` a la web y escribe la tabla
   en el resumen del workflow.
4. Publica todo en GitHub Pages.

Si el torneo falla, la web con el tablero se publica igualmente.

Así, cuando se fusiona el PR de un bot nuevo, la clasificación se actualiza
sola con ese bot incluido.
