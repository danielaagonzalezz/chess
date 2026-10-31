"""
Puente entre la pagina web (JavaScript) y el motor de ajedrez (Python).

Este archivo se ejecuta dentro del navegador con Pyodide. Solo adapta el
motor: la logica del juego y los bots son los de src/chess, sin cambios.
Todas las funciones devuelven texto JSON para que JavaScript lo lea facil.
"""

import json

from chess.bots import BOTS
from chess.game import Game
from chess.pieces import (
    BISHOP, BLACK, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE, Square,
)

LETRAS = {KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K", PAWN: ""}
INICIAL = {PAWN: 8, KNIGHT: 2, BISHOP: 2, ROOK: 2, QUEEN: 1}
VALOR = {PAWN: 1, KNIGHT: 3, BISHOP: 3, ROOK: 5, QUEEN: 9}

_game = None
_bot = None
_humano = WHITE
_dos = False  # True: dos personas en el mismo tablero, sin bot
_bvb = False  # True: bot contra bot, sin humano
_bots = {}    # en bot contra bot: color -> bot
_sans = []


def _casilla(texto):
    return Square("abcdefgh".index(texto[0]), int(texto[1]) - 1)


def _san(game, jugada):
    """Escribe una jugada en notacion algebraica estandar (Nf3, exd5, O-O...)."""
    pieza = game.board.get_piece(jugada.origen)
    destino = str(jugada.destino)
    if pieza.piece_type == KING and abs(jugada.destino.file - jugada.origen.file) == 2:
        texto = "O-O" if jugada.destino.file == 6 else "O-O-O"
    else:
        captura = (
            game.board.get_piece(jugada.destino) is not None
            or (pieza.piece_type == PAWN and jugada.origen.file != jugada.destino.file)
        )
        if pieza.piece_type == PAWN:
            texto = ("abcdefgh"[jugada.origen.file] + "x" if captura else "") + destino
        else:
            # Si otra pieza igual puede ir al mismo sitio, hay que desambiguar.
            otras = [
                j for j in game.jugadas_legales()
                if j.destino == jugada.destino and j.origen != jugada.origen
                and game.board.get_piece(j.origen) == pieza
            ]
            desamb = ""
            if otras:
                if all(o.origen.file != jugada.origen.file for o in otras):
                    desamb = "abcdefgh"[jugada.origen.file]
                elif all(o.origen.rank != jugada.origen.rank for o in otras):
                    desamb = str(jugada.origen.rank + 1)
                else:
                    desamb = str(jugada.origen)
            texto = LETRAS[pieza.piece_type] + desamb + ("x" if captura else "") + destino
        if jugada.promocion is not None:
            texto += "=" + LETRAS[jugada.promocion]
    despues = game.copy()
    despues.jugar(jugada)
    if despues.esta_terminada() and despues.motivo == "jaque mate":
        texto += "#"
    elif despues.esta_en_jaque():
        texto += "+"
    return texto


def _estado():
    g = _game
    # En el modo de dos jugadores "el humano" es quien tiene el turno.
    humano = g.turno if _dos else _humano   # en bot contra bot: None
    casillas = []
    for rank in range(8):
        for file in range(8):
            p = g.board.get_piece(Square(file, rank))
            casillas.append(p.symbol() if p else "")

    # Piezas capturadas = las que faltan respecto a la posicion inicial.
    capturadas = {WHITE: [], BLACK: []}
    material = {WHITE: 0, BLACK: 0}
    cuenta = {}
    for s in casillas:
        if s:
            cuenta[s] = cuenta.get(s, 0) + 1
    for tipo, cantidad in INICIAL.items():
        letra = "P" if tipo == PAWN else LETRAS[tipo]
        for color, simbolo in ((WHITE, letra), (BLACK, letra.lower())):
            en_tablero = cuenta.get(simbolo, 0)
            material[color] += en_tablero * VALOR[tipo]
            faltan = max(0, cantidad - en_tablero)
            capturadas[color] += [simbolo] * faltan

    ultima = str(g.historial[-1]) if g.historial else None
    rey = None
    if g.esta_en_jaque():
        simbolo_rey = "K" if g.turno == WHITE else "k"
        rey = casillas.index(simbolo_rey)

    return json.dumps({
        "casillas": casillas,
        "turno": g.turno,
        "humano": humano,
        "dos": _dos,
        "bvb": _bvb,
        "bot_blancas": _bots[WHITE].name if _bvb else None,
        "bot_negras": _bots[BLACK].name if _bvb else None,
        "orientacion": WHITE if (_dos or _bvb) else _humano,
        "legales": [str(j) for j in g.jugadas_legales()],
        "jaque": g.esta_en_jaque(),
        "rey_en_jaque": rey,
        "terminada": g.esta_terminada(),
        "ganador": g.ganador(),
        "resultado": g.resultado,
        "motivo": g.motivo,
        "ultima": ultima,
        "historial": list(_sans),
        "fen": g.fen(),
        "capturadas": capturadas,
        "ventaja": material[WHITE] - material[BLACK],
        "bot": _bot.name if _bot else None,
    })


def bots():
    return json.dumps(list(BOTS))


def nueva(color, bot):
    """Empieza una partida. color: 'white' o 'black' (el del humano)."""
    global _game, _bot, _humano, _sans, _dos, _bvb
    _game = Game()
    _humano = color
    _dos = bot == "humano"
    _bvb = False
    _bot = None if _dos else BOTS[bot]()
    _sans = []
    return _estado()


def nueva_bots(blancas, negras):
    """Empieza una partida entre dos bots (nombres del catalogo BOTS)."""
    global _game, _bot, _humano, _sans, _dos, _bvb, _bots
    _game = Game()
    _humano = None
    _dos = False
    _bvb = True
    _bot = None
    _bots = {WHITE: BOTS[blancas](), BLACK: BOTS[negras]()}
    _sans = []
    return _estado()


def estado():
    return _estado()


def jugar(texto):
    """Juega la jugada del humano (por ejemplo 'e2e4' o 'e7e8q')."""
    global _sans
    if _game.esta_terminada() or (not _dos and _game.turno != _humano):
        raise ValueError("No es tu turno")
    jugada = next((j for j in _game.jugadas_legales() if str(j) == texto), None)
    if jugada is None:
        raise ValueError("Jugada ilegal: " + texto)
    _sans.append(_san(_game, jugada))
    _game.jugar(jugada)
    return _estado()


def mover_bot():
    """Si le toca a un bot, elige y juega su jugada (en bot contra bot, el del turno)."""
    if _game.esta_terminada():
        return _estado()
    if _bvb:
        bot = _bots[_game.turno]
    elif _dos or _game.turno == _humano:
        return _estado()
    else:
        bot = _bot
    jugada = bot.choose_move(_game.copy())
    _sans.append(_san(_game, jugada))
    _game.jugar(jugada)
    return _estado()


def deshacer():
    """Deshace hasta tu ultima jugada (la del bot y la tuya)."""
    global _game, _sans
    historial = list(_game.historial)
    quitar = 1
    # Si le toca al humano, el bot ya respondio: se quitan dos jugadas.
    if not _dos and _game.turno == _humano and len(historial) >= 2:
        quitar = 2
    if not historial:
        return _estado()
    nuevo = Game()
    for j in historial[:-quitar]:
        nuevo.jugar(j)
    _game = nuevo
    _sans = _sans[:-quitar]
    return _estado()


def desde_fen(fen, color, bot):
    """Empieza desde una posicion FEN (util para probar finales y la promocion)."""
    global _game, _bot, _humano, _sans, _dos, _bvb
    _game = Game.desde_fen(fen)
    _humano = color
    _dos = bot == "humano"
    _bvb = False
    _bot = None if _dos else BOTS[bot]()
    _sans = []
    return _estado()
