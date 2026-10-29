# `web_static/` — la web estática (sin servidor)

Una página para jugar al ajedrez contra los bots que **no necesita
servidor ni instalar nada**: el motor de ajedrez y los bots (Python) se
ejecutan dentro del navegador con [Pyodide](https://pyodide.org). Es la
web que se publica en GitHub Pages.

## Qué hay dentro

| Archivo | Para qué sirve |
|---|---|
| `index.html`, `style.css` | La página y su aspecto |
| `app.js` | El tablero: clics, arrastrar piezas, promoción, historial |
| `worker.js` | Arranca Pyodide en segundo plano y carga el paquete `chess` |
| `bridge.py` | Pequeño puente entre la página y `Game` / `BOTS` |
| `build.py` | Copia `src/chess` a `web_static/py/` (no se sube a git) |

La web **no duplica la lógica del juego**: usa exactamente `src/chess`. Si
se añade un bot nuevo a `BOTS`, aparece solo en el desplegable.

## Probarla en tu ordenador

```bash
python web_static/build.py
python -m http.server -d web_static 8000
```

y abre <http://localhost:8000>. (Hace falta servidor, no vale abrir el
`index.html` con doble clic, porque el navegador bloquea `fetch` en `file://`.)

## Publicarla en GitHub Pages

1. Mueve `web_static/pages.yml` a `.github/workflows/pages.yml`.
2. En GitHub: **Settings → Pages → Source: GitHub Actions** (solo una vez).
3. Al fusionar un PR en `main`, el workflow `.github/workflows/pages.yml`
   ejecuta `build.py` y publica la carpeta `web_static/`.
4. La URL será `https://<usuario>.github.io/chess/`.

## Cómo funciona

- Pyodide es Python compilado a WebAssembly. Se descarga de un CDN la
  primera vez (unos MB) y el navegador lo guarda en caché.
- `worker.js` corre en un *Web Worker*: así el bot puede pensar (hasta 5 s
  con `minimax-4`) sin congelar la página.
- `app.js` habla con Python con mensajes: `nueva`, `jugar`, `mover_bot`,
  `deshacer`. Cada respuesta es el estado completo de la partida en JSON
  (casillas, jugadas legales, historial, jaque, resultado…).
- La página solo deja mover a las casillas que Python declara legales, y
  Python vuelve a comprobarlo: el navegador no decide nada de ajedrez.

Los tests del puente están en `tests/test_web_static.py`.
