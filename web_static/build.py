"""
Prepara la web estatica: copia el paquete `chess` (src/chess) a web_static/py/
y escribe py/manifest.json con la lista de archivos.

Asi la web usa SIEMPRE el mismo codigo que los tests y los bots, sin
duplicarlo a mano. Se ejecuta antes de publicar (lo hace el workflow de
GitHub Pages) o para probar en local:

    python web_static/build.py
    python -m http.server -d web_static 8000
"""

import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEN = RAIZ / "src" / "chess"
DESTINO = Path(__file__).resolve().parent / "py"


def main():
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    archivos = []
    for ruta in sorted(ORIGEN.rglob("*.py")):
        relativa = ruta.relative_to(ORIGEN.parent)  # chess/board.py
        destino = DESTINO / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ruta, destino)
        archivos.append(relativa.as_posix())
    (DESTINO / "manifest.json").write_text(json.dumps(archivos, indent=2))
    print("Copiados", len(archivos), "archivos a", DESTINO)


if __name__ == "__main__":
    main()
