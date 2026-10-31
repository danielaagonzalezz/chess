from chess.bots.caracteristicas import N_EXTRAS, NOMBRES, TEMPO, extras
from chess.bots.evaluacion_ml import a_codigos
from chess.game import Game


def contadores(fen):
    game = Game.desde_fen(fen)
    return extras(a_codigos(game.board), game.turno == "white")


def indice(nombre):
    return NOMBRES.index(nombre)


def test_posicion_inicial_todo_igualado_salvo_el_turno():
    v = contadores("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert len(v) == N_EXTRAS
    assert v[TEMPO] == 1
    assert v[:TEMPO] == [0] * TEMPO


def test_el_turno_cambia_de_signo():
    blancas = contadores("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    negras = contadores("4k3/8/8/8/8/8/8/4K3 b - - 0 1")
    assert blancas[TEMPO] == 1 and negras[TEMPO] == -1


def test_peones_doblados_y_aislados():
    # Blancas: peones a2 y a3 (doblados y aislados). Negras: peones normales b7 c7.
    v = contadores("4k3/1pp5/8/8/8/P7/P7/4K3 w - - 0 1")
    assert v[indice("peones doblados")] == 1
    assert v[indice("peones aislados")] == 2      # a2 y a3 aislados; b7 y c7 no
    

def test_peon_pasado_y_su_fila():
    # Peon blanco pasado en e5 (5a fila): fila relativa 4 -> contador "5a fila".
    v = contadores("4k3/8/8/4P3/8/8/8/4K3 w - - 0 1")
    assert v[indice("peon pasado en 5a fila")] == 1
    # Si hay un peon negro delante en la misma columna, ya no es pasado.
    v = contadores("4k3/4p3/8/4P3/8/8/8/4K3 w - - 0 1")
    assert v[indice("peon pasado en 5a fila")] == 0


def test_peon_pasado_negro_cuenta_la_fila_desde_su_lado():
    # Peon negro en e4: 5a fila contando desde las negras (rank 4 -> 7 - 3 = 4 -> "5a fila").
    v = contadores("4k3/8/8/8/4p3/8/8/4K3 w - - 0 1")
    assert v[indice("peon pasado en 5a fila")] == -1


def test_pareja_de_alfiles():
    v = contadores("4k3/8/8/8/8/8/8/2B1KB2 w - - 0 1")
    assert v[indice("pareja de alfiles")] == 1


def test_torre_en_columna_abierta_y_semiabierta():
    # Torre blanca en a1 (columna sin peones): abierta. Torre negra en h8 con peon negro propio: nada.
    v = contadores("4k2r/7p/8/8/8/8/8/R3K3 w - - 0 1")
    assert v[indice("torre en columna abierta")] == 1
    # Semiabierta: la columna no tiene peones propios pero si del rival.
    v = contadores("4k3/p7/8/8/8/8/8/R3K3 w - - 0 1")
    assert v[indice("torre en columna semiabierta")] == 1


def test_escudo_de_peones_y_peones_conectados():
    v = contadores("4k3/8/8/8/8/8/5PPP/6K1 w - - 0 1")
    assert v[indice("escudo de peones del rey")] == 3
    assert v[indice("peones conectados")] == 0
    v = contadores("4k3/8/8/8/8/3P4/2P5/4K3 w - - 0 1")
    assert v[indice("peones conectados")] == 1     # d3 esta defendido por c2


def test_son_simetricas_entre_colores():
    # La misma posicion con los colores cambiados da contadores opuestos (salvo el turno).
    a = contadores("r3k2r/pp3ppp/2n1b3/3q4/3P4/2N2N2/PP3PPP/R2QR1K1 w kq - 0 1")
    b = contadores("r2qr1k1/pp3ppp/2n2n2/3p4/3Q4/2N1B3/PP3PPP/R3K2R b KQ - 0 1")
    assert [-x for x in a[:TEMPO]] == b[:TEMPO]
