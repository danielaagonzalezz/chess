"""
Partida de ajedrez: la clase Game.

Un Game junta todo lo que hemos hecho hasta ahora y guarda lo que le
falta a un tablero para ser una partida de verdad:

- de quien es el turno,
- que enroques siguen disponibles,
- si hay una casilla de captura al paso,
- el historial de jugadas,
- y si la partida ha terminado (jaque mate, tablas) y como.

Es la clase que usaran la interfaz web y los bots: se le pregunta que
jugadas son legales (jugadas_legales) y se le dice cual se juega (jugar).

Ejemplo:

    game = Game()
    game.jugar("e2e4")
    game.jugar("e7e5")
    print(game.board)
    print(game.jugadas_legales())
"""

from chess.board import Board
from chess.exceptions import GameOverError, InvalidFenError, InvalidMoveError
from chess.move import calcular_casilla_al_paso, jugada_desde_texto
from chess.pieces import (
    Piece, Square, PIECE_LETTERS, opposite_color, square_from_algebraic,
    WHITE, BLACK, PAWN, KNIGHT, BISHOP, KING,
)
from chess.reglas import (
    actualizar_derechos_enroque, aplicar_jugada_completa, copiar_tablero,
    esta_en_jaque, jugadas_legales,
)

# Posicion inicial en notacion FEN (el formato estandar para guardar posiciones).
FEN_INICIAL = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Resultados posibles de una partida.
RESULTADO_BLANCAS = "1-0"
RESULTADO_NEGRAS = "0-1"
RESULTADO_TABLAS = "1/2-1/2"

# Motivos por los que termina una partida.
JAQUE_MATE = "jaque mate"
AHOGADO = "ahogado"
MATERIAL_INSUFICIENTE = "material insuficiente"
TRIPLE_REPETICION = "triple repeticion"
REGLA_50_MOVIMIENTOS = "regla de los 50 movimientos"

# Orden en el que se escriben los derechos de enroque en FEN.
ORDEN_DERECHOS = "KQkq"


class Game:
    """Una partida de ajedrez: tablero, turno, historial y resultado."""

    def __init__(self):
        self._cargar_fen(FEN_INICIAL)

    # -----------------------------------------------------
    # Crear partidas
    # -----------------------------------------------------

    @classmethod
    def desde_fen(cls, fen):
        """Crea una partida a partir de una posicion en notacion FEN."""
        partida = cls.__new__(cls)
        partida._cargar_fen(fen)
        return partida

    def copy(self):
        """
        Devuelve una copia independiente de la partida.

        Muy util para los bots: pueden probar jugadas en la copia sin
        estropear la partida real.
        """
        copia = Game.__new__(Game)
        copia.board = copiar_tablero(self.board)
        copia.turno = self.turno
        copia.derechos_enroque = set(self.derechos_enroque)
        copia.casilla_al_paso = self.casilla_al_paso
        copia.medios_movimientos = self.medios_movimientos
        copia.numero_jugada = self.numero_jugada
        copia.historial = list(self.historial)
        copia._repeticiones = dict(self._repeticiones)
        copia.resultado = self.resultado
        copia.motivo = self.motivo
        copia._legales = self._legales
        copia._clave = self._clave
        return copia

    # -----------------------------------------------------
    # Consultar el estado
    # -----------------------------------------------------

    def jugadas_legales(self):
        """Lista de jugadas legales del jugador que tiene el turno."""
        if self.resultado is not None:
            return []
        if self._legales is None:
            self._legales = jugadas_legales(
                self.board, self.turno, self.casilla_al_paso, self.derechos_enroque
            )
        return list(self._legales)

    def esta_en_jaque(self):
        """True si el jugador que tiene el turno esta en jaque."""
        return esta_en_jaque(self.board, self.turno)

    def esta_terminada(self):
        """True si la partida ha terminado."""
        return self.resultado is not None

    def ganador(self):
        """WHITE, BLACK, o None si la partida sigue o terminó en tablas."""
        if self.resultado == RESULTADO_BLANCAS:
            return WHITE
        if self.resultado == RESULTADO_NEGRAS:
            return BLACK
        return None

    # -----------------------------------------------------
    # Jugar
    # -----------------------------------------------------

    def jugar(self, jugada):
        """
        Juega una jugada. Puede ser una Move o un texto como "e2e4".

        Lanza GameOverError si la partida ya ha terminado e
        InvalidMoveError si la jugada no es legal. Si falla, la partida
        no cambia.
        """
        if isinstance(jugada, str):
            jugada = jugada_desde_texto(jugada)

        if self.resultado is not None:
            raise GameOverError("La partida ya ha terminado (" + self.resultado + ")")

        if jugada not in self.jugadas_legales():
            raise InvalidMoveError("Jugada ilegal: " + str(jugada))

        pieza = self.board.get_piece(jugada.origen)

        # Hay que calcular la nueva casilla de captura al paso ANTES de mover.
        nueva_casilla_al_paso = calcular_casilla_al_paso(self.board, jugada)

        capturada = aplicar_jugada_completa(self.board, jugada, self.casilla_al_paso)

        # Contador de la regla de los 50 movimientos: vuelve a 0 con
        # cualquier captura o movimiento de peon.
        if pieza.piece_type == PAWN or capturada is not None:
            self.medios_movimientos = 0
        else:
            self.medios_movimientos += 1

        self.derechos_enroque = actualizar_derechos_enroque(self.derechos_enroque, jugada)
        self.casilla_al_paso = nueva_casilla_al_paso
        self.historial.append(jugada)

        if self.turno == BLACK:
            self.numero_jugada += 1
        self.turno = opposite_color(self.turno)

        self._legales = None
        self._clave = None
        self._registrar_posicion()
        self._actualizar_resultado()

    # -----------------------------------------------------
    # FEN
    # -----------------------------------------------------

    def fen(self):
        """Devuelve la posicion actual como texto FEN."""
        filas = []
        for rank in range(7, -1, -1):
            texto = ""
            vacias = 0
            for file in range(8):
                pieza = self.board.get_piece(Square(file, rank))
                if pieza is None:
                    vacias += 1
                else:
                    if vacias > 0:
                        texto += str(vacias)
                        vacias = 0
                    texto += pieza.symbol()
            if vacias > 0:
                texto += str(vacias)
            filas.append(texto)

        turno = "w" if self.turno == WHITE else "b"

        derechos = ""
        for letra in ORDEN_DERECHOS:
            if letra in self.derechos_enroque:
                derechos += letra
        if derechos == "":
            derechos = "-"

        al_paso = "-"
        if self.casilla_al_paso is not None:
            al_paso = str(self.casilla_al_paso)

        return " ".join([
            "/".join(filas), turno, derechos, al_paso,
            str(self.medios_movimientos), str(self.numero_jugada),
        ])

    def _cargar_fen(self, fen):
        """Rellena la partida con la posicion que describe el texto FEN."""
        partes = fen.split()
        if len(partes) != 6:
            raise InvalidFenError("Un FEN tiene 6 partes, este tiene " + str(len(partes)))
        colocacion, turno, derechos, al_paso, medios, numero = partes

        # ---- Piezas ----
        letras_a_tipo = {}
        for tipo, letra in PIECE_LETTERS.items():
            letras_a_tipo[letra] = tipo

        filas = colocacion.split("/")
        if len(filas) != 8:
            raise InvalidFenError("El FEN debe tener 8 filas")

        board = Board()
        for indice_fila, texto_fila in enumerate(filas):
            rank = 7 - indice_fila
            file = 0
            for caracter in texto_fila:
                if caracter.isdigit():
                    file += int(caracter)
                elif caracter.upper() in letras_a_tipo:
                    if file > 7:
                        raise InvalidFenError("Fila demasiado larga: " + texto_fila)
                    color = WHITE if caracter.isupper() else BLACK
                    tipo = letras_a_tipo[caracter.upper()]
                    board.set_piece(Square(file, rank), Piece(tipo, color))
                    file += 1
                else:
                    raise InvalidFenError("Caracter desconocido en el FEN: '" + caracter + "'")
            if file != 8:
                raise InvalidFenError("La fila '" + texto_fila + "' no suma 8 casillas")

        # ---- Turno, enroques, al paso y contadores ----
        if turno not in ("w", "b"):
            raise InvalidFenError("El turno debe ser 'w' o 'b'")
        if derechos != "-" and any(letra not in ORDEN_DERECHOS for letra in derechos):
            raise InvalidFenError("Derechos de enroque invalidos: '" + derechos + "'")

        casilla_al_paso = None
        if al_paso != "-":
            try:
                casilla_al_paso = square_from_algebraic(al_paso)
            except Exception:
                raise InvalidFenError("Casilla al paso invalida: '" + al_paso + "'")

        if not (medios.isdigit() and numero.isdigit()):
            raise InvalidFenError("Los contadores del FEN deben ser numeros")

        self.board = board
        self.turno = WHITE if turno == "w" else BLACK
        self.derechos_enroque = set() if derechos == "-" else set(derechos)
        self.casilla_al_paso = casilla_al_paso
        self.medios_movimientos = int(medios)
        self.numero_jugada = int(numero)
        self.historial = []
        self._repeticiones = {}
        self.resultado = None
        self.motivo = None
        self._legales = None
        self._clave = None

        self._registrar_posicion()
        self._actualizar_resultado()

    # -----------------------------------------------------
    # Final de partida
    # -----------------------------------------------------

    def _actualizar_resultado(self):
        """Mira si la partida ha terminado y, si es asi, guarda como."""
        if not self.jugadas_legales_sin_resultado():
            if self.esta_en_jaque():
                # Sin jugadas y en jaque: jaque mate, gana el otro.
                if self.turno == WHITE:
                    self.resultado = RESULTADO_NEGRAS
                else:
                    self.resultado = RESULTADO_BLANCAS
                self.motivo = JAQUE_MATE
            else:
                # Sin jugadas pero sin jaque: ahogado, tablas.
                self.resultado = RESULTADO_TABLAS
                self.motivo = AHOGADO
        elif self._material_insuficiente():
            self.resultado = RESULTADO_TABLAS
            self.motivo = MATERIAL_INSUFICIENTE
        elif self._repeticiones.get(self.clave_posicion(), 0) >= 3:
            self.resultado = RESULTADO_TABLAS
            self.motivo = TRIPLE_REPETICION
        elif self.medios_movimientos >= 100:
            # 100 medios movimientos = 50 jugadas de cada bando sin
            # capturas ni movimientos de peon.
            self.resultado = RESULTADO_TABLAS
            self.motivo = REGLA_50_MOVIMIENTOS

    def jugadas_legales_sin_resultado(self):
        """Jugadas legales ignorando si la partida ya esta terminada."""
        if self._legales is None:
            self._legales = jugadas_legales(
                self.board, self.turno, self.casilla_al_paso, self.derechos_enroque
            )
        return self._legales

    def _material_insuficiente(self):
        """
        True si ningun bando puede dar jaque mate por falta de piezas:
        rey contra rey, rey y un alfil/caballo contra rey, o solo alfiles
        todos en casillas del mismo color.
        """
        restantes = []
        for casilla, pieza in self.board.all_pieces():
            if pieza.piece_type != KING:
                restantes.append((casilla, pieza))

        if len(restantes) == 0:
            return True

        for casilla, pieza in restantes:
            if pieza.piece_type not in (KNIGHT, BISHOP):
                return False  # peon, torre o dama: siempre hay material

        if len(restantes) == 1:
            return True

        # Varias piezas menores: solo es tabla si son todo alfiles en el
        # mismo color de casilla.
        colores_de_casilla = set()
        for casilla, pieza in restantes:
            if pieza.piece_type != BISHOP:
                return False
            colores_de_casilla.add((casilla.file + casilla.rank) % 2)
        return len(colores_de_casilla) == 1

    # -----------------------------------------------------
    # Triple repeticion
    # -----------------------------------------------------

    def clave_posicion(self):
        """
        Identifica la posicion actual: piezas, turno, enroques y captura al
        paso (esta ultima solo cuenta si un peon puede realmente hacerla).

        Dos posiciones con la misma clave son la misma posicion. Sirve para
        contar repeticiones y tambien a los bots para recordar posiciones
        ya analizadas. Se calcula una vez por posicion y se guarda.
        """
        if self._clave is None:
            self._clave = self._calcular_clave()
        return self._clave

    def _calcular_clave(self):
        al_paso = None
        if self.casilla_al_paso is not None:
            sentido = 1 if self.turno == WHITE else -1
            for delta_columna in (-1, 1):
                origen = self.casilla_al_paso.offset(delta_columna, -sentido)
                if origen is not None and self.board.get_piece(origen) == Piece(PAWN, self.turno):
                    al_paso = str(self.casilla_al_paso)

        # tuple(...) de las casillas es mucho mas rapido que pasar el tablero a texto.
        return (tuple(self.board.squares), self.turno, frozenset(self.derechos_enroque), al_paso)

    def _registrar_posicion(self):
        """Anota que la posicion actual ha ocurrido una vez mas."""
        clave = self.clave_posicion()
        self._repeticiones[clave] = self._repeticiones.get(clave, 0) + 1

    def __str__(self):
        return str(self.board)
