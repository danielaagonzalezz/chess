"""
Caracteristicas de una posicion, mas alla de "que pieza hay en que casilla".

Una evaluacion que solo suma un valor por pieza y casilla no sabe que un
peon aislado es debil, que un peon pasado es fuerte o que una torre vale
mas en una columna abierta. Estas caracteristicas se lo cuentan. NO llevan
numeros a mano: cada una es solo un CONTADOR, y cuanto vale lo aprende el
modelo de las partidas (training/entrenar.py), igual que los valores por
casilla.

Cada caracteristica se calcula como "las de las blancas MENOS las de las
negras", asi que es positiva si favorece a las blancas.

Esta es la UNICA definicion: la usan el entrenamiento y el bot, por eso no
pueden desajustarse. Trabaja sobre la lista de 64 numeros del motor rapido
(0 = vacia, 1..6 = P N B R Q K blancas, 7..12 = negras; a1=0 ... h8=63).
"""

NOMBRES = [
    "pareja de alfiles",            # 0
    "peones doblados",              # 1
    "peones aislados",              # 2
    "peon pasado en 2a fila",       # 3
    "peon pasado en 3a fila",       # 4
    "peon pasado en 4a fila",       # 5
    "peon pasado en 5a fila",       # 6
    "peon pasado en 6a fila",       # 7
    "peon pasado en 7a fila",       # 8
    "torre en columna abierta",     # 9
    "torre en columna semiabierta",  # 10
    "escudo de peones del rey",     # 11
    "peones conectados",            # 12
    "torre en septima",             # 13
    "tener el turno",               # 14
]
N_EXTRAS = len(NOMBRES)
TEMPO = 14


def extras(b, turno_blancas=True):
    """
    Lista con N_EXTRAS contadores (blancas - negras) de la posicion 'b'.

    'turno_blancas' solo afecta a la ultima ("tener el turno": +1 si
    mueven las blancas, -1 si mueven las negras).
    """
    v = [0] * N_EXTRAS
    peones_b = [0] * 8       # peones blancos en cada columna
    peones_n = [0] * 8
    max_n = [-1] * 8         # fila mas alta de un peon negro en la columna
    min_b = [8] * 8          # fila mas baja de un peon blanco en la columna
    lista_pb = []
    lista_pn = []
    alfiles_b = alfiles_n = 0
    torres_b = []
    torres_n = []
    rey_b = rey_n = -1

    for sq in range(64):
        p = b[sq]
        if not p:
            continue
        if p == 1:
            f = sq & 7
            peones_b[f] += 1
            r = sq >> 3
            if r < min_b[f]:
                min_b[f] = r
            lista_pb.append(sq)
        elif p == 7:
            f = sq & 7
            peones_n[f] += 1
            r = sq >> 3
            if r > max_n[f]:
                max_n[f] = r
            lista_pn.append(sq)
        elif p == 3:
            alfiles_b += 1
        elif p == 9:
            alfiles_n += 1
        elif p == 4:
            torres_b.append(sq)
        elif p == 10:
            torres_n.append(sq)
        elif p == 6:
            rey_b = sq
        elif p == 12:
            rey_n = sq

    # ---- pareja de alfiles ----
    v[0] = (alfiles_b >= 2) - (alfiles_n >= 2)

    # ---- peones doblados ----
    doblados = 0
    for f in range(8):
        if peones_b[f] > 1:
            doblados += peones_b[f] - 1
        if peones_n[f] > 1:
            doblados -= peones_n[f] - 1
    v[1] = doblados

    # ---- peones blancos: aislados, pasados, conectados ----
    for sq in lista_pb:
        f = sq & 7
        r = sq >> 3
        if (f == 0 or not peones_b[f - 1]) and (f == 7 or not peones_b[f + 1]):
            v[2] += 1
        pasado = max_n[f] <= r
        if pasado and f > 0 and max_n[f - 1] > r:
            pasado = False
        if pasado and f < 7 and max_n[f + 1] > r:
            pasado = False
        if pasado and 1 <= r <= 6:
            v[2 + r] += 1               # r=1 -> 3 ... r=6 -> 8
        if (f > 0 and b[sq - 9] == 1) or (f < 7 and b[sq - 7] == 1):
            v[12] += 1

    # ---- peones negros (los mismos contadores, restando) ----
    for sq in lista_pn:
        f = sq & 7
        r = sq >> 3
        if (f == 0 or not peones_n[f - 1]) and (f == 7 or not peones_n[f + 1]):
            v[2] -= 1
        pasado = min_b[f] >= r
        if pasado and f > 0 and min_b[f - 1] < r:
            pasado = False
        if pasado and f < 7 and min_b[f + 1] < r:
            pasado = False
        if pasado and 1 <= r <= 6:
            v[2 + 7 - r] -= 1           # fila relativa 7-r: r=6 -> 3 ... r=1 -> 8
        if (f > 0 and b[sq + 7] == 7) or (f < 7 and b[sq + 9] == 7):
            v[12] -= 1

    # ---- torres ----
    for sq in torres_b:
        f = sq & 7
        if not peones_b[f]:
            if not peones_n[f]:
                v[9] += 1
            else:
                v[10] += 1
        if sq >> 3 == 6:
            v[13] += 1
    for sq in torres_n:
        f = sq & 7
        if not peones_n[f]:
            if not peones_b[f]:
                v[9] -= 1
            else:
                v[10] -= 1
        if sq >> 3 == 1:
            v[13] -= 1

    # ---- escudo de peones delante del rey ----
    if rey_b >= 0:
        f = rey_b & 7
        r = rey_b >> 3
        cuenta = 0
        for g in range(max(0, f - 1), min(7, f + 1) + 1):
            for rr in (r + 1, r + 2):
                if rr < 8 and b[rr * 8 + g] == 1:
                    cuenta += 1
        v[11] += cuenta
    if rey_n >= 0:
        f = rey_n & 7
        r = rey_n >> 3
        cuenta = 0
        for g in range(max(0, f - 1), min(7, f + 1) + 1):
            for rr in (r - 1, r - 2):
                if rr >= 0 and b[rr * 8 + g] == 7:
                    cuenta += 1
        v[11] -= cuenta

    v[TEMPO] = 1 if turno_blancas else -1
    return v
