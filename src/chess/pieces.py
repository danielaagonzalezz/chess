


#Estructuras basicas: colores, tipos de pieza, piezas y casillas.
 

from chess.exceptions import InvalidSquareError
 

# COLORES


 
WHITE = "white"
BLACK = "black"
 
 
def opposite_color(color):
    """Devuelve el color contrario al que le pasamos."""
    if color == WHITE:
        return BLACK
    else:
        return WHITE
 
 
# =========================================================
# TIPOS DE PIEZA
# =========================================================
# Igual que con los colores: seis textos fijos, uno por tipo de pieza.
 
PAWN = "pawn"
KNIGHT = "knight"
BISHOP = "bishop"
ROOK = "rook"
QUEEN = "queen"
KING = "king"
 
# Letra estandar de cada pieza en notacion de ajedrez.
PIECE_LETTERS = {
    PAWN: "P",
    KNIGHT: "N",
    BISHOP: "B",
    ROOK: "R",
    QUEEN: "Q",
    KING: "K",
}
 
# Valor en puntos de cada pieza (el rey no se valora: 0).
PIECE_VALUES = {
    PAWN: 1,
    KNIGHT: 3,
    BISHOP: 3,
    ROOK: 5,
    QUEEN: 9,
    KING: 0,
}
 
# Simbolo visual (unicode) de cada combinacion tipo+color.
PIECE_UNICODE = {
    (PAWN, WHITE): "\u2659",
    (KNIGHT, WHITE): "\u2658",
    (BISHOP, WHITE): "\u2657",
    (ROOK, WHITE): "\u2656",
    (QUEEN, WHITE): "\u2655",
    (KING, WHITE): "\u2654",
    (PAWN, BLACK): "\u265F",
    (KNIGHT, BLACK): "\u265E",
    (BISHOP, BLACK): "\u265D",
    (ROOK, BLACK): "\u265C",
    (QUEEN, BLACK): "\u265B",
    (KING, BLACK): "\u265A",
}
 
 
class Piece:
    """Una pieza concreta: un tipo (peon, caballo...) y un color."""
 
    def __init__(self, piece_type, color):
        self.piece_type = piece_type
        self.color = color
 
    def value(self):
        """Valor material de la pieza (peon=1 ... reina=9, rey=0)."""
        return PIECE_VALUES[self.piece_type]
 
    def symbol(self):
        """Letra de la pieza: mayuscula si es blanca, minuscula si es negra."""
        letter = PIECE_LETTERS[self.piece_type]
        if self.color == WHITE:
            return letter
        else:
            return letter.lower()
 
    def unicode(self):
        """Simbolo visual de la pieza (para imprimir el tablero)."""
        return PIECE_UNICODE[(self.piece_type, self.color)]
 
    def __str__(self):
        # Esto se usa cuando haces print(pieza) o str(pieza)
        return self.symbol()
 
    def __eq__(self, other):
        # Esto se usa cuando comparas dos piezas con ==
        if not isinstance(other, Piece):
            return False
        return self.piece_type == other.piece_type and self.color == other.color
 
 
# =========================================================
# CASILLAS
# =========================================================
 
FILES = "abcdefgh"  # las 8 columnas del tablero, de la a a la h
 
 
class Square:
    """
    Una casilla del tablero.
 
    file: columna, numero de 0 a 7 (0=a, 1=b, ... 7=h)
    rank: fila, numero de 0 a 7 (0=rango 1, 1=rango 2, ... 7=rango 8)
    """
 
    def __init__(self, file, rank):
        if file < 0 or file > 7 or rank < 0 or rank > 7:
            raise InvalidSquareError(
                "Casilla fuera del tablero: file=" + str(file) + ", rank=" + str(rank)
            )
        self.file = file
        self.rank = rank
 #en el a esstá el blanco
    def to_algebraic(self):
        """Convierte la casilla a notacion algebraica, por ejemplo 'e4'."""
        letra_columna = FILES[self.file]
        numero_fila = self.rank + 1
        return letra_columna + str(numero_fila)
 
    def to_index(self):
        """Convierte la casilla a un numero unico de 0 a 63."""
        return self.rank * 8 + self.file
 
    def offset(self, delta_file, delta_rank):
        """
        Devuelve la casilla que resulta de moverse delta_file columnas y
        delta_rank filas desde aqui. Si el resultado cae fuera del
        tablero, devuelve None en vez de dar un error.
        """
        new_file = self.file + delta_file
        new_rank = self.rank + delta_rank
        if new_file < 0 or new_file > 7 or new_rank < 0 or new_rank > 7:
            return None
        return Square(new_file, new_rank)
 
    def __str__(self):
        return self.to_algebraic()
 
    def __eq__(self, other):
        if not isinstance(other, Square):
            return False
        return self.file == other.file and self.rank == other.rank
 
 
def square_from_algebraic(notation):
    """Crea una Square a partir de notacion algebraica, por ejemplo 'e4'."""
    if len(notation) != 2:
        raise InvalidSquareError("Notacion de casilla invalida: '" + notation + "'")
 
    letra_columna = notation[0].lower()
    numero_fila = notation[1]
 
    if letra_columna not in FILES or numero_fila not in "12345678":
        raise InvalidSquareError("Notacion de casilla invalida: '" + notation + "'")
 
    file = FILES.index(letra_columna)
    rank = int(numero_fila) - 1
    return Square(file, rank)
 
 
def square_from_index(index):
    """Crea una Square a partir de un numero de 0 a 63."""
    if index < 0 or index > 63:
        raise InvalidSquareError("Indice de casilla invalido: " + str(index))
    file = index % 8
    rank = index // 8
    return Square(file, rank)
 

