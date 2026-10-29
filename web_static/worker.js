// Worker: carga Pyodide (Python en el navegador) y el motor de ajedrez.
// Corre aparte de la pagina para que el bot pueda "pensar" sin congelarla.

const params = new URL(self.location.href).searchParams;
const PYODIDE_BASE = params.get("pyodide") ||
  "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

importScripts(PYODIDE_BASE + "pyodide.js");

let pyodide = null;
let bridge = null;

async function arrancar() {
  pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });

  // Copiamos el paquete `chess` (lista en py/manifest.json) al sistema de
  // archivos virtual de Pyodide y lo ponemos en el camino de busqueda.
  const manifest = await (await fetch("py/manifest.json")).json();
  const raiz = "/home/pyodide/lib";
  for (const ruta of manifest) {
    const texto = await (await fetch("py/" + ruta)).text();
    const carpeta = raiz + "/" + ruta.split("/").slice(0, -1).join("/");
    pyodide.FS.mkdirTree(carpeta);
    pyodide.FS.writeFile(raiz + "/" + ruta, texto);
  }
  pyodide.runPython(`import sys; sys.path.insert(0, "${raiz}")`);

  const puente = await (await fetch("bridge.py")).text();
  pyodide.FS.writeFile(raiz + "/bridge.py", puente);
  bridge = pyodide.pyimport("bridge");
}

const listo = arrancar().then(
  () => self.postMessage({ tipo: "listo" }),
  (e) => self.postMessage({ tipo: "fallo", error: String(e) }),
);

self.onmessage = async (ev) => {
  const { id, cmd, args } = ev.data;
  try {
    await listo;
    const resultado = bridge[cmd](...(args || []));
    self.postMessage({ tipo: "respuesta", id, resultado: String(resultado) });
  } catch (e) {
    self.postMessage({ tipo: "respuesta", id, error: String(e) });
  }
};
