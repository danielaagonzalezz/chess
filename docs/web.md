# `web/app.py` — la interfaz web

Una página para jugar contra un bot, hecha con [Streamlit](https://streamlit.io).
Usa directamente el motor de ajedrez (`Game`) y los bots del catálogo `BOTS`.

## Ejecutarla en tu ordenador

```bash
python -m pip install -e ".[web]"
python -m streamlit run web/app.py
```

y abre la dirección que aparece (normalmente <http://localhost:8501>).

## Cómo se juega

1. Elige **rival** y **color** en la barra lateral y pulsa *Empezar partida*.
2. Pulsa una pieza tuya: se marca en color junto a las casillas a las que
   puede ir (un punto `●` si está vacía).
3. Pulsa la casilla de destino. El bot responde solo.
4. Si un peón llega al final, la pieza a la que promociona se elige en la
   barra lateral (por defecto, dama).

En la barra lateral también ves el historial de jugadas y la posición en FEN.

## Cómo está hecha

- El estado de la partida vive en `st.session_state` (`game`, `humano`,
  `bot`, `seleccion`).
- Cada casilla es un botón. Al pulsarlo se ejecuta `pulsar_casilla`, que
  decide si es elegir pieza, cambiar de pieza o mover.
- Después de cada jugada tuya, `mover_bot` hace jugar al bot.
- Hay tests en `tests/test_web.py` que "pulsan botones" con el simulador
  de Streamlit (`AppTest`), sin abrir un navegador.

## Publicarla

La app se publica gratis en [Streamlit Community Cloud](https://streamlit.io/cloud):
se conecta el repositorio de GitHub, se elige `web/app.py` como archivo
principal y se obtiene una URL pública. El archivo `requirements.txt` de la
raíz le indica qué instalar.
