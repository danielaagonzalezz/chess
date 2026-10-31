"""
Paso 2 del aprendizaje: entrenar la evaluacion con las posiciones.

Lee el .npz de preparar_datos.py y ajusta una REGRESION LOGISTICA:

    P(ganan blancas) = sigmoide( evaluacion(posicion) / ESCALA )

donde la evaluacion es una suma de pesos, uno por cada (fase, tipo de
pieza, casilla): 2 x 6 x 64 = 768 numeros. Los pesos se ajustan para
minimizar el error de la prediccion frente al resultado real de la
partida (entropia cruzada) con una pequena penalizacion L2 que evita
que se disparen. La optimizacion la hace L-BFGS de scipy.

Despues compara, en posiciones que NO se usaron para entrenar, la
prediccion del modelo con la de la evaluacion hecha a mano
(evaluacion.py), y guarda los pesos en src/chess/bots/pesos_eval.json.

Uso:
    python training/entrenar.py data/posiciones.npz
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.optimize import minimize

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from chess.bots.evaluacion import (  # noqa: E402
    TABLA_REY_FINAL, TABLA_REY_PARTIDA, TABLAS, VALOR_PIEZA,
    evaluar as evaluar_a_mano,
)
from chess.bots.caracteristicas import N_EXTRAS, NOMBRES as NOMBRES_EXTRAS, extras  # noqa: E402
from chess.bots.evaluacion_ml import (  # noqa: E402
    FASE_TOTAL, LETRAS, RUTA_PESOS, TIPOS,
)
from chess.board import Board  # noqa: E402
from chess.pieces import BLACK, WHITE, Piece  # noqa: E402

# Una evaluacion de +400 centipeones <-> 10 veces mas probable ganar que perder.
# (La misma escala que se usa en ajedrez para pasar de puntos a probabilidad.)
CP_POR_LOGIT = 400 / math.log(10)

# Fase de cada codigo de pieza (1..6 blancas, 7..12 negras; peon y rey no cuentan).
FASE_POR_CODIGO = np.zeros(13, dtype=np.int8)
for _i, _p in enumerate([0, 1, 1, 2, 4, 0]):
    FASE_POR_CODIGO[_i + 1] = _p
    FASE_POR_CODIGO[_i + 7] = _p


def construir_caracteristicas(tableros, turnos=None):
    """
    Matriz dispersa X (N x (768 + 2 * N_EXTRAS)): cada fila es una posicion.
    Las columnas 0..767 son las tablas por casilla y las demas, las
    caracteristicas contadas (caracteristicas.py) en medio juego y final.
    Si 'turnos' es None, la ultima caracteristica (tener el turno) vale 0.

    Para cada pieza blanca de tipo t en la casilla s se suma +f a la columna
    (fase, t, s); para cada pieza negra, -f a la columna de la casilla
    simetrica. f = fase/24 para 'mg' y 1 - fase/24 para 'eg'. Asi
    X @ pesos es exactamente lo que calcula EvaluadorAprendido.
    """
    n = len(tableros)
    fase = np.minimum(FASE_POR_CODIGO[tableros].sum(axis=1), FASE_TOTAL).astype(np.float64)
    f_mg = fase / FASE_TOTAL
    f_eg = 1.0 - f_mg

    filas, columnas, valores = [], [], []
    fila_idx, casilla_idx = np.nonzero(tableros)
    codigos = tableros[fila_idx, casilla_idx].astype(np.int64)
    es_blanca = codigos <= 6
    tipo = np.where(es_blanca, codigos - 1, codigos - 7)
    casilla = np.where(es_blanca, casilla_idx, casilla_idx ^ 56)
    signo = np.where(es_blanca, 1.0, -1.0)
    for desplazamiento, f in ((0, f_mg), (384, f_eg)):
        filas.append(fila_idx)
        columnas.append(desplazamiento + tipo * 64 + casilla)
        valores.append(signo * f[fila_idx])
    # Caracteristicas contadas: se calculan con la MISMA funcion que usa el bot.
    ex = np.zeros((n, N_EXTRAS))
    for i in range(n):
        ex[i] = extras(tableros[i].tolist(), True if turnos is None else bool(turnos[i]))
        if turnos is None:
            ex[i, -1] = 0
    ex_mg = sparse.csr_matrix(ex * f_mg[:, None])
    ex_eg = sparse.csr_matrix(ex * f_eg[:, None])
    pst = sparse.csr_matrix(
        (np.concatenate(valores), (np.concatenate(filas), np.concatenate(columnas))),
        shape=(n, 768),
    )
    return sparse.hstack([pst, ex_mg, ex_eg], format="csr")


def sin_media(v):
    """
    Quita a cada tabla de 64 casillas su media (deja solo lo "posicional").
    Solo afecta a las 768 primeras columnas; las caracteristicas contadas
    se dejan como estan.
    """
    salida = v.copy()
    t = v[:768].reshape(12, 64)
    salida[:768] = (t - t.mean(axis=1, keepdims=True)).reshape(-1)
    return salida


def entrenar(X, y, l2, prior, material_fijo=True):
    """
    Regresion logistica con L2, resuelta con L-BFGS. Devuelve los pesos (en logits).

    'prior' son los pesos de partida (la evaluacion a mano): el modelo
    aprende solo una CORRECCION 'delta' y la penalizacion L2 se aplica a
    la correccion, no a los pesos. Con l2 enorme se queda en la evaluacion
    a mano; con l2 pequeno, se separa de ella todo lo que digan los datos.

    Con 'material_fijo' la correccion no puede cambiar el valor MEDIO de
    cada pieza en cada fase (el material: 1, 3, 3, 5, 9), solo como varia
    segun la casilla. Los datos no determinan bien el material en la
    apertura (casi siempre esta igualado) y la busqueda lo necesita para
    no regalar piezas; lo posicional si lo aprende de las partidas.
    """
    n = X.shape[0]
    XT = X.T.tocsr()
    z0 = X @ prior

    def funcion(u):
        delta = sin_media(u) if material_fijo else u
        z = z0 + X @ delta
        # log(1 + e^z) calculado sin desbordar.
        log1pexp = np.logaddexp(0.0, z)
        perdida = (log1pexp - y * z).sum() / n + (l2 * delta * delta).sum()
        p = 1.0 / (1.0 + np.exp(-z))
        grad = XT @ (p - y) / n + 2 * l2 * delta
        if material_fijo:
            grad = sin_media(grad)
        return perdida, grad

    res = minimize(funcion, np.zeros(X.shape[1]), jac=True, method="L-BFGS-B",
                   options={"maxiter": 500})
    delta = sin_media(res.x) if material_fijo else res.x
    return prior + delta, res


def pesos_a_mano():
    """
    La evaluacion a mano (material + tablas por casilla) escrita en el
    mismo formato de 768 pesos, en centipeones del archivo a mano.
    Orden: [fase (mg, eg)][pieza P N B R Q K][casilla]. Las caracteristicas
    contadas parten de 0.
    """
    w = np.zeros((2, 6, 64))
    for i, tipo in enumerate(TIPOS):
        for casilla in range(64):
            if tipo in TABLAS:
                valor = VALOR_PIEZA[tipo] + TABLAS[tipo][casilla]
                w[0, i, casilla] = w[1, i, casilla] = valor
            else:  # el rey: tabla de partida y tabla de final
                w[0, i, casilla] = TABLA_REY_PARTIDA[casilla]
                w[1, i, casilla] = TABLA_REY_FINAL[casilla]
    return np.concatenate([w.reshape(768), np.zeros(2 * N_EXTRAS)])


def metricas(z, y):
    """Entropia cruzada y acierto prediciendo quien gana (ignorando tablas)."""
    perdida = (np.logaddexp(0.0, z) - y * z).mean()
    decisivas = y != 0.5
    acierto = ((z[decisivas] > 0) == (y[decisivas] > 0.5)).mean()
    return perdida, acierto


def a_tablero(fila):
    """Pasa una fila de codigos (64) a un Board del proyecto."""
    tablero = Board()
    for i, codigo in enumerate(fila):
        if codigo:
            blanca = codigo <= 6
            tablero.squares[i] = Piece(TIPOS[(codigo - 1) % 6], WHITE if blanca else BLACK)
    return tablero


def ajustar_escala_a_mano(z_mano, y):
    """
    La evaluacion a mano esta en otra escala; para compararla de forma justa
    se le busca la escala (un solo numero) que mejor predice los resultados.
    """
    mejor = None
    for escala in np.geomspace(1e-4, 1e-1, 40):
        perdida, _ = metricas(z_mano * escala, y)
        if mejor is None or perdida < mejor[0]:
            mejor = (perdida, escala)
    return mejor[1]


def guardar(pesos_cp, ruta):
    cp = np.rint(pesos_cp[:768]).astype(int).reshape(2, 6, 64)
    extra = np.rint(pesos_cp[768:]).astype(int)
    datos = {
        "descripcion": "Pesos en centipeones por (fase, pieza, casilla) y por caracteristica contada. "
                       "Generado por training/entrenar.py.",
        "mg": {LETRAS[t]: cp[0][i].tolist() for i, t in enumerate(TIPOS)},
        "eg": {LETRAS[t]: cp[1][i].tolist() for i, t in enumerate(TIPOS)},
        "extras": NOMBRES_EXTRAS,
        "extras_mg": extra[:N_EXTRAS].tolist(),
        "extras_eg": extra[N_EXTRAS:].tolist(),
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    return cp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("datos", help=".npz generado por preparar_datos.py")
    ap.add_argument("--l2", type=float, nargs="+", default=[1e-6, 1e-5],
                    help="regularizacion de las tablas por casilla (se elige en validacion)")
    ap.add_argument("--l2-extras", type=float, nargs="+", default=[1e-5, 1e-4, 1e-3, 1e-2],
                    help="regularizacion de las caracteristicas contadas (se elige en validacion)")
    ap.add_argument("--validacion", type=float, default=0.1, help="fraccion para elegir l2")
    ap.add_argument("--prueba", type=float, default=0.1, help="fraccion final reservada para comprobar")
    ap.add_argument("--salida", default=str(RUTA_PESOS))
    ap.add_argument("--sin-extras", action="store_true",
                    help="entrenar solo las tablas por casilla (para medir cuanto aportan las caracteristicas)")
    args = ap.parse_args()

    datos = np.load(args.datos)
    tableros, y = datos["tableros"], datos["resultado"].astype(np.float64)
    n = len(y)
    # Las posiciones de una misma partida estan seguidas: separar por bloques
    # (sin mezclar antes) evita que el modelo vea en el entrenamiento
    # posiciones de las partidas con las que luego se comprueba.
    fin_tr = int(n * (1 - args.validacion - args.prueba))
    fin_va = int(n * (1 - args.prueba))
    tr, va, te = slice(0, fin_tr), slice(fin_tr, fin_va), slice(fin_va, n)
    print(f"{n} posiciones: {fin_tr} entrenar, {fin_va - fin_tr} validar, {n - fin_va} comprobar")

    X = construir_caracteristicas(tableros, datos["turno"])
    if args.sin_extras:
        X = X[:, :768].tocsr()

    # Punto de partida: la evaluacion a mano, con la escala (centipeones ->
    # logit) que mejor predice los resultados de entrenamiento.
    a_mano = pesos_a_mano()
    if args.sin_extras:
        a_mano = a_mano[:768]
    z_mano = X[tr] @ a_mano
    escala = ajustar_escala_a_mano(z_mano, y[tr])
    prior = a_mano * escala
    print(f"escala de la evaluacion a mano: {escala:.5f} logit/cp")

    # Elegir la regularizacion con el bloque de validacion. Las
    # caracteristicas contadas raras (una torre en septima en medio juego
    # casi nunca pasa) se desbocan si no se frenan, asi que tienen su propia
    # penalizacion. Entre las que quedan a menos de 0.001 del mejor error de
    # validacion, se prefiere la mas fuerte (el modelo mas sencillo).
    n_col = X.shape[1]
    candidatos = []
    combinaciones = [(a, b) for a in args.l2 for b in (args.l2_extras if n_col > 768 else [args.l2[0]])]
    for l2_pst, l2_ex in combinaciones:
        l2 = np.full(n_col, l2_pst)
        l2[768:] = l2_ex
        w, res = entrenar(X[tr], y[tr], l2, prior)
        perdida_va, _ = metricas(X[va] @ w, y[va])
        print(f"  l2 tablas={l2_pst:g} l2 caracteristicas={l2_ex:g}: error en validacion {perdida_va:.4f}")
        candidatos.append((perdida_va, l2_pst, l2_ex, w))
    mejor_perdida = min(c[0] for c in candidatos)
    elegibles = [c for c in candidatos if c[0] <= mejor_perdida + 0.001]
    _, l2_pst, l2_ex, w = max(elegibles, key=lambda c: (c[2], c[1]))
    print(f"elegido: l2 tablas={l2_pst:g}, l2 caracteristicas={l2_ex:g}")

    # Comprobacion final en posiciones que no se han usado para nada.
    z_te = X[te] @ w
    p_te = metricas(z_te, y[te])
    p_tr = metricas(X[tr] @ w, y[tr])
    z_mano_te = np.array([evaluar_a_mano(a_tablero(f)) for f in tableros[te]], dtype=np.float64)
    p_mano_completa = metricas(z_mano_te * ajustar_escala_a_mano(z_mano_te, y[te]), y[te])
    p_mano_tablas = metricas((X[te] @ prior), y[te])
    p_nada = metricas(np.zeros(n - fin_va), y[te])

    print("\n                                 error (menor=mejor)   acierto quien gana")
    print(f"  sin informacion                {p_nada[0]:.4f}                {p_nada[1]:.1%}")
    print(f"  evaluacion a mano (completa)   {p_mano_completa[0]:.4f}                {p_mano_completa[1]:.1%}")
    print(f"  a mano (solo tablas, mismo formato) {p_mano_tablas[0]:.4f}           {p_mano_tablas[1]:.1%}")
    print(f"  evaluacion aprendida           {p_te[0]:.4f}                {p_te[1]:.1%}   (entrenamiento: {p_tr[0]:.4f} / {p_tr[1]:.1%})")

    if args.sin_extras:
        w = np.concatenate([w, np.zeros(2 * N_EXTRAS)])
    cp = guardar(w / escala, args.salida)
    print("\nvalor medio por pieza en medio juego (cp):",
          {LETRAS[t]: int(cp[0][i].mean()) for i, t in enumerate(TIPOS)})
    if not args.sin_extras:
        print("\ncaracteristicas aprendidas (cp, medio juego / final):")
        for i, nombre in enumerate(NOMBRES_EXTRAS):
            print(f"  {nombre:32s} {int(w[768 + i] / escala):5d} / {int(w[768 + N_EXTRAS + i] / escala):5d}")
    print("pesos guardados en", args.salida)


if __name__ == "__main__":
    main()
