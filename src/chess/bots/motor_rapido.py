"""
Motor de busqueda rapido para el bot aprendido.

POR QUE EXISTE
--------------
Las jugadas legales de game.py se calculan aplicando cada jugada al tablero
y mirando si el rey queda en jaque: es claro y correcto, pero cada posicion
cuesta ~1 ms y el bot solo llega a mirar 3-4 jugadas por delante. Aqui hay
un segundo motor, pensado SOLO para buscar rapido:

  - El tablero es una lista de 64 numeros (no objetos Piece).
  - Las jugadas se HACEN y se DESHACEN sobre el mismo tablero (no se copia).
  - Las jugadas son numeros enteros y se generan con tablas precalculadas.
  - Una jugada pseudolegal solo se comprueba (si deja al rey en jaque) cuando
    de verdad se va a probar: si hay poda, las demas ni se comprueban.
  - Hash de Zobrist incremental para la tabla de transposicion y las
    repeticiones.

Las REGLAS siguen siendo las de game.py: el bot convierte la partida a este
motor (con el FEN), busca, y devuelve una Move que se comprueba contra
game.jugadas_legales(). Los tests comparan este motor con game.py.

CODIGOS DE PIEZA
----------------
0 = vacia; 1..6 = peon, caballo, alfil, torre, dama, rey BLANCOS;
7..12 = lo mismo NEGRAS. Casillas: a1=0, b1=1 ... h8=63 (como Square.to_index).

JUGADAS (enteros)
-----------------
origen | destino << 6 | promocion << 12 | marca << 15
  promocion: 0 o el tipo de pieza (2 caballo, 3 alfil, 4 torre, 5 dama)
  marca: 1 captura al paso, 2 enroque, 3 avance doble de peon

BUSQUEDA
--------
Negamax con poda alfa-beta y profundizacion iterativa, mas las mejoras
habituales: tabla de transposicion, busqueda de capturas (quiescencia),
extension por jaque, poda por jugada nula, reducciones de jugadas tardias
(LMR), busqueda de variante principal (PVS), poda "reverse futility",
y orden de jugadas por MVV-LVA, killers e historial.
"""

import random
import time

from chess.bots.caracteristicas import N_EXTRAS, extras
from chess.bots.evaluacion_ml import LETRAS, TIPOS, cargar_pesos

PEON, CABALLO, ALFIL, TORRE, DAMA, REY = 1, 2, 3, 4, 5, 6

MATE = 100000
UMBRAL_MATE = MATE - 1000
INFINITO = MATE * 10

# Fase de la partida que aporta cada pieza (indexado por codigo 0..12).
FASE = [0, 0, 1, 1, 2, 4, 0, 0, 1, 1, 2, 4, 0]
FASE_TOTAL = 24

# Valores para ordenar capturas (MVV-LVA), indexados por TIPO de pieza.
VALOR_ORDEN = [0, 100, 320, 330, 500, 900, 20000]

TEMPO = 10  # pequena ventaja por tener el turno (centipeones)


# =========================================================
# Tablas precalculadas
# =========================================================

def _construir_tablas():
    caballo, rey = [], []
    rayos_alfil, rayos_torre = [], []
    ataca_peon = ([], [])
    for sq in range(64):
        f, r = sq % 8, sq // 8
        caballo.append(tuple(
            (r + dr) * 8 + f + df
            for dr, df in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
            if 0 <= r + dr < 8 and 0 <= f + df < 8
        ))
        rey.append(tuple(
            (r + dr) * 8 + f + df
            for dr in (-1, 0, 1) for df in (-1, 0, 1)
            if (dr or df) and 0 <= r + dr < 8 and 0 <= f + df < 8
        ))

        def rayos(direcciones):
            salida = []
            for dr, df in direcciones:
                rayo = []
                rr, ff = r + dr, f + df
                while 0 <= rr < 8 and 0 <= ff < 8:
                    rayo.append(rr * 8 + ff)
                    rr += dr
                    ff += df
                if rayo:
                    salida.append(tuple(rayo))
            return tuple(salida)

        rayos_alfil.append(rayos(((1, 1), (1, -1), (-1, 1), (-1, -1))))
        rayos_torre.append(rayos(((1, 0), (-1, 0), (0, 1), (0, -1))))
        # Casillas que ataca un peon (blanco: hacia arriba; negro: hacia abajo).
        ataca_peon[0].append(tuple(
            (r + 1) * 8 + f + df for df in (-1, 1) if r < 7 and 0 <= f + df < 8))
        ataca_peon[1].append(tuple(
            (r - 1) * 8 + f + df for df in (-1, 1) if r > 0 and 0 <= f + df < 8))
    return caballo, rey, rayos_alfil, rayos_torre, ataca_peon


T_CABALLO, T_REY, RAYOS_ALFIL, RAYOS_TORRE, ATAQUE_PEON = _construir_tablas()

# Que derechos de enroque se pierden al mover desde / a cada casilla.
# Bits: 1 = blanco corto, 2 = blanco largo, 4 = negro corto, 8 = negro largo.
MASCARA_ENROQUE = [15] * 64
MASCARA_ENROQUE[4] = 12
MASCARA_ENROQUE[0] = 13
MASCARA_ENROQUE[7] = 14
MASCARA_ENROQUE[60] = 3
MASCARA_ENROQUE[56] = 7
MASCARA_ENROQUE[63] = 11

# Zobrist
_azar = random.Random(20261029)
Z_PIEZA = [[_azar.getrandbits(64) for _ in range(64)] for _ in range(13)]
Z_TURNO = _azar.getrandbits(64)
Z_ENROQUE = [_azar.getrandbits(64) for _ in range(16)]
Z_AL_PASO = [_azar.getrandbits(64) for _ in range(8)]

NOMBRES = ["%s%d" % ("abcdefgh"[s % 8], s // 8 + 1) for s in range(64)]
INDICE_DE_NOMBRE = {n: i for i, n in enumerate(NOMBRES)}
LETRA_PROMOCION = {2: "n", 3: "b", 4: "r", 5: "q"}
TIPO_DE_LETRA = {"p": 1, "n": 2, "b": 3, "r": 4, "q": 5, "k": 6}


def tablas_de_pesos(mg, eg):
    """
    Pasa los pesos del fichero (por pieza, vistos desde las blancas) a
    tablas indexadas por codigo de pieza y casilla, ya con el signo
    (las negras restan y leen la casilla simetrica).
    """
    tmg = [[0] * 64 for _ in range(13)]
    teg = [[0] * 64 for _ in range(13)]
    for i, tipo in enumerate(TIPOS):
        letra = LETRAS[tipo]
        for sq in range(64):
            tmg[i + 1][sq] = mg[letra][sq]
            teg[i + 1][sq] = eg[letra][sq]
            tmg[i + 7][sq] = -mg[letra][sq ^ 56]
            teg[i + 7][sq] = -eg[letra][sq ^ 56]
    return tmg, teg


class SinTiempo(Exception):
    """Se lanza dentro de la busqueda cuando se acaba el tiempo."""


# =========================================================
# La posicion
# =========================================================

class Posicion:
    """Tablero + turno + enroques + al paso, con hacer/deshacer jugadas."""

    def __init__(self, casillas, turno, derechos, al_paso, medios, tablas):
        self.b = list(casillas)
        self.side = turno                  # 0 = blancas, 1 = negras
        self.rights = derechos             # mascara de bits
        self.ep = al_paso                  # casilla de captura al paso o -1
        self.half = medios
        self.tmg, self.teg = tablas
        self.ksq = [-1, -1]
        self.mg = 0
        self.eg = 0
        self.phase = 0
        self.np = [0, 0]                   # piezas que no son peon ni rey, por color
        self.npawns = 0
        for sq, p in enumerate(self.b):
            if p:
                self.mg += self.tmg[p][sq]
                self.eg += self.teg[p][sq]
                self.phase += FASE[p]
                t = p if p < 7 else p - 6
                if t == REY:
                    self.ksq[0 if p < 7 else 1] = sq
                elif t == PEON:
                    self.npawns += 1
                else:
                    self.np[0 if p < 7 else 1] += 1
        # La casilla al paso solo cuenta para el hash si un peon puede capturar.
        self.eph = self.ep >= 0 and self._peon_puede_al_paso()
        self.h = self.calcular_hash()
        self.pila = []
        self.hist = [self.h]

    # ---------- crear desde FEN ----------

    @classmethod
    def desde_fen(cls, fen, tablas):
        partes = fen.split()
        casillas = [0] * 64
        for i, fila in enumerate(partes[0].split("/")):
            rank = 7 - i
            file = 0
            for c in fila:
                if c.isdigit():
                    file += int(c)
                else:
                    casillas[rank * 8 + file] = TIPO_DE_LETRA[c.lower()] + (0 if c.isupper() else 6)
                    file += 1
        turno = 0 if partes[1] == "w" else 1
        derechos = 0
        for letra, bit in (("K", 1), ("Q", 2), ("k", 4), ("q", 8)):
            if letra in partes[2]:
                derechos |= bit
        al_paso = -1 if partes[3] == "-" else INDICE_DE_NOMBRE[partes[3]]
        medios = int(partes[4]) if len(partes) > 4 else 0
        return cls(casillas, turno, derechos, al_paso, medios, tablas)

    def _peon_puede_al_paso(self):
        # Un peon del bando que tiene el turno que ataque la casilla al paso.
        propio = PEON if self.side == 0 else PEON + 6
        for t in ATAQUE_PEON[1 - self.side][self.ep]:
            if self.b[t] == propio:
                return True
        return False

    def calcular_hash(self):
        h = 0
        for sq, p in enumerate(self.b):
            if p:
                h ^= Z_PIEZA[p][sq]
        if self.side:
            h ^= Z_TURNO
        h ^= Z_ENROQUE[self.rights]
        if self.eph:
            h ^= Z_AL_PASO[self.ep & 7]
        return h

    # ---------- ataques ----------

    def atacado(self, sq, por):
        """True si la casilla 'sq' esta atacada por alguna pieza del color 'por'."""
        b = self.b
        o = 6 * por
        for t in T_CABALLO[sq]:
            if b[t] == 2 + o:
                return True
        for t in T_REY[sq]:
            if b[t] == 6 + o:
                return True
        peon = 1 + o
        for t in ATAQUE_PEON[1 - por][sq]:
            if b[t] == peon:
                return True
        a, d = 3 + o, 5 + o
        for rayo in RAYOS_ALFIL[sq]:
            for t in rayo:
                p = b[t]
                if p:
                    if p == a or p == d:
                        return True
                    break
        a = 4 + o
        for rayo in RAYOS_TORRE[sq]:
            for t in rayo:
                p = b[t]
                if p:
                    if p == a or p == d:
                        return True
                    break
        return False

    def en_jaque(self):
        s = self.side
        return self.atacado(self.ksq[s], 1 - s)

    # ---------- generar jugadas pseudolegales ----------

    def generar(self, capturas=False):
        """
        Jugadas pseudolegales (pueden dejar al propio rey en jaque).
        Con capturas=True solo capturas y promociones a dama (para la
        busqueda de capturas).
        """
        b = self.b
        side = self.side
        mov = []
        add = mov.append
        lo = 1 + 6 * side
        hi = lo + 5
        elo = 7 if side == 0 else 1
        ehi = elo + 5
        ep = self.ep
        for sq in range(64):
            p = b[sq]
            if p < lo or p > hi:
                continue
            t = p - 6 * side
            if t == PEON:
                if side == 0:
                    d, inicio, ultima = 8, 1, 6
                else:
                    d, inicio, ultima = -8, 6, 1
                r = sq >> 3
                adelante = sq + d
                if r == ultima:
                    if b[adelante] == 0:
                        if capturas:
                            add(sq | adelante << 6 | 5 << 12)
                        else:
                            for pr in (5, 4, 3, 2):
                                add(sq | adelante << 6 | pr << 12)
                    for to in ATAQUE_PEON[side][sq]:
                        q = b[to]
                        if elo <= q <= ehi:
                            if capturas:
                                add(sq | to << 6 | 5 << 12)
                            else:
                                for pr in (5, 4, 3, 2):
                                    add(sq | to << 6 | pr << 12)
                else:
                    if not capturas and b[adelante] == 0:
                        add(sq | adelante << 6)
                        if r == inicio and b[adelante + d] == 0:
                            add(sq | (adelante + d) << 6 | 3 << 15)
                    for to in ATAQUE_PEON[side][sq]:
                        q = b[to]
                        if q:
                            if elo <= q <= ehi:
                                add(sq | to << 6)
                        elif to == ep:
                            add(sq | to << 6 | 1 << 15)
            elif t == CABALLO or t == REY:
                for to in (T_CABALLO[sq] if t == CABALLO else T_REY[sq]):
                    q = b[to]
                    if q == 0:
                        if not capturas:
                            add(sq | to << 6)
                    elif elo <= q <= ehi:
                        add(sq | to << 6)
            else:
                if t != TORRE:   # alfil o dama: diagonales
                    for rayo in RAYOS_ALFIL[sq]:
                        for to in rayo:
                            q = b[to]
                            if q == 0:
                                if not capturas:
                                    add(sq | to << 6)
                            else:
                                if elo <= q <= ehi:
                                    add(sq | to << 6)
                                break
                if t != ALFIL:   # torre o dama: filas y columnas
                    for rayo in RAYOS_TORRE[sq]:
                        for to in rayo:
                            q = b[to]
                            if q == 0:
                                if not capturas:
                                    add(sq | to << 6)
                            else:
                                if elo <= q <= ehi:
                                    add(sq | to << 6)
                                break

        if not capturas and self.rights:
            self._enroques(mov)
        return mov

    def _enroques(self, mov):
        b = self.b
        if self.side == 0:
            if b[4] != REY:
                return
            r = self.rights
            if r & 1 and b[7] == TORRE and b[5] == 0 and b[6] == 0:
                if not self.atacado(4, 1) and not self.atacado(5, 1) and not self.atacado(6, 1):
                    mov.append(4 | 6 << 6 | 2 << 15)
            if r & 2 and b[0] == TORRE and b[1] == 0 and b[2] == 0 and b[3] == 0:
                if not self.atacado(4, 1) and not self.atacado(3, 1) and not self.atacado(2, 1):
                    mov.append(4 | 2 << 6 | 2 << 15)
        else:
            if b[60] != REY + 6:
                return
            r = self.rights
            if r & 4 and b[63] == TORRE + 6 and b[61] == 0 and b[62] == 0:
                if not self.atacado(60, 0) and not self.atacado(61, 0) and not self.atacado(62, 0):
                    mov.append(60 | 62 << 6 | 2 << 15)
            if r & 8 and b[56] == TORRE + 6 and b[57] == 0 and b[58] == 0 and b[59] == 0:
                if not self.atacado(60, 0) and not self.atacado(59, 0) and not self.atacado(58, 0):
                    mov.append(60 | 58 << 6 | 2 << 15)

    # ---------- hacer / deshacer ----------

    def hacer(self, m):
        """Hace la jugada. NO comprueba si deja al rey en jaque (ver 'legal_tras_hacer')."""
        b = self.b
        side = self.side
        frm = m & 63
        to = (m >> 6) & 63
        promo = (m >> 12) & 7
        flag = m >> 15
        p = b[frm]
        cap = b[to]
        self.pila.append((m, p, cap, self.rights, self.ep, self.eph, self.half, self.h,
                          self.mg, self.eg, self.phase, self.np[0], self.np[1], self.npawns))
        tmg, teg = self.tmg, self.teg
        h = self.h
        mg = self.mg - tmg[p][frm]
        eg = self.eg - teg[p][frm]
        h ^= Z_PIEZA[p][frm]
        b[frm] = 0
        if cap:
            h ^= Z_PIEZA[cap][to]
            mg -= tmg[cap][to]
            eg -= teg[cap][to]
            self.phase -= FASE[cap]
            ct = cap if cap < 7 else cap - 6
            if ct == PEON:
                self.npawns -= 1
            else:
                self.np[1 - side] -= 1
        elif flag == 1:
            cs = to - 8 if side == 0 else to + 8
            cp = b[cs]
            b[cs] = 0
            h ^= Z_PIEZA[cp][cs]
            mg -= tmg[cp][cs]
            eg -= teg[cp][cs]
            self.npawns -= 1
        nuevo = p
        if promo:
            nuevo = promo + 6 * side
            self.phase += FASE[nuevo]
            self.npawns -= 1
            self.np[side] += 1
        b[to] = nuevo
        h ^= Z_PIEZA[nuevo][to]
        mg += tmg[nuevo][to]
        eg += teg[nuevo][to]
        if flag == 2:
            if to == 6:
                rf, rt = 7, 5
            elif to == 2:
                rf, rt = 0, 3
            elif to == 62:
                rf, rt = 63, 61
            else:
                rf, rt = 56, 59
            torre = TORRE + 6 * side
            b[rf] = 0
            b[rt] = torre
            h ^= Z_PIEZA[torre][rf] ^ Z_PIEZA[torre][rt]
            mg += tmg[torre][rt] - tmg[torre][rf]
            eg += teg[torre][rt] - teg[torre][rf]
        if p == REY or p == REY + 6:
            self.ksq[side] = to

        antiguo = self.rights
        nuevo_der = antiguo & MASCARA_ENROQUE[frm] & MASCARA_ENROQUE[to]
        if nuevo_der != antiguo:
            h ^= Z_ENROQUE[antiguo] ^ Z_ENROQUE[nuevo_der]
            self.rights = nuevo_der

        if self.eph:
            h ^= Z_AL_PASO[self.ep & 7]
        if flag == 3:
            self.ep = (frm + to) >> 1
            peon_rival = PEON + 6 * (1 - side)
            f = to & 7
            self.eph = (f > 0 and b[to - 1] == peon_rival) or (f < 7 and b[to + 1] == peon_rival)
            if self.eph:
                h ^= Z_AL_PASO[f]
        else:
            self.ep = -1
            self.eph = False

        if p == PEON or p == PEON + 6 or cap or flag == 1:
            self.half = 0
        else:
            self.half += 1
        self.side = 1 - side
        h ^= Z_TURNO
        self.h = h
        self.mg = mg
        self.eg = eg
        self.hist.append(h)

    def deshacer(self):
        b = self.b
        (m, p, cap, self.rights, self.ep, self.eph, self.half, self.h,
         self.mg, self.eg, self.phase, self.np[0], self.np[1], self.npawns) = self.pila.pop()
        self.hist.pop()
        self.side ^= 1
        side = self.side
        frm = m & 63
        to = (m >> 6) & 63
        flag = m >> 15
        b[frm] = p
        b[to] = cap
        if flag == 1:
            b[to - 8 if side == 0 else to + 8] = PEON + 6 * (1 - side)
        elif flag == 2:
            if to == 6:
                rf, rt = 7, 5
            elif to == 2:
                rf, rt = 0, 3
            elif to == 62:
                rf, rt = 63, 61
            else:
                rf, rt = 56, 59
            b[rt] = 0
            b[rf] = TORRE + 6 * side
        if p == REY or p == REY + 6:
            self.ksq[side] = frm

    def hacer_nulo(self):
        self.pila.append((self.ep, self.eph, self.half, self.h))
        h = self.h
        if self.eph:
            h ^= Z_AL_PASO[self.ep & 7]
        self.ep = -1
        self.eph = False
        self.side ^= 1
        h ^= Z_TURNO
        self.half += 1
        self.h = h
        self.hist.append(h)

    def deshacer_nulo(self):
        self.ep, self.eph, self.half, self.h = self.pila.pop()
        self.hist.pop()
        self.side ^= 1

    def legal_tras_hacer(self):
        """Tras 'hacer', True si la jugada fue legal (el rey que movio no esta en jaque)."""
        s = self.side ^ 1           # el que acaba de mover
        return not self.atacado(self.ksq[s], 1 - s)

    # ---------- utilidades ----------

    def legales(self):
        """Lista de jugadas LEGALES (para tests y para el bot)."""
        resultado = []
        for m in self.generar():
            self.hacer(m)
            if self.legal_tras_hacer():
                resultado.append(m)
            self.deshacer()
        return resultado

    def perft(self, profundidad):
        """Cuenta las posiciones alcanzables en 'profundidad' jugadas (para comprobar el motor)."""
        if profundidad == 0:
            return 1
        total = 0
        for m in self.generar():
            self.hacer(m)
            if self.legal_tras_hacer():
                total += 1 if profundidad == 1 else self.perft(profundidad - 1)
            self.deshacer()
        return total

    def material_insuficiente(self):
        """Rey contra rey o rey y una pieza menor contra rey (sin peones)."""
        return self.npawns == 0 and self.phase <= 1


def jugada_a_texto(m):
    """Jugada entera -> texto como 'e2e4' o 'e7e8q'."""
    texto = NOMBRES[m & 63] + NOMBRES[(m >> 6) & 63]
    promo = (m >> 12) & 7
    if promo:
        texto += LETRA_PROMOCION[promo]
    return texto


# =========================================================
# La busqueda
# =========================================================

EXACTO, INFERIOR, SUPERIOR = 0, 1, 2
TAMANO_MAXIMO_TABLA = 600000


class Buscador:
    """
    Busca la mejor jugada de una Posicion.

    - 'tiempo': segundos maximos por jugada (la busqueda se para sola).
    - 'profundidad': profundidad maxima (por defecto, solo manda el tiempo).
    - 'pesos_extras': (mg, eg) con los pesos de las caracteristicas contadas
      (caracteristicas.py). None = solo las tablas por pieza y casilla.
    - 'evaluar': funcion opcional(posicion) -> centipeones para el bando
      que tiene el turno. Por defecto, la evaluacion aprendida.
    """

    def __init__(self, tiempo=2.0, profundidad=64, evaluar=None, pesos_extras=None):
        self.tiempo = tiempo
        self.profundidad_max = profundidad
        self.evaluar_externa = evaluar
        self.extras_mg, self.extras_eg = pesos_extras if pesos_extras is not None else (None, None)
        self.tabla = {}
        self.killers = [[0, 0] for _ in range(128)]
        self.historial = [[0] * 64 for _ in range(13)]
        self.nodos = 0
        self.profundidad_alcanzada = 0
        self.valor = 0
        self.limite = None
        self.previas = {}
        self.mejor_raiz = 0

    # ---------- evaluacion ----------

    def evaluar(self, pos):
        if self.evaluar_externa is not None:
            return self.evaluar_externa(pos)
        ph = pos.phase if pos.phase < FASE_TOTAL else FASE_TOTAL
        mg = pos.mg
        eg = pos.eg
        if self.extras_mg is None:
            v = (mg * ph + eg * (FASE_TOTAL - ph)) // FASE_TOTAL
            return (v if pos.side == 0 else -v) + TEMPO
        valores = extras(pos.b, pos.side == 0)
        wm = self.extras_mg
        we = self.extras_eg
        for i in range(N_EXTRAS):
            x = valores[i]
            if x:
                mg += wm[i] * x
                eg += we[i] * x
        v = (mg * ph + eg * (FASE_TOTAL - ph)) // FASE_TOTAL
        return v if pos.side == 0 else -v

    # ---------- punto de entrada ----------

    def buscar(self, pos, previas=None):
        """
        Devuelve la mejor jugada (entero) o 0 si no hay jugadas legales.
        'previas': {hash: veces} de posiciones ya ocurridas en la partida
        (para evitar repetir posiciones y buscar la repeticion si se va ganando).
        """
        self.previas = previas or {}
        self.nodos = 0
        self.profundidad_alcanzada = 0
        if len(self.tabla) > TAMANO_MAXIMO_TABLA:
            self.tabla.clear()
        self.historial = [[0] * 64 for _ in range(13)]
        for k in self.killers:
            k[0] = k[1] = 0
        inicio = time.perf_counter()
        self.limite = inicio + self.tiempo

        legales = pos.legales()
        if not legales:
            return 0
        mejor = legales[0]
        if len(legales) == 1:
            return mejor
        self.mejor_raiz = mejor

        try:
            for prof in range(1, self.profundidad_max + 1):
                valor = self._negamax(pos, prof, -INFINITO, INFINITO, 0, True)
                mejor = self.mejor_raiz
                self.valor = valor
                self.profundidad_alcanzada = prof
                if abs(valor) >= UMBRAL_MATE:
                    break
                # La siguiente vuelta cuesta varias veces mas: si ya se ha
                # gastado casi la mitad del tiempo, no merece la pena empezarla.
                if time.perf_counter() - inicio > self.tiempo * 0.45:
                    break
        except SinTiempo:
            pass
        return mejor

    # ---------- negamax ----------

    def _negamax(self, pos, prof, alfa, beta, ply, nulo_permitido):
        self.nodos += 1
        if not self.nodos & 2047 and time.perf_counter() > self.limite:
            raise SinTiempo()

        raiz = ply == 0
        h = pos.h
        if not raiz:
            if pos.half >= 100:
                return 0
            if pos.half >= 4:
                # Repeticion dentro de la busqueda (misma posicion ya vista).
                hist = pos.hist
                n = len(hist)
                limite = n - 1 - pos.half
                i = n - 3
                while i >= 0 and i >= limite:
                    if hist[i] == h:
                        return 0
                    i -= 2
            if h in self.previas:
                return 0
            if pos.npawns == 0 and pos.phase <= 1:
                return 0

        side = pos.side
        en_jaque = pos.atacado(pos.ksq[side], 1 - side)
        if en_jaque:
            prof += 1
        if prof <= 0:
            return self._quiescencia(pos, alfa, beta, ply, 0)

        alfa_original = alfa
        mov_tabla = 0
        entrada = self.tabla.get(h)
        if entrada is not None:
            prof_t, valor_t, tipo, mov_tabla = entrada
            if prof_t >= prof and not raiz:
                if valor_t >= UMBRAL_MATE:
                    valor_t -= ply
                elif valor_t <= -UMBRAL_MATE:
                    valor_t += ply
                if tipo == EXACTO:
                    return valor_t
                if tipo == INFERIOR:
                    if valor_t > alfa:
                        alfa = valor_t
                elif valor_t < beta:
                    beta = valor_t
                if alfa >= beta:
                    return valor_t

        estatica = 0
        if not en_jaque and not raiz:
            estatica = self.evaluar(pos)
            # "Reverse futility": si ya voy MUY por encima de beta, la poda es segura.
            if prof <= 3 and estatica - 110 * prof >= beta and abs(beta) < UMBRAL_MATE:
                return estatica
            # Jugada nula: paso el turno; si aun asi supero beta, esta rama es buena.
            if (nulo_permitido and prof >= 3 and estatica >= beta
                    and pos.np[side] > 0 and abs(beta) < UMBRAL_MATE):
                reduccion = 2 + (prof >= 6)
                pos.hacer_nulo()
                valor = -self._negamax(pos, prof - 1 - reduccion, -beta, -beta + 1, ply + 1, False)
                pos.deshacer_nulo()
                if valor >= beta:
                    return beta if valor >= UMBRAL_MATE else valor

        # ---- Generar y ordenar jugadas ----
        b = pos.b
        killers = self.killers[ply]
        hist_t = self.historial
        puntuadas = []
        for m in pos.generar():
            if m == mov_tabla:
                puntos = 10000000
            else:
                victima = b[(m >> 6) & 63]
                p = b[m & 63]
                if victima:
                    puntos = 1000000 + 10 * VALOR_ORDEN[victima if victima < 7 else victima - 6] \
                        - VALOR_ORDEN[p if p < 7 else p - 6] // 10
                elif (m >> 12) & 7 == 5:
                    puntos = 1100000
                elif m == killers[0]:
                    puntos = 900000
                elif m == killers[1]:
                    puntos = 800000
                else:
                    puntos = hist_t[p][(m >> 6) & 63]
                    if (m >> 15) == 1:
                        puntos = 1000000  # captura al paso
            puntuadas.append((puntos, m))
        puntuadas.sort(reverse=True)

        mejor = -INFINITO
        mejor_mov = 0
        legales = 0
        for puntos, m in puntuadas:
            pos.hacer(m)
            if not pos.legal_tras_hacer():
                pos.deshacer()
                continue
            legales += 1
            if legales == 1:
                valor = -self._negamax(pos, prof - 1, -beta, -alfa, ply + 1, True)
            else:
                reduccion = 0
                if (prof >= 3 and legales > 4 and not en_jaque and puntos < 800000
                        and not pos.en_jaque()):
                    reduccion = 1 if legales < 10 else 2
                valor = -self._negamax(pos, prof - 1 - reduccion, -alfa - 1, -alfa, ply + 1, True)
                if valor > alfa and (reduccion or valor < beta):
                    valor = -self._negamax(pos, prof - 1, -beta, -alfa, ply + 1, True)
            pos.deshacer()

            if valor > mejor:
                mejor = valor
                mejor_mov = m
                if raiz:
                    self.mejor_raiz = m
                if valor > alfa:
                    alfa = valor
                    if alfa >= beta:
                        if puntos < 800000:  # jugada tranquila que corta: killer + historial
                            if killers[0] != m:
                                killers[1] = killers[0]
                                killers[0] = m
                            fila_h = hist_t[b[m & 63]]
                            fila_h[(m >> 6) & 63] = min(fila_h[(m >> 6) & 63] + prof * prof, 500000)
                        break

        if legales == 0:
            return -(MATE - ply) if en_jaque else 0

        valor_guardar = mejor
        if valor_guardar >= UMBRAL_MATE:
            valor_guardar += ply
        elif valor_guardar <= -UMBRAL_MATE:
            valor_guardar -= ply
        if mejor <= alfa_original:
            tipo = SUPERIOR
        elif mejor >= beta:
            tipo = INFERIOR
        else:
            tipo = EXACTO
        self.tabla[h] = (prof, valor_guardar, tipo, mejor_mov)
        return mejor

    # ---------- busqueda de capturas ----------

    def _quiescencia(self, pos, alfa, beta, ply, qd):
        self.nodos += 1
        if not self.nodos & 2047 and time.perf_counter() > self.limite:
            raise SinTiempo()

        side = pos.side
        en_jaque = pos.atacado(pos.ksq[side], 1 - side)
        if not en_jaque:
            estatica = self.evaluar(pos)
            if estatica >= beta:
                return estatica
            if estatica > alfa:
                alfa = estatica
            if qd >= 10:
                return estatica
            movs = pos.generar(True)
        else:
            if qd >= 4:
                return self.evaluar(pos)
            movs = pos.generar()

        b = pos.b
        puntuadas = []
        for m in movs:
            victima = b[(m >> 6) & 63]
            p = b[m & 63]
            puntos = 0
            if victima:
                puntos = 10 * VALOR_ORDEN[victima if victima < 7 else victima - 6] \
                    - VALOR_ORDEN[p if p < 7 else p - 6] // 10
            puntuadas.append((puntos, m))
        puntuadas.sort(reverse=True)

        legales = 0
        for puntos, m in puntuadas:
            pos.hacer(m)
            if not pos.legal_tras_hacer():
                pos.deshacer()
                continue
            legales += 1
            valor = -self._quiescencia(pos, -beta, -alfa, ply + 1, qd + 1)
            pos.deshacer()
            if valor >= beta:
                return valor
            if valor > alfa:
                alfa = valor
        if en_jaque and legales == 0:
            return -(MATE - ply)
        return alfa
